from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import TypeVar
import pandas as pd
import numpy as np

from aegis_trade.domain import Symbol
from aegis_trade.engine.events import FillEvent, MarketEvent, OrderAction

Number = TypeVar("Number", Decimal, float)


def compute_realized_pnl(
    entry_price: Number,
    exit_price: Number,
    quantity_closed: Number,
    is_long: bool,
) -> Number:
    """Autorité unique du PnL réalisé, brut de frais (Lot 3).

    Quatre sites calculaient cette grandeur, dont trois avec une convention de
    signe qui leur était propre. `application/monitoring/engine.py` combinait un
    `quantity` déjà signé avec un multiplicateur de direction : la double
    inversion rendait le PnJ de tout SHORT exactement opposé au bon, et le PnL
    en pourcentage nul (le garde `quantity > 0` échoue sur un signé négatif).
    Le corpus de mémoire du Council classait donc tout short gagnant en FAILURE.

    `quantity_closed` est une quantité absolue : la direction est portée par
    `is_long` seul, jamais par le signe de la quantité. C'est la contrainte qui
    rend la double inversion structurellement impossible.

    Le paramètre de type est contraint à `Decimal | float` pour que chaque
    appelant conserve son arithmétique d'origine : le `Backtester` est en float
    de bout en bout, le `Portfolio` en Decimal. Convertir l'un vers l'autre ici
    déplacerait des arrondis dans des chiffres déjà validés par des tests.
    """
    if quantity_closed < 0:
        raise ValueError(f"quantity_closed doit être absolue, reçu {quantity_closed}")
    delta = (exit_price - entry_price) if is_long else (entry_price - exit_price)
    return delta * quantity_closed


@dataclass
class EnginePosition:
    """Internal position tracking for the Trading Engine."""
    symbol: Symbol
    volume: Decimal  # Positive for LONG, Negative for SHORT
    average_price: Decimal
    unrealized_pnl: Decimal = Decimal("0.0")
    realized_pnl: Decimal = Decimal("0.0")


@dataclass(frozen=True)
class EquityPoint:
    timestamp: datetime
    equity: Decimal
    cash: Decimal


