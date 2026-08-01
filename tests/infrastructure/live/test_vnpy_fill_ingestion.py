"""Lot 2C — les fills live alimentent réellement le Portfolio.

Ces tests portent sur la boucle de retour du risque : tant qu'un fill exécuté
chez le broker n'atteint pas le `Portfolio`, l'exposition reste vide, l'equity
ne bouge pas, le drawdown reste nul et le kill switch ne peut pas s'armer.

Le `Portfolio` utilisé ici est le vrai, jamais un double : c'est l'état qu'il
en retire qui constitue l'assertion, pas le fait qu'une méthode ait été appelée.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest

from aegis_trade.domain.core import AssetClass, Symbol
from aegis_trade.engine.events import FillEvent, OrderAction
from aegis_trade.engine.portfolio import Portfolio
from aegis_trade.infrastructure.live.vnpy.execution import VnPyExecutionGateway
from aegis_trade.infrastructure.live.vnpy.mapper import VnPySymbolMapper

BTCUSDT = Symbol(name="BTCUSDT", asset_class=AssetClass.CRYPTO)


def _trade(
    *,
    vt_symbol: str = "BTCUSDT.BINANCE",
    direction: str = "LONG",
    volume: float = 2.0,
    price: float = 50_000.0,
    trade_id: str = "vt_trade_1",
    moment: datetime | None = None,
    reference: str = "aegis_live",
) -> Mock:
    """Construit un `TradeData` vn.py minimal mais fidèle.

    vn.py livre des enums (`Direction.LONG`, `Exchange.BINANCE`) dont seul
    l'attribut `.name` / `.value` est stable : le double les imite plutôt que
    de passer des chaînes nues, sinon le test validerait une API qui n'existe
    pas côté broker.
    """
    trade = Mock()
    trade.vt_symbol = vt_symbol
    trade.symbol = vt_symbol.split(".")[0]
    trade.direction = Mock(spec=["name", "value"])
    trade.direction.name = direction
    trade.direction.value = direction.title()
    trade.volume = volume
    trade.price = price
    trade.exchange = Mock(spec=["value"])
    trade.exchange.value = vt_symbol.split(".")[-1]
    trade.datetime = moment if moment is not None else datetime.now(timezone.utc)
    trade.vt_tradeid = trade_id
    trade.reference = reference
    return trade


def _gateway(portfolio: Portfolio | None = None) -> tuple[VnPyExecutionGateway, AsyncMock]:
    publisher = AsyncMock()
    mapper = VnPySymbolMapper("BINANCE")
    mapper.register(BTCUSDT)
    gateway = VnPyExecutionGateway(
        main_engine=Mock(),
        event_publisher=publisher,
        symbol_mapper=mapper,
        portfolio=portfolio,
    )
    return gateway, publisher


@pytest.mark.asyncio
async def test_fill_opens_position_in_real_portfolio() -> None:
    """Un fill d'achat crée la position et débite la trésorerie."""
    portfolio = Portfolio(initial_capital=1_000_000.0)
    gateway, _ = _gateway(portfolio)

    await gateway.on_trade(_trade(volume=2.0, price=50_000.0))

    position = portfolio.get_position(BTCUSDT)
    assert position is not None, "le fill n'a pas atteint le Portfolio"
    assert position.volume == Decimal("2.0")
    assert position.average_price == Decimal("50000.0")
    assert portfolio.cash == Decimal("1000000.0") - Decimal("100000.0")


@pytest.mark.asyncio
async def test_fill_symbol_is_the_domain_symbol_not_a_raw_string() -> None:
    """La position doit être indexée par le `Symbol` exact, pas par une chaîne.

    `Symbol` est frozen et hashable : `asset_class="CRYPTO"` (chaîne) et
    `AssetClass.CRYPTO` produisent deux clés de hash différentes. Une
    traduction approximative ouvrirait donc une position fantôme à côté de
    celle que l'ordre a créée, et l'exposition vue par le RiskEngine serait
    fausse sans qu'aucun test ne proteste.
    """
    portfolio = Portfolio(initial_capital=1_000_000.0)
    gateway, _ = _gateway(portfolio)

    await gateway.on_trade(_trade())

    assert BTCUSDT in portfolio.open_positions
    key = next(iter(portfolio.open_positions))
    assert isinstance(key, Symbol)
    assert key.asset_class is AssetClass.CRYPTO


