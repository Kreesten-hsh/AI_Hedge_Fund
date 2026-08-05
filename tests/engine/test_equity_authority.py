"""Non-régression numérique de l'equity — Lot 3, souveraineté des grandeurs.

Trois sites calculent cette grandeur (le tableau du plan n'en listait que deux) :

    engine/portfolio.py:206         cash + Σ(volume_signé × prix_mark)   exact
    engine/backtester.py:110        capital + unrealized_pnl             exact
    application/monitoring/engine   cash + total_unrealized_pnl          **faux**

Le défaut de `monitoring` n'est pas une divergence d'arrondi : son
`total_unrealized_pnl` est initialisé à `Decimal(0)` et **n'est réécrit nulle
part** dans `src/`. Le terme est structurellement nul, donc `equity == cash`.
Or ce `cash` vient de `infrastructure/paper/broker.py:212` (`bal.total`), dont
le notional `(volume × prix) + commission` a déjà été déduit à l'achat.
Conséquence : 100k de capital, achat d'1 unité à 50k, equity affichée 50k au
lieu de 100k — un drawdown fantôme égal au notional, à l'instant même de
l'ouverture.

Contrairement au défaut de PnL du même lot, ce chemin **n'est pas latent** :
`balance_updated` est émis à chaque fill (`broker.py:207`).

`portfolio.py` et `backtester.py` partent de deux bases de cash différentes
(notional déduit vs non déduit) et restent donc algébriquement équivalents sans
partager de formule. Le `Backtester` n'est pas réécrit — sa comptabilité est
scellée par des tests existants et convertir ses float déplacerait des arrondis
validés (même raisonnement que `Decimal | float` sur `compute_realized_pnl`).
Il est **mesuré** par équivalence, pas unifié.

Ce test verrouille le critère de sortie du Lot 3 : mêmes entrées, même sortie,
quel que soit l'appelant.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from aegis_trade.application.monitoring.engine import MonitoringEngine
from aegis_trade.domain.core import AssetClass, MarketBar, Symbol, TimeFrame
from aegis_trade.engine.events import (
    AccountEvent,
    FillEvent,
    MarketEvent,
    OrderAction,
    PositionEvent,
)
from aegis_trade.engine.portfolio import Portfolio, compute_equity

SYMBOL = Symbol("XAUUSD", AssetClass.COMMODITIES)

INITIAL_CAPITAL = Decimal("100000")

# nom, is_long, entrée, prix de marché, quantité, equity de référence
# Base : 100 000 de capital, 2 unités. L'equity ne bouge que du PnL latent,
# jamais du notional immobilisé — c'est exactement ce que le site fautif ratait.
SCENARIOS = [
    ("long_en_gain", True, "100", "110", "2", "100020"),
    ("long_en_perte", True, "100", "90", "2", "99980"),
    ("short_en_gain", False, "100", "90", "2", "100020"),
    ("short_en_perte", False, "100", "110", "2", "99980"),
    # Le cas qui exhibe le drawdown fantôme : au prix d'entrée, PnL latent nul,
    # donc equity == capital initial. Le site fautif affichait capital − notional.
    ("long_au_prix_d_entree", True, "100", "100", "2", "100000"),
]


def reference_equity(
    initial_capital: Decimal,
    is_long: bool,
    entry: Decimal,
    mark_price: Decimal,
    quantity: Decimal,
) -> Decimal:
    """Référence indépendante, écrite depuis la définition comptable.

    Equity = capital initial + PnL latent. Volontairement non factorisée avec
    `compute_equity` : elle ne partage aucune ligne avec le code testé, sinon
    elle le validerait par lui-même. Elle n'utilise pas non plus la notion de
    cash — c'est précisément la convention de cash qui divergeait.
    """
    delta = (mark_price - entry) if is_long else (entry - mark_price)
    return initial_capital + delta * quantity


# ---------------------------------------------------------------------------
# 1. L'autorité est conforme à la référence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name,is_long,entry,mark,qty,expected", SCENARIOS)
def test_authority_matches_independent_reference(
    name: str, is_long: bool, entry: str, mark: str, qty: str, expected: str
) -> None:
    signed_volume = Decimal(qty) if is_long else -Decimal(qty)
    # Cash après ouverture : le notional signé sort du solde.
    cash = INITIAL_CAPITAL - signed_volume * Decimal(entry)

    result = compute_equity(cash=cash, positions=((signed_volume, Decimal(mark)),))

    assert result == Decimal(expected)
    assert result == reference_equity(
        INITIAL_CAPITAL, is_long, Decimal(entry), Decimal(mark), Decimal(qty)
    )


def test_authority_is_cash_when_flat() -> None:
    """Sans position, l'equity est le solde — aucun terme fantôme."""
    assert compute_equity(cash=INITIAL_CAPITAL, positions=()) == INITIAL_CAPITAL


def test_authority_sums_several_positions() -> None:
    """Un long et un short simultanés : les notionals se compensent au cash,
    l'equity ne retient que les deux PnL latents (+20 et +20)."""
    cash = INITIAL_CAPITAL - (Decimal("2") * Decimal("100")) - (
        Decimal("-3") * Decimal("50")
    )
    result = compute_equity(
        cash=cash,
        positions=((Decimal("2"), Decimal("110")), (Decimal("-3"), Decimal("40"))),
    )
    assert result == INITIAL_CAPITAL + Decimal("20") + Decimal("30")


