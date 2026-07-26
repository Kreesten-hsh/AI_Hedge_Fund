import collections
from dataclasses import dataclass
from typing import Sequence

from aegis_trade.engine.broker import Broker
from aegis_trade.engine.events import EngineEvent, MarketEvent, SignalEvent, OrderEvent, FillEvent
from aegis_trade.engine.feed import MarketDataFeed
from aegis_trade.engine.portfolio import Portfolio, EquityPoint, PortfolioEngine
from aegis_trade.engine.risk import RiskEngine
from aegis_trade.engine.strategy import Strategy


@dataclass
class EngineReport:
    metrics: dict[str, float]
    equity_curve: list[EquityPoint]


class TradingEngine:
    """
    Universal Event-Driven Trading Engine.
    Coordinates the Event Loop across Feed, Strategy, Risk, Broker, and Portfolio.
    """
    def __init__(
        self,
        feed: MarketDataFeed,
        strategy: Strategy,
        broker: Broker,
        risk_engine: RiskEngine,
        portfolio: PortfolioEngine
    ):
        self._feed = feed
        self._strategy = strategy
        self._broker = broker
        self._risk_engine = risk_engine
        self._portfolio = portfolio
        
        self._queue: collections.deque[EngineEvent] = collections.deque()
        self._pending_orders: list[OrderEvent] = []
        self._latest_market_event: MarketEvent | None = None

    def run(self) -> EngineReport:
        """
        Executes the main event loop.
        """
        for market_event in self._feed:
            # First, execute any pending orders from previous bar at the open of this new bar
            for order in self._pending_orders:
                fill = self._broker.on_order_event(order, market_event)
                if fill:
                    self._queue.append(fill)
            self._pending_orders.clear()
            
            # Now queue the market event
            self._queue.append(market_event)
            
            while self._queue:
                event = self._queue.popleft()
                
                if isinstance(event, MarketEvent):
                    self._latest_market_event = event
                    # 1. Update Portfolio MTM
                    self._portfolio.on_market_event(event)
                    # 2. Pass to strategy
                    signals = self._strategy.on_market_event(event)
                    # 3. Update Risk Engine state
                    if hasattr(self._risk_engine, "on_market_event"):
                        self._risk_engine.on_market_event(event)
                    if signals:
                        self._queue.extend(signals)
                        
                elif isinstance(event, SignalEvent):
                    # Pass to Risk Engine -> OrderEvent
                    orders = self._risk_engine.on_signal_event(event, self._portfolio)
                    if orders:
                        self._queue.extend(orders)
                        
                elif isinstance(event, OrderEvent):
                    # Intercept order by PortfolioEngine (Global Risk Governance)
                    if hasattr(self._portfolio, "process_order"):
                        is_approved, processed_event = self._portfolio.process_order(event)
                        if is_approved:
                            self._pending_orders.append(processed_event)
                        else:
                            # Push the AuditEvent to queue for logging (if any consumers want it)
                            self._queue.append(processed_event)
                    else:
                        # Fallback if regular Portfolio is used
                        self._pending_orders.append(event)
                elif isinstance(event, FillEvent):
                    # Update Portfolio
                    self._portfolio.on_fill_event(event)

        # Force close all positions at the end of the simulation for accurate reporting
        if self._latest_market_event:
            # We bypass Strategy and Risk to liquidate directly
            for symbol, pos in list(self._portfolio.open_positions.items()):
                action = "sell" if pos.volume > 0 else "buy"
                from aegis_trade.engine.events import OrderAction
                close_order = OrderEvent(
                    timestamp=self._latest_market_event.timestamp,
                    symbol=symbol,
                    action=OrderAction(action),
                    volume=abs(pos.volume),
                    strategy_id="ENGINE_LIQUIDATION"
                )
                fill = self._broker.on_order_event(close_order, self._latest_market_event)
                if fill:
                    self._portfolio.on_fill_event(fill)

        return EngineReport(
            metrics=self._portfolio.metrics,
            equity_curve=self._portfolio.equity_curve
        )
