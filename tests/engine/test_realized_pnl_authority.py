"""Non-régression numérique du PnL réalisé — Lot 3, souveraineté des grandeurs.

Quatre sites calculaient cette grandeur avec trois conventions de signe
distinctes. Mesurés contre une référence de comptabilité de trade sur les quatre
combinaisons direction × issue :

    engine/portfolio.py             exact sur les 4
    engine/backtester.py (brut)     exact sur les 4
    application/monitoring/engine   exact en LONG, **signe inversé en SHORT**

Le défaut de `monitoring` n'était pas une duplication de code identique : sa
`PositionSnapshot.quantity` est signée (négative en SHORT) et il lui appliquait
en plus un multiplicateur de direction. La double inversion produisait
l'opposé exact du PnL, et le garde `quantity > 0` mettait le pourcentage à zéro
pour tout short — ce que `_run_reflection_pipeline` traduit en `FAILURE`.

Ce test verrouille le critère de sortie du Lot 3 : mêmes entrées, même sortie,
quel que soit l'appelant.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from aegis_trade.application.monitoring.engine import MonitoringEngine
from aegis_trade.domain.core import AssetClass, Symbol
from aegis_trade.domain.execution import FillEvent as BrokerFillEvent
from aegis_trade.engine.backtester import Backtester
from aegis_trade.engine.events import FillEvent, OrderAction, PositionEvent
from aegis_trade.engine.portfolio import Portfolio, compute_realized_pnl

SYMBOL = Symbol("XAUUSD", AssetClass.COMMODITIES)

# nom, is_long, entrée, sortie, quantité, PnL brut de référence
SCENARIOS = [
    ("long_gagnant", True, "100", "110", "2", "20"),
    ("long_perdant", True, "100", "90", "2", "-20"),
    ("short_gagnant", False, "100", "90", "2", "20"),
    ("short_perdant", False, "100", "110", "2", "-20"),
]


def reference_realized_pnl(
    is_long: bool, entry: Decimal, exit_price: Decimal, quantity: Decimal
) -> Decimal:
    """Référence indépendante, écrite depuis la définition comptable.

    Volontairement non factorisée avec `compute_realized_pnl` : elle ne partage
    aucune ligne avec le code testé, sinon elle le validerait par lui-même.
    """
    if is_long:
        return (exit_price - entry) * quantity
    return (entry - exit_price) * quantity


# ---------------------------------------------------------------------------
# 1. L'autorité est conforme à la référence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name,is_long,entry,exit_price,qty,expected", SCENARIOS)
def test_authority_matches_independent_reference(
    name: str, is_long: bool, entry: str, exit_price: str, qty: str, expected: str
) -> None:
    result = compute_realized_pnl(
        entry_price=Decimal(entry),
        exit_price=Decimal(exit_price),
        quantity_closed=Decimal(qty),
        is_long=is_long,
    )

    assert result == reference_realized_pnl(
        is_long, Decimal(entry), Decimal(exit_price), Decimal(qty)
    )
    assert result == Decimal(expected)


def test_authority_rejects_a_signed_quantity() -> None:
    """La quantité doit être absolue : c'est ce qui interdit la double inversion.

    Passer une quantité déjà signée à une fonction qui porte aussi la direction
    est exactement le défaut de `monitoring` ; le refus est structurel, pas
    documentaire.
    """
    with pytest.raises(ValueError):
        compute_realized_pnl(
            entry_price=Decimal("100"),
            exit_price=Decimal("110"),
            quantity_closed=Decimal("-2"),
            is_long=False,
        )


def test_authority_preserves_the_caller_arithmetic() -> None:
    """Le `Backtester` est en float, le `Portfolio` en Decimal : ni l'un ni
    l'autre ne doit être converti au passage."""
    as_float = compute_realized_pnl(
        entry_price=100.0, exit_price=110.0, quantity_closed=2.0, is_long=True
    )
    as_decimal = compute_realized_pnl(
        entry_price=Decimal("100"),
        exit_price=Decimal("110"),
        quantity_closed=Decimal("2"),
        is_long=True,
    )

    assert isinstance(as_float, float)
    assert isinstance(as_decimal, Decimal)