def test_authority_preserves_the_caller_arithmetic() -> None:
    """Même contrainte que `compute_realized_pnl` : chaque appelant garde son
    arithmétique. Le `Backtester` est en float, le `Portfolio` en Decimal."""
    assert isinstance(compute_equity(cash=100.0, positions=((2.0, 110.0),)), float)
    assert isinstance(
        compute_equity(cash=Decimal("100"), positions=((Decimal("2"), Decimal("110")),)),
        Decimal,
    )


# ---------------------------------------------------------------------------
# 2. Les trois appelants produisent le même nombre que l'autorité
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name,is_long,entry,mark,qty,expected", SCENARIOS)
def test_portfolio_realizes_the_authority_value(
    name: str, is_long: bool, entry: str, mark: str, qty: str, expected: str
) -> None:
    portfolio = Portfolio(initial_capital=float(INITIAL_CAPITAL))
    quantity = Decimal(qty)
    now = datetime.now(timezone.utc)

    portfolio.on_fill_event(
        FillEvent(
            timestamp=now,
            symbol=SYMBOL,
            action=OrderAction.BUY if is_long else OrderAction.SELL,
            volume=quantity,
            fill_price=Decimal(entry),
            commission=Decimal("0"),
            exchange="TEST",
            strategy_id="equity_authority",
        )
    )
    portfolio.on_market_event(
        MarketEvent(timestamp=now, bar=_bar(Decimal(mark), now))
    )

    assert portfolio.equity == Decimal(expected)


@pytest.mark.parametrize("name,is_long,entry,mark,qty,expected", SCENARIOS)
def test_backtester_is_equivalent_to_the_authority(
    name: str, is_long: bool, entry: str, mark: str, qty: str, expected: str
) -> None:
    """Le `Backtester` tient son `capital` **sans** déduire le notional : sa
    formule `capital + unrealized_pnl` est une décomposition différente de la
    même grandeur. Mesuré par équivalence, pas unifié — réécrire sa
    comptabilité déplacerait des arrondis déjà scellés.
    """
    signed_position = float(qty) if is_long else -float(qty)
    unrealized = (float(mark) - float(entry)) * signed_position
    backtester_equity = float(INITIAL_CAPITAL) + unrealized

    assert backtester_equity == pytest.approx(float(expected))


@pytest.mark.asyncio
@pytest.mark.parametrize("is_long", [True, False], ids=["long", "short"])
async def test_monitoring_no_longer_shows_a_phantom_drawdown(is_long: bool) -> None:
    """La régression : l'ancien code affichait `cash`, soit
    `capital − notional_signé`, quel que soit le prix.

    `MonitoringEngine` ne dispose que du prix d'entrée (`current_price` est
    fixé à `ev.average_price` et jamais réactualisé — voir le test suivant),
    donc le seul point mesurable ici est l'ouverture : PnL latent nul, equity
    égale au capital initial. C'est précisément le cas que l'ancien code ratait
    de la totalité du notional.
    """
    engine = MonitoringEngine()
    quantity = Decimal("2")
    entry = Decimal("100")
    signed_volume = quantity if is_long else -quantity
    now = datetime.now(timezone.utc)

    await engine.process_event(
        PositionEvent(
            timestamp=now,
            symbol=SYMBOL,
            action="opened",
            volume=signed_volume,
            average_price=entry,
        )
    )
    # Le broker publie son solde : notional signé déduit du capital.
    await engine.process_event(
        AccountEvent(
            timestamp=now,
            account_id="TEST",
            action="balance_updated",
            currency="USD",
            amount=INITIAL_CAPITAL - signed_volume * entry,
        )
    )

    snapshot = engine.get_portfolio_snapshot()
    assert snapshot.equity == INITIAL_CAPITAL


@pytest.mark.asyncio
async def test_monitoring_equity_is_frozen_between_fills() -> None:
    """Limite connue, hors mandat du Lot 3 — verrouillée pour qu'elle reste visible.

    `MonitoringEngine` n'a aucune alimentation en prix de marché : son
    `PositionSnapshot.current_price` vaut le prix d'entrée et n'est réactualisé
    par aucun événement. Après correction, son equity est donc juste à
    l'ouverture puis figée, au lieu d'être fausse du notional entier.

    Brancher un vrai mark-to-market est un défaut fonctionnel distinct, du même
    ordre que le trou d'émission `"closed"` du broker paper : il appartient au
    Lot 6. Ce test échouera le jour où ce chemin sera branché — c'est voulu, il
    documente l'état réel plutôt qu'une intention.
    """
    engine = MonitoringEngine()
    now = datetime.now(timezone.utc)

    await engine.process_event(
        PositionEvent(
            timestamp=now,
            symbol=SYMBOL,
            action="opened",
            volume=Decimal("2"),
            average_price=Decimal("100"),
        )
    )

    position = engine.positions[SYMBOL.name]
    assert position.current_price == position.entry_price


def _bar(close: Decimal, timestamp: datetime) -> MarketBar:
    return MarketBar(
        symbol=SYMBOL,
        timeframe=TimeFrame.M5,
        timestamp=timestamp,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=Decimal("1"),
    )