@pytest.mark.asyncio
async def test_short_fill_opens_negative_position() -> None:
    """Un fill SHORT doit ouvrir une position négative, pas une position longue."""
    portfolio = Portfolio(initial_capital=1_000_000.0)
    gateway, _ = _gateway(portfolio)

    await gateway.on_trade(_trade(direction="SHORT", volume=1.0))

    position = portfolio.get_position(BTCUSDT)
    assert position is not None
    assert position.volume == Decimal("-1.0")


@pytest.mark.asyncio
async def test_unknown_direction_is_rejected_not_defaulted_to_buy() -> None:
    """Une direction illisible doit lever, jamais être assimilée à un achat.

    Un défaut silencieux sur BUY inverserait le signe de la position : le
    Portfolio croirait détenir du long là où le broker a vendu.
    """
    portfolio = Portfolio(initial_capital=1_000_000.0)
    gateway, _ = _gateway(portfolio)

    with pytest.raises(ValueError, match="[Dd]irection"):
        await gateway.on_trade(_trade(direction="UNKNOWN"))

    assert portfolio.open_positions == {}


@pytest.mark.asyncio
async def test_duplicate_trade_is_applied_once() -> None:
    """Une répétition d'EVENT_TRADE (reconnexion, resynchro) ne double pas la position."""
    portfolio = Portfolio(initial_capital=1_000_000.0)
    gateway, _ = _gateway(portfolio)

    first = await gateway.on_trade(_trade(trade_id="vt_dup", volume=2.0))
    second = await gateway.on_trade(_trade(trade_id="vt_dup", volume=2.0))

    assert isinstance(first, FillEvent)
    assert second is None, "le doublon a été appliqué une seconde fois"
    position = portfolio.get_position(BTCUSDT)
    assert position is not None
    assert position.volume == Decimal("2.0")


@pytest.mark.asyncio
async def test_distinct_trades_accumulate() -> None:
    """Deux fills distincts s'additionnent : la déduplication ne doit pas trop filtrer."""
    portfolio = Portfolio(initial_capital=1_000_000.0)
    gateway, _ = _gateway(portfolio)

    await gateway.on_trade(_trade(trade_id="vt_1", volume=2.0, price=50_000.0))
    await gateway.on_trade(_trade(trade_id="vt_2", volume=1.0, price=53_000.0))

    position = portfolio.get_position(BTCUSDT)
    assert position is not None
    assert position.volume == Decimal("3.0")


@pytest.mark.asyncio
async def test_duplicate_is_not_republished_on_the_bus() -> None:
    """Un doublon ne repart pas sur le bus : sinon le P&L aval compterait deux fois."""
    gateway, publisher = _gateway(Portfolio(initial_capital=1_000_000.0))

    await gateway.on_trade(_trade(trade_id="vt_dup"))
    await gateway.on_trade(_trade(trade_id="vt_dup"))

    assert publisher.await_count == 1


@pytest.mark.asyncio
async def test_dedup_memory_stays_bounded() -> None:
    """La mémoire de déduplication est bornée : la passerelle tourne des semaines."""
    portfolio = Portfolio(initial_capital=100_000_000.0)
    publisher = AsyncMock()
    mapper = VnPySymbolMapper("BINANCE")
    mapper.register(BTCUSDT)
    gateway = VnPyExecutionGateway(
        main_engine=Mock(),
        event_publisher=publisher,
        symbol_mapper=mapper,
        portfolio=portfolio,
        max_remembered_trades=5,
    )

    for index in range(20):
        await gateway.on_trade(_trade(trade_id=f"vt_{index}", volume=1.0))

    assert len(gateway._applied_trade_ids) == 5
    assert len(gateway._applied_trade_order) == 5
    # Les 5 derniers restent protégés contre une répétition immédiate.
    assert await gateway.on_trade(_trade(trade_id="vt_19", volume=1.0)) is None