# ---------------------------------------------------------------------------
# 2. Les trois appelants produisent le même nombre que l'autorité
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name,is_long,entry,exit_price,qty,expected", SCENARIOS)
def test_portfolio_realizes_the_authority_value(
    name: str, is_long: bool, entry: str, exit_price: str, qty: str, expected: str
) -> None:
    portfolio = Portfolio(initial_capital=100000.0)
    quantity = Decimal(qty)
    open_action = OrderAction.BUY if is_long else OrderAction.SELL
    close_action = OrderAction.SELL if is_long else OrderAction.BUY
    now = datetime.now(timezone.utc)

    for action, price in ((open_action, entry), (close_action, exit_price)):
        portfolio.on_fill_event(
            FillEvent(
                timestamp=now,
                symbol=SYMBOL,
                action=action,
                volume=quantity,
                fill_price=Decimal(price),
                commission=Decimal("0"),
                exchange="TEST",
                strategy_id="pnl_authority",
            )
        )

    assert portfolio._closed_trades_pnl == [Decimal(expected)]


@pytest.mark.parametrize("name,is_long,entry,exit_price,qty,expected", SCENARIOS)
def test_backtester_realizes_the_authority_value(
    name: str, is_long: bool, entry: str, exit_price: str, qty: str, expected: str
) -> None:
    """Le PnL brut du `Backtester` est celui de l'autorité ; sa colonne `pnl`
    est nette de frais et reste donc distincte, par conception.

    Le `Backtester` est instancié sans ses collaborateurs : `_process_fill` est
    une comptabilité pure, la brancher sur un data feed n'ajouterait qu'une
    source de bruit entre l'entrée et la grandeur mesurée.
    """
    backtester = Backtester.__new__(Backtester)
    backtester.capital = 100000.0
    backtester.position = 0.0
    backtester.average_price = 0.0
    backtester.trades_history = []
    backtester.equity_curve = {}

    commission = 1.5
    now = datetime.now(timezone.utc)
    for direction, price in (
        (1 if is_long else -1, entry),
        (-1 if is_long else 1, exit_price),
    ):
        backtester._process_fill(
            BrokerFillEvent(
                symbol=SYMBOL,
                direction=direction,
                quantity=float(qty),
                fill_price=float(price),
                commission=commission,
                timestamp=now,
            ),
            float(price),
        )

    net_pnl = backtester.trades_history[-1]["pnl"]
    assert net_pnl == pytest.approx(float(expected) - commission)


@pytest.mark.asyncio
@pytest.mark.parametrize("name,is_long,entry,exit_price,qty,expected", SCENARIOS)
async def test_monitoring_realizes_the_authority_value(
    name: str, is_long: bool, entry: str, exit_price: str, qty: str, expected: str
) -> None:
    """Le cas SHORT est la régression : l'ancien code renvoyait −`expected`."""
    engine = MonitoringEngine()
    signed_volume = Decimal(qty) if is_long else -Decimal(qty)
    now = datetime.now(timezone.utc)

    await engine.process_event(
        PositionEvent(
            timestamp=now,
            symbol=SYMBOL,
            action="opened",
            volume=signed_volume,
            average_price=Decimal(entry),
        )
    )
    await engine.process_event(
        PositionEvent(
            timestamp=now,
            symbol=SYMBOL,
            action="closed",
            volume=Decimal("0"),
            average_price=Decimal(exit_price),
        )
    )

    trade = engine.get_trades()[-1]
    assert trade.side == ("LONG" if is_long else "SHORT")
    assert trade.realized_pnl_amount == Decimal(expected)

    # Le pourcentage valait 0 pour tout SHORT : `_run_reflection_pipeline`
    # classe la mémoire sur `realized_pnl_percent > 0`, donc tout short gagnant
    # partait en FAILURE.
    expected_percent = (Decimal(expected) / (Decimal(entry) * Decimal(qty))) * Decimal(100)
    assert trade.realized_pnl_percent == expected_percent
    assert (trade.realized_pnl_percent > 0) == (Decimal(expected) > 0)
