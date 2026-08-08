from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import TypeVar
import pandas as pd

from aegis_trade.domain import Symbol
from aegis_trade.engine.events import FillEvent, MarketEvent, OrderAction
from aegis_trade.engine.performance import (
    annualized_sharpe,
    annualized_sortino,
    TRADING_DAYS_PER_YEAR,
)

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


def compute_equity(
    cash: Number, positions: tuple[tuple[Number, Number], ...]
) -> Number:
    """Autorité unique de l'equity — Lot 3, souveraineté des grandeurs.

    Trois sites calculaient cette grandeur. `application/monitoring/engine.py`
    initialisait `total_unrealized_pnl` à `Decimal(0)` et ne le réécrivait
    nulle part : le terme était structurellement nul, donc `equity == cash`.
    Or ce `cash` vient du broker (`bal.total`), dont le notional a été déduit.
    Conséquence : 100k de capital, achat d'1 unité à 50k, equity affichée 50k
    au lieu de 100k — un drawdown fantôme égal au notional, à l'instant même
    de l'ouverture.

    Convention mark-to-market : `cash + Σ(volume_signé × prix_mark)`. Le
    `volume` est signé (positif pour un LONG, négatif pour un SHORT) : le
    notional du long s'ajoute, celui du short se soustrait — l'algèbre correcte
    découle de la convention de cash plutôt que d'un test explicite de side.

    Paramètre `positions` : tuple de tuples `(volume_signé, prix_mark)`. Forme
    contrainte pour que l'appelant ne puisse pas passer une liste mutable sans
    le vouloir — même raisonnement que pour `compute_realized_pnl`.

    Le type est contraint à `Decimal | float` : le `Backtester` est en float,
    le `Portfolio` en Decimal, le `MonitoringEngine` en Decimal. Le `Backtester`
    reste mesuré par équivalence, pas unifié — sa comptabilité est scellée par
    des tests existants et convertir ses float déplacerait des arrondis validés.
    """
    if isinstance(cash, Decimal):
        decimal_value = Decimal(0)
        for signed_volume, mark_price in positions:
            decimal_value += Decimal(str(signed_volume)) * Decimal(str(mark_price))
        return cash + decimal_value
    float_value = 0.0
    for signed_volume, mark_price in positions:
        float_value += float(signed_volume) * float(mark_price)
    return cash + float_value


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

        # `self.cash` est le solde après déduction du coût de la position. Le
        # volume étant signé, le notional du long s'ajoute et celui du short se
        # soustrait : c'est la convention portée par `compute_equity`, qui fait
        # autorité pour les trois sites de cette grandeur (Lot 3).
        marked_positions = tuple(
            (pos.volume, self._latest_prices[pos.symbol])
            for pos in self._positions.values()
            if pos.symbol in self._latest_prices
        )
        self.equity = compute_equity(cash=self.cash, positions=marked_positions)
        
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
                    days = len(daily_equity)

                    # `engine/performance.py` fait autorité sur l'annualisation (Lot 3).
                    # Les rendements sont ré-échantillonnés en journalier ci-dessus, donc la
                    # périodicité passée est bien TRADING_DAYS_PER_YEAR.
                    sharpe = annualized_sharpe(daily_returns, 0.0, TRADING_DAYS_PER_YEAR)
                    sortino = annualized_sortino(daily_returns, 0.0, TRADING_DAYS_PER_YEAR)

                    # Calmar : rendement annualisé / max drawdown.
                    # L'exposant `252/days` est conservé — il annualise un rendement CUMULÉ, ce qui
                    # est une grandeur distincte du facteur sqrt appliqué à un écart-type. Le garde
                    # `days < 30` de l'ancien code n'est plus une exception silencieuse : sous un
                    # mois, extrapoler un cumul à l'année amplifie le bruit d'un facteur 8+
                    # (252/30), donc le rendement de PÉRIODE est renvoyé tel quel et le ratio n'est
                    # pas annualisé. Documenté au lieu d'être un commentaire de fin de ligne.
                    if days > 0:
                        growth = float(daily_equity.iloc[-1] / daily_equity.iloc[0])
                        if days < 30:
                            period_return = growth - 1.0
                        else:
                            period_return = growth ** (TRADING_DAYS_PER_YEAR / days) - 1.0

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