class Portfolio:
    """
    Event-Sourced Portfolio.
    Maintains cash, equity, and positions by consuming events.
    """
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = Decimal(str(initial_capital))
        self.cash = self.initial_capital
        self.equity = self.initial_capital
        
        # Internal state
        self._positions: dict[Symbol, EnginePosition] = {}
        self._equity_curve: list[EquityPoint] = []
        self._closed_trades_pnl: list[Decimal] = []
        
        # Latest known prices for MTM
        self._latest_prices: dict[Symbol, Decimal] = {}

    @property
    def open_positions(self) -> dict[Symbol, EnginePosition]:
        """Read-only view of current open positions."""
        return self._positions.copy()

    def get_position(self, symbol: Symbol) -> EnginePosition | None:
        return self._positions.get(symbol)
        
    def get_latest_price(self, symbol: Symbol) -> Decimal | None:
        return self._latest_prices.get(symbol)

    def on_fill_event(self, event: FillEvent) -> None:
        """
        Updates positions and cash when a fill occurs.
        """
        fill_qty = event.volume if event.action == OrderAction.BUY else -event.volume
        fill_price = event.fill_price
        
        # Deduct commission from cash immediately
        self.cash -= event.commission

        if event.symbol not in self._positions:
            self._positions[event.symbol] = EnginePosition(
                symbol=event.symbol,
                volume=fill_qty,
                average_price=fill_price
            )
            # Cash impact: we bought (qty > 0) -> cash decreases by qty * price
            self.cash -= fill_qty * fill_price
        else:
            pos = self._positions[event.symbol]
            
            # Check if this trade is increasing or decreasing the position
            is_increasing = (pos.volume > 0 and fill_qty > 0) or (pos.volume < 0 and fill_qty < 0)
            
            if is_increasing:
                # Weighted average price
                total_cost = (abs(pos.volume) * pos.average_price) + (abs(fill_qty) * fill_price)
                new_volume = pos.volume + fill_qty
                pos.average_price = total_cost / abs(new_volume)
                pos.volume = new_volume
                self.cash -= fill_qty * fill_price
            else:
                # Decreasing or reversing position (Realizing PnL)
                if abs(fill_qty) <= abs(pos.volume):
                    # Partial or full close
                    realized_pnl = compute_realized_pnl(
                        entry_price=pos.average_price,
                        exit_price=fill_price,
                        quantity_closed=abs(fill_qty),
                        is_long=pos.volume > 0,
                    )
                    pos.realized_pnl += realized_pnl
                    self._closed_trades_pnl.append(realized_pnl)
                    
                    pos.volume += fill_qty
                    # Cash increases by the sold amount plus the realized PnL
                    # If Long: we sold (fill_qty < 0), cash += abs(fill_qty) * fill_price
                    # If Short: we bought (fill_qty > 0), cash -= abs(fill_qty) * fill_price
                    self.cash -= fill_qty * fill_price
                    
                    if pos.volume == 0:
                        del self._positions[event.symbol]
                else:
                    # Reversing position
                    # 1. Close current position
                    realized_pnl = compute_realized_pnl(
                        entry_price=pos.average_price,
                        exit_price=fill_price,
                        quantity_closed=abs(pos.volume),
                        is_long=pos.volume > 0,
                    )
                    self._closed_trades_pnl.append(realized_pnl)
                    
                    # Cash adjustments for closing
                    close_qty = -pos.volume
                    self.cash -= close_qty * fill_price
                    
                    # 2. Open new position in opposite direction
                    new_qty = fill_qty + pos.volume
                    self._positions[event.symbol] = EnginePosition(
                        symbol=event.symbol,
                        volume=new_qty,
                        average_price=fill_price
                    )
                    # Cash adjustments for opening
                    self.cash -= new_qty * fill_price

        self._update_equity(event.timestamp)

    def on_market_event(self, event: MarketEvent) -> None:
        """
        Updates Mark-To-Market equity.
        """
        self._latest_prices[event.bar.symbol] = event.bar.close
        self._update_equity(event.timestamp)

    def _update_equity(self, timestamp: datetime) -> None:
        unrealized = Decimal("0.0")
        for pos in self._positions.values():
            if pos.symbol in self._latest_prices:
                current_price = self._latest_prices[pos.symbol]
                if pos.volume > 0:
                    pnl = (current_price - pos.average_price) * pos.volume
                else:
                    pnl = (pos.average_price - current_price) * abs(pos.volume)
                pos.unrealized_pnl = pnl
                unrealized += pnl

        # Note: In a real margin account, cash doesn't strictly define equity. 
        # Equity = Cash + Position Value. 
        # Here `self.cash` represents the cash balance (after subtracting position cost).
        # Position Value = abs(volume) * current_price.
        # So Equity = Cash + sum(volume * current_price) if Long, Cash - sum(volume * current_price) if Short.
        # Actually, simpler: Equity = Initial Capital + Realized PnL + Unrealized PnL - Total Commissions
        # But since Cash already factors in Realized PnL, Commissions and initial cost:
        # If we bought 1 BTC at $50k with $100k capital. Cash = $50k. BTC value = $60k. Equity = $110k.
        # Equity = Cash + Position Value = 50k + 60k = 110k.
        position_value = Decimal("0.0")
        for pos in self._positions.values():
            if pos.symbol in self._latest_prices:
                if pos.volume > 0:
                    position_value += pos.volume * self._latest_prices[pos.symbol]
                else:
                    # For short, we received cash when selling, so we owe the position value.
                    position_value += pos.volume * self._latest_prices[pos.symbol] 

        self.equity = self.cash + position_value
        
        # Only record if we actually have a timestamp 
        if timestamp:
            self._equity_curve.append(EquityPoint(
                timestamp=timestamp,
                equity=self.equity,
                cash=self.cash
            ))

    @property
    def equity_curve(self) -> list[EquityPoint]:
        return self._equity_curve

    @property
    def metrics(self) -> dict[str, float]:
        """Calculates basic metrics (will be expanded in a dedicated Metrics Engine later)."""
        closed_pnl = [float(p) for p in self._closed_trades_pnl]
        total_trades = len(closed_pnl)
        winning_trades = sum(1 for p in closed_pnl if p > 0)
        losing_trades = sum(1 for p in closed_pnl if p <= 0)
        
        gross_profit = sum(p for p in closed_pnl if p > 0)
        gross_loss = sum(abs(p) for p in closed_pnl if p <= 0)
        
        win_rate = (winning_trades / total_trades) if total_trades > 0 else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (float('inf') if gross_profit > 0 else 0.0)
        
        net_profit = float(self.equity - self.initial_capital)
        
        # Max Drawdown
        max_dd = 0.0
        peak = float(self.initial_capital)
        for ep in self._equity_curve:
            eq = float(ep.equity)
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

        # Advanced Metrics
        sharpe = 0.0
        sortino = 0.0
        calmar = 0.0
        
        if total_trades > 1 and len(self._equity_curve) > 1:
            df = pd.DataFrame([{ "timestamp": ep.timestamp, "equity": float(ep.equity) } for ep in self._equity_curve])
            df.set_index("timestamp", inplace=True)
            
            # Resample to daily equity to calculate standard daily returns
            daily_equity = df["equity"].resample("1d").last().ffill().dropna()
            
            if len(daily_equity) > 1:
                daily_returns = daily_equity.pct_change().dropna()
                if len(daily_returns) > 0:
                    mean_return = daily_returns.mean()
                    std_return = daily_returns.std()
                    
                    # Sharpe Ratio (Risk-free rate = 0)
                    # Use sqrt of actual days in period to avoid absurd 252 extrapolation on short windows
                    days = len(daily_equity)
                    annualization_factor = np.sqrt(days) if days < 30 else np.sqrt(252)
                    
                    sharpe = (mean_return / std_return * annualization_factor) if std_return > 0 else 0.0
                    
                    # Sortino Ratio
                    downside_returns = daily_returns[daily_returns < 0]
                    downside_std = downside_returns.std() if len(downside_returns) > 1 else 0.0
                    sortino = (mean_return / downside_std * annualization_factor) if downside_std > 0 else (float('inf') if mean_return > 0 else 0.0)
                    
                    # Calmar Ratio
                    if days > 0:
                        # Avoid exponentiating 7 days to 36 (252/7)
                        if days < 30:
                            period_return = (daily_equity.iloc[-1] / daily_equity.iloc[0]) - 1
                        else:
                            period_return = (daily_equity.iloc[-1] / daily_equity.iloc[0]) ** (252 / days) - 1
                            
                        calmar = (period_return / max_dd) if max_dd > 0 else (float('inf') if period_return > 0 else 0.0)
        else:
            # Not enough trades to be statistically significant
            sharpe = float('nan')
            sortino = float('nan')
            calmar = float('nan')

        return {
            "net_profit": net_profit,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "max_drawdown": max_dd,
            "total_trades": total_trades,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "calmar_ratio": calmar
        }

from aegis_trade.engine.global_risk import GlobalRiskManager
from aegis_trade.engine.events import OrderEvent, AuditEvent, EngineEvent

class PortfolioEngine(Portfolio):
    """
    Active Portfolio Engine that intercepts orders and applies Global Risk Governance.
    """
    def __init__(self, initial_capital: float = 100000.0, risk_manager: GlobalRiskManager | None = None):
        super().__init__(initial_capital)
        self.risk_manager = risk_manager or GlobalRiskManager()

    def process_order(self, order: OrderEvent) -> tuple[bool, EngineEvent]:
        """
        Validates an order through the Global Risk Manager.
        Returns (is_approved, event). If approved, event is the OrderEvent.
        If rejected, event is an AuditEvent.
        """
        is_approved, reason = self.risk_manager.validate_order(order, self, self._latest_prices)
        if not is_approved:
            audit = AuditEvent(
                timestamp=order.timestamp,
                audit_type="RISK_REJECTION",
                message=f"Order {order.action.value.upper()} {order.volume} {order.symbol.name} REJECTED: {reason}"
            )
            return False, audit
        return True, order
