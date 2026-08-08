"""Lot 2E — les features passées au Council sont celles que les agents lisent.

Défaut mesuré avant ce lot : l'orchestrateur injectait onze clés dont huit
(`trend_score`, `momentum_score`, ... `execution_cost`) ne sont lues par aucun
agent, et aucune des clés réellement lues n'était fournie honnêtement :

| agent      | clé lue             | fourni avant  | vote forcé |
|------------|---------------------|---------------|------------|
| Trend      | ema_50              | absent        | WAIT 0.0   |
| Momentum   | rsi                 | 55.0 constant | WAIT 0.1   |
| Volatility | bb_upper / bb_lower | absents       | WAIT 0.0   |
| Liquidity  | spread              | absent        | WAIT 0.0   |
| Execution  | broker_latency_ms   | absent        | WAIT 0.0   |

Avec buy_score = sell_score = 0, `ConflictResolver` renvoie un multiplicateur
nul, le verdict devient WAIT et `create_order` renvoie None : aucun ordre
n'était atteignable, quel que soit le marché.

Ces tests portent sur le contrat de clés et sur la valeur numérique produite,
jamais sur le fait qu'une méthode ait été appelée.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from aegis_trade.application.council.feature_provider import RollingFeatureProvider
from aegis_trade.domain.core import AssetClass, MarketBar, Symbol, TimeFrame, Tick
from aegis_trade.infrastructure.features.technical_extractor import (
    TechnicalFeatureExtractor,
)

SYMBOL = Symbol(name="BTCUSD", asset_class=AssetClass.CRYPTO)
OTHER = Symbol(name="ETHUSD", asset_class=AssetClass.CRYPTO)

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _bar(
    close: str,
    index: int = 0,
    symbol: Symbol = SYMBOL,
    volume: str = "1000",
) -> MarketBar:
    price = Decimal(close)
    return MarketBar(
        symbol=symbol,
        timeframe=TimeFrame.M1,
        timestamp=BASE + timedelta(minutes=index),
        open=price,
        high=price + Decimal("1"),
        low=price - Decimal("1"),
        close=price,
        volume=Decimal(volume),
    )


def _provider() -> RollingFeatureProvider:
    return RollingFeatureProvider(extractor=TechnicalFeatureExtractor())


def _feed(provider: RollingFeatureProvider, closes: list[str]) -> dict[str, float]:
    features: dict[str, float] = {}
    for index, close in enumerate(closes):
        features = provider.observe_bar(_bar(close, index))
    return features


class TestKeysMatchWhatAgentsRead:
    def test_trend_agent_key_is_provided(self) -> None:
        features = _feed(_provider(), [str(100 + i) for i in range(60)])

        # L'agent lit `ema_50`, pas `ema_distance`.
        assert "ema_50" in features
        assert features["ema_50"] > 0.0

    def test_momentum_agent_key_is_provided_unsuffixed(self) -> None:
        """L'extracteur produit `rsi_14` ; l'agent lit `rsi`.

        La traduction est faite ici, en un seul endroit, plutôt qu'en renommant
        la clé dans cinq agents : le nom lu par les agents est le contrat.
        """
        features = _feed(_provider(), [str(100 + i) for i in range(60)])

        assert "rsi" in features
        assert 0.0 <= features["rsi"] <= 100.0

    def test_volatility_agent_keys_are_provided(self) -> None:
        features = _feed(_provider(), [str(100 + i) for i in range(60)])

        assert features["bb_upper"] > features["bb_lower"]

    def test_liquidity_agent_volume_key_is_the_observed_volume(self) -> None:
        provider = _provider()
        provider.observe_bar(_bar("100", 0, volume="4321"))

        features = provider.observe_bar(_bar("101", 1, volume="8765"))

        assert features["volume"] == pytest.approx(8765.0)

    def test_dead_placeholder_keys_are_not_produced(self) -> None:
        """Les huit `*_score` ne sont lus par aucun agent."""
        features = _feed(_provider(), [str(100 + i) for i in range(60)])

        for dead in (
            "trend_score",
            "momentum_score",
            "volatility_score",
            "liquidity_score",
            "pattern_score",
            "news_score",
            "portfolio_risk",
            "execution_cost",
        ):
            assert dead not in features


class TestValuesAreComputedNotConstant:
    def test_rsi_reacts_to_a_pure_uptrend(self) -> None:
        """Que des hausses : RSI proche de 100, donc > 70 (zone SELL).

        Un RSI constant à 55 restait dans la bande neutre 30-70 : le
        MomentumAgent ne pouvait mathématiquement jamais voter autre chose que
        WAIT.
        """
        features = _feed(_provider(), [str(100 + i) for i in range(60)])

        assert features["rsi"] > 70.0

    def test_rsi_reacts_to_a_pure_downtrend(self) -> None:
        features = _feed(_provider(), [str(200 - i) for i in range(60)])

        assert features["rsi"] < 30.0

    def test_ema_lags_a_rising_price(self) -> None:
        features = _feed(_provider(), [str(100 + i) for i in range(60)])

        # Prix courant 159, EMA 50 en retard : le TrendAgent doit voir
        # price > ema * 1.001.
        assert features["ema_50"] < 159.0

    def test_features_change_between_two_different_ticks(self) -> None:
        provider = _provider()
        first = dict(_feed(provider, [str(100 + i) for i in range(60)]))

        # Retournement franc, et non une hausse de plus : après 60 hausses
        # consécutives le RSI est saturé à 100 et y resterait légitimement.
        second = provider.observe_bar(_bar("120", 60))

        assert second["ema_50"] != first["ema_50"]
        assert second["rsi"] < first["rsi"]


class TestWarmUpIsHonest:
    def test_undefined_features_are_omitted_rather_than_zeroed(self) -> None:
        """Avant 20 barres les bandes n'existent pas.

        Les renvoyer à 0.0 mettrait le prix au-dessus de `bb_upper` et ferait
        voter SELL au VolatilityAgent sur une bande inexistante. Absentes, les
        agents votent WAIT — ce qui est leur comportement correct sans donnée.
        """
        features = _feed(_provider(), ["100", "101", "102"])

        assert "bb_upper" not in features
        assert "bb_lower" not in features

    def test_nan_is_never_published(self) -> None:
        import math

        features = _feed(_provider(), ["100", "101"])

        for name, value in features.items():
            assert not math.isnan(value), f"{name} est NaN"

    def test_first_bar_still_yields_the_price_features(self) -> None:
        provider = _provider()

        features = provider.observe_bar(_bar("100", 0))

        assert features["ema_50"] == pytest.approx(100.0)
        assert features["volume"] == pytest.approx(1000.0)


class TestOptionalSourcesAreOnlyPublishedWhenReal:
    def test_spread_is_absent_without_an_observed_tick(self) -> None:
        """`MarketBar` ne porte pas de bid/ask.

        Dériver un spread d'un bar serait remplacer un placeholder par un
        autre. Sans tick réel, la clé n'est pas publiée.
        """
        features = _feed(_provider(), [str(100 + i) for i in range(30)])

        assert "spread" not in features

    def test_spread_comes_from_the_observed_tick(self) -> None:
        provider = _provider()
        provider.observe_tick(
            Tick(
                symbol=SYMBOL,
                timestamp=BASE,
                bid=Decimal("99.5"),
                ask=Decimal("100.5"),
            )
        )

        features = provider.observe_bar(_bar("100", 0))

        assert features["spread"] == pytest.approx(1.0)

    def test_broker_latency_is_absent_before_any_measurement(self) -> None:
        features = _feed(_provider(), ["100", "101"])

        assert "broker_latency_ms" not in features

    def test_broker_latency_comes_from_a_measured_execution(self) -> None:
        provider = _provider()
        provider.observe_latency(243.0)

        features = provider.observe_bar(_bar("100", 0))

        assert features["broker_latency_ms"] == pytest.approx(243.0)

    def test_a_tick_on_another_symbol_does_not_leak_its_spread(self) -> None:
        provider = _provider()
        provider.observe_tick(
            Tick(
                symbol=OTHER,
                timestamp=BASE,
                bid=Decimal("10.0"),
                ask=Decimal("30.0"),
            )
        )

        features = provider.observe_bar(_bar("100", 0))

        assert "spread" not in features


class TestPerSymbolIsolation:
    def test_two_symbols_keep_separate_histories(self) -> None:
        provider = _provider()
        for index in range(40):
            provider.observe_bar(_bar(str(100 + index), index, symbol=SYMBOL))
            provider.observe_bar(_bar(str(500 - index), index, symbol=OTHER))

        rising = provider.features_for(SYMBOL)
        falling = provider.features_for(OTHER)

        assert rising["rsi"] > 70.0
        assert falling["rsi"] < 30.0

    def test_history_is_bounded(self) -> None:
        """Une session live tourne des semaines : la fenêtre doit être bornée."""
        provider = RollingFeatureProvider(
            extractor=TechnicalFeatureExtractor(), window=50
        )

        for index in range(500):
            provider.observe_bar(_bar(str(100 + index % 7), index))

        assert provider.history_size(SYMBOL) == 50

    def test_features_for_an_unknown_symbol_is_empty(self) -> None:
        assert _provider().features_for(SYMBOL) == {}
