import logging
import pandas as pd
from typing import List, Dict, Any

from aegis_trade.domain.core import Symbol, TimeFrame
from aegis_trade.domain.ports.data_feed import IDataFeed
from aegis_trade.domain.strategy import IStrategy
from aegis_trade.domain.execution import IBroker, OrderIntent, FillEvent
from aegis_trade.engine.performance import PerformanceEngine, TearsheetReport

logger = logging.getLogger(__name__)

class Backtester:
    """
    Modular orchestrator for historical backtesting.
    Connects DataFeed, Strategy, Broker and Performance Engine.
    """
    def __init__(self, data_feed: IDataFeed, strategy: IStrategy, broker: IBroker, starting_capital: float = 100000.0):
        self.data_feed = data_feed
        self.strategy = strategy
        self.broker = broker
        
        self.initial_capital = starting_capital
        self.capital = starting_capital
        self.position = 0.0 # simple single-asset holding
        self.average_price = 0.0
        
        self.equity_curve = {}
        self.trades_history = []
        
        # Hooks for future event-driven architecture
        self.event_bus = None
        self.risk_manager = None
        
    def _run_risk_manager_hook(self):
        """Hook for global risk management (Exposure, Max DD constraints)."""
        pass
        
    def _run_event_bus_hook(self):
        """Hook for asynchronous event publishing."""
        pass

    def run(self, symbol: Symbol, timeframe: TimeFrame) -> TearsheetReport:
        logger.info(f"Starting backtest for {symbol.name} on {timeframe.value}...")
        
        stream = self.data_feed.get_feature_stream(symbol, timeframe)
        
        for feature_set in stream:
            timestamp = feature_set.timestamp
            
            # Extract price for PnL and execution
            # Fallback to 1.0 if not found (pure signal testing)
            current_price = feature_set.features.get('close_price')
            if current_price is None:
                # If there's no close price, we try to use a dummy price of 100 for purely directional return tests.
                current_price = 100.0
            
            # 1. Update Portfolio Mark-to-Market
            unrealized_pnl = 0.0
            if self.position != 0:
                unrealized_pnl = (current_price - self.average_price) * self.position
            
            current_equity = self.capital + unrealized_pnl
            self.equity_curve[timestamp] = current_equity
            
            # 2. Strategy evaluation
            signals = self.strategy.generate_signals(feature_set)
            
            # 3. Simple Portfolio Logic (Transform Signal to Order)
            # This logic will be replaced by PM-01
            for sig in signals:
                if sig.direction == 1 and self.position <= 0:
                    # Buy
                    qty = (self.capital * 0.95) / current_price # risk 95%
                    # If we are short, we need to buy to cover first, but we keep it simple here:
                    # just go long. If we were short, we just buy 2x qty.
                    # Simplification: we close current pos and open new.
                    target_qty = qty
                    order_qty = target_qty - self.position
                    
                    intent = OrderIntent(
                        symbol=symbol, direction=1, quantity=abs(order_qty), 
                        target_price=current_price, timestamp=timestamp
                    )
                    
                    # 4. Execution
                    fill = self.broker.execute_order(intent)
                    if fill:
                        self._process_fill(fill, current_price)
                        
                elif sig.direction == -1 and self.position >= 0:
                    # Sell/Short
                    qty = (self.capital * 0.95) / current_price
                    target_qty = -qty
                    order_qty = abs(target_qty - self.position)
                    
                    intent = OrderIntent(
                        symbol=symbol, direction=-1, quantity=order_qty, 
                        target_price=current_price, timestamp=timestamp
                    )
                    
                    fill = self.broker.execute_order(intent)
                    if fill:
                        self._process_fill(fill, current_price)
                        
                elif sig.direction == 0 and self.position != 0:
                    # Close position
                    intent = OrderIntent(
                        symbol=symbol, 
                        direction=-1 if self.position > 0 else 1, 
                        quantity=abs(self.position), 
                        target_price=current_price, 
                        timestamp=timestamp
                    )
                    fill = self.broker.execute_order(intent)
                    if fill:
                        self._process_fill(fill, current_price)

        # 5. Performance Metrics
        logger.info("Computing performance metrics...")
        equity_series = pd.Series(self.equity_curve)
        trades_df = pd.DataFrame(self.trades_history)
        
        perf_engine = PerformanceEngine()
        tearsheet = perf_engine.compute_tearsheet(equity_series, trades_df)
        return tearsheet
        
    def _process_fill(self, fill: FillEvent, current_market_price: float):
        """Update internal accounting (Portfolio)."""
        signed_qty = fill.quantity * fill.direction
        
        # Realized PnL logic
        realized_pnl = 0.0
        if self.position > 0 and fill.direction < 0: # Closing a long
            qty_closed = min(self.position, fill.quantity)
            realized_pnl = (fill.fill_price - self.average_price) * qty_closed
        elif self.position < 0 and fill.direction > 0: # Closing a short
            qty_closed = min(abs(self.position), fill.quantity)
            realized_pnl = (self.average_price - fill.fill_price) * qty_closed
            
        self.capital += realized_pnl
        self.capital -= fill.commission
        
        # Average price update
        new_position = self.position + signed_qty
        if new_position == 0:
            self.average_price = 0.0
        elif (self.position > 0 and fill.direction > 0) or (self.position < 0 and fill.direction < 0):
            # Adding to position
            total_value = abs(self.position * self.average_price) + (fill.quantity * fill.fill_price)
            self.average_price = total_value / abs(new_position)
        # If reversing position, average price becomes the new fill price
        elif (self.position > 0 and new_position < 0) or (self.position < 0 and new_position > 0):
            self.average_price = fill.fill_price
            
        self.position = new_position
        
        # Record trade
        self.trades_history.append({
            'timestamp': fill.timestamp,
            'pnl': realized_pnl - fill.commission, # Net PnL of the transaction
            'turnover': fill.quantity * fill.fill_price,
            'exposure': 1 if self.position != 0 else 0
        })