@pytest.mark.asyncio
async def test_trade_without_identifier_is_rejected() -> None:
    """Sans identifiant, la déduplication est impossible : on refuse le fill."""
    portfolio = Portfolio(initial_capital=1_000_000.0)
    gateway, _ = _gateway(portfolio)
    trade = _trade()
    trade.vt_tradeid = ""
    trade.tradeid = ""

    with pytest.raises(ValueError, match="identifiant"):
        await gateway.on_trade(trade)


@pytest.mark.asyncio
async def test_naive_timestamp_is_coerced_to_utc() -> None:
    """`EngineEvent` refuse un timestamp naïf : la passerelle doit le qualifier."""
    gateway, publisher = _gateway(Portfolio(initial_capital=1_000_000.0))
    naive = datetime(2026, 7, 1, 12, 0, 0)

    fill = await gateway.on_trade(_trade(moment=naive))

    assert fill is not None
    assert fill.timestamp.tzinfo is timezone.utc
    assert publisher.await_count == 1


@pytest.mark.asyncio
async def test_aware_non_utc_timestamp_is_converted() -> None:
    """Un horodatage déjà zoné est converti, pas réécrit."""
    gateway, _ = _gateway(Portfolio(initial_capital=1_000_000.0))
    moment = datetime(2026, 7, 1, 14, 0, 0, tzinfo=timezone(timedelta(hours=2)))

    fill = await gateway.on_trade(_trade(moment=moment))

    assert fill is not None
    assert fill.timestamp == datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_fill_is_published_on_the_event_bus() -> None:
    """Le fill est publié : l'audit et le monitoring en dépendent."""
    gateway, publisher = _gateway(Portfolio(initial_capital=1_000_000.0))

    await gateway.on_trade(_trade())

    publisher.assert_awaited_once()
    published = publisher.await_args[0][0]
    assert isinstance(published, FillEvent)
    assert published.action == OrderAction.BUY
    assert published.exchange == "BINANCE"


@pytest.mark.asyncio
async def test_gateway_without_portfolio_still_publishes() -> None:
    """Sans Portfolio branché, la passerelle publie sans appliquer ni planter."""
    gateway, publisher = _gateway(portfolio=None)

    fill = await gateway.on_trade(_trade())

    assert isinstance(fill, FillEvent)
    publisher.assert_awaited_once()


@pytest.mark.asyncio
async def test_zero_volume_fill_is_rejected_by_the_domain() -> None:
    """Le domaine refuse un volume nul : la passerelle ne le contourne pas."""
    gateway, _ = _gateway(Portfolio(initial_capital=1_000_000.0))

    with pytest.raises(ValueError):
        await gateway.on_trade(_trade(volume=0.0))


class TestSymbolRoundTrip:
    """L'aller-retour de symbole conditionne l'identité des positions."""

    def test_round_trip_preserves_asset_class(self) -> None:
        mapper = VnPySymbolMapper("BINANCE")
        forex = Symbol(name="XAUUSD", asset_class=AssetClass.FOREX)

        vt_symbol = mapper.to_vnpy_symbol(forex)
        restored = mapper.from_vnpy_symbol(vt_symbol)

        assert restored == forex
        assert restored.asset_class is AssetClass.FOREX

    def test_unknown_symbol_uses_declared_default(self) -> None:
        """Un symbole jamais vu à l'aller retombe sur la classe déclarée."""
        mapper = VnPySymbolMapper("IDEALPRO", default_asset_class=AssetClass.FOREX)

        restored = mapper.from_vnpy_symbol("EURUSD.IDEALPRO")

        assert restored.asset_class is AssetClass.FOREX

    def test_empty_symbol_is_rejected(self) -> None:
        mapper = VnPySymbolMapper("BINANCE")
        with pytest.raises(ValueError):
            mapper.from_vnpy_symbol("")

    def test_forex_fill_does_not_come_back_as_crypto(self) -> None:
        """Régression : `asset_class` était codé en dur à CRYPTO.

        Un fill FOREX revenait typé CRYPTO, donc sous une clé de hash
        différente de la position ouverte à l'aller.
        """
        mapper = VnPySymbolMapper("IDEALPRO")
        forex = Symbol(name="XAUUSD", asset_class=AssetClass.FOREX)
        mapper.register(forex)

        assert mapper.from_vnpy_symbol("XAUUSD.IDEALPRO").asset_class is AssetClass.FOREX
