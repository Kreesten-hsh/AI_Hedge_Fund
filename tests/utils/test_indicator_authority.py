"""Non-régression numérique de l'ATR — Lot 3, souveraineté des grandeurs.

Quatre implémentations divergentes de l'ATR coexistaient dans le code. Mesurées
contre la référence Wilder 1978 (« New Concepts in Technical Trading Systems »)
sur 120 barres synthétiques :

    utils/math.compute_atr            écart  0.00 %   (référence)
    technical_extractor  ewm(1/14)    écart -0.00 % mais 14 barres de warmup
                                      servies sans NaN, donc fausses
    reflection/extractor rolling(14)  écart +6.61 %  (moyenne simple du True
                                      Range, pas un lissage de Wilder)
    ai_decision_engine   mean(H-L)    écart -9.49 %  (aucun True Range : les
                                      gaps entre barres sont ignorés)

Ce test verrouille le critère de sortie du Lot 3 : mêmes entrées, même sortie,
quel que soit l'appelant qui calcule la grandeur.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd
import pytest

from aegis_trade.application.reflection.extractor import LiveFeatureExtractor
from aegis_trade.application.reflection.snapshot import RichMarketSnapshot
from aegis_trade.domain.core import AssetClass, MarketBar, Symbol, TimeFrame
from aegis_trade.engine.ai_decision_engine import ATR_PERIOD, AiDecisionEngine
from aegis_trade.engine.events import MarketEvent
from aegis_trade.infrastructure.features.technical_extractor import (
    TechnicalFeatureExtractor,
)
from aegis_trade.utils.math import compute_atr

PERIOD = 14
SYMBOL = Symbol("XAUUSD", AssetClass.COMMODITIES)


def reference_wilder_atr(
    highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int
) -> np.ndarray:
    """Référence indépendante, écrite depuis la formule publiée.

    Volontairement naïve et non factorisée : elle ne partage aucune ligne avec
    `utils.math`, sinon elle validerait le code par lui-même.

        TR_0   = H_0 - L_0
        TR_i   = max(H_i - L_i, |H_i - C_{i-1}|, |L_i - C_{i-1}|)
        ATR_{p-1} = moyenne(TR_0 .. TR_{p-1})
        ATR_i  = (ATR_{i-1} * (p - 1) + TR_i) / p
    """
    tr = [highs[0] - lows[0]]
    for i in range(1, len(highs)):
        tr.append(
            max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
        )
    atr = np.full(len(tr), np.nan)
    atr[period - 1] = float(np.mean(tr[:period]))
    for i in range(period, len(tr)):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr


def synthetic_bars(n: int) -> list[MarketBar]:
    """Marche aléatoire déterministe, arrondie pour un aller-retour Decimal exact.

    Les prix passent par `Decimal(str(...))` : sans arrondi préalable, la
    conversion `Decimal -> float` opérée par les extracteurs réintroduirait un
    écart de représentation qui masquerait ou fabriquerait une divergence.
    """
    rng = np.random.default_rng(42)
    closes = 2000.0 + np.cumsum(rng.normal(0, 1.0, n))
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)

    bars = []
    for i in range(n):
        close = round(float(closes[i]), 6)
        open_ = round(close + float(rng.normal(0, 0.4)), 6)
        high = round(max(open_, close) + abs(float(rng.normal(0, 0.8))), 6)
        low = round(min(open_, close) - abs(float(rng.normal(0, 0.8))), 6)
        bars.append(
            MarketBar(
                symbol=SYMBOL,
                timeframe=TimeFrame.H1,
                timestamp=start + timedelta(hours=i),
                open=Decimal(str(open_)),
                high=Decimal(str(high)),
                low=Decimal(str(low)),
                close=Decimal(str(close)),
                volume=Decimal("1000"),
            )
        )
    return bars


def ohlc_arrays(bars: list[MarketBar]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return (
        np.array([float(b.high) for b in bars]),
        np.array([float(b.low) for b in bars]),
        np.array([float(b.close) for b in bars]),
    )


def history_frame(bars: list[MarketBar]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "timestamp": b.timestamp,
                "open": float(b.open),
                "high": float(b.high),
                "low": float(b.low),
                "close": float(b.close),
                "volume": float(b.volume),
            }
            for b in bars
        ]
    )


# ---------------------------------------------------------------------------
# 1. L'autorité est conforme à la référence publiée
# ---------------------------------------------------------------------------


def test_compute_atr_matches_independent_wilder_reference() -> None:
    bars = synthetic_bars(120)
    highs, lows, closes = ohlc_arrays(bars)

    result = compute_atr(highs, lows, closes, PERIOD)
    expected = reference_wilder_atr(highs, lows, closes, PERIOD)

    np.testing.assert_allclose(result, expected, rtol=0, atol=1e-12)


def test_compute_atr_warmup_is_explicitly_nan() -> None:
    """Les `period - 1` premières valeurs sont NaN, pas des nombres approximatifs.

    Une valeur calculée sur un échantillon incomplet est fausse et rien en aval
    ne saurait la distinguer d'une valeur établie : le NaN est le seul signal
    qu'un consommateur peut vérifier.
    """
    bars = synthetic_bars(40)
    highs, lows, closes = ohlc_arrays(bars)

    atr = compute_atr(highs, lows, closes, PERIOD)

    assert np.isnan(atr[: PERIOD - 1]).all()
    assert not np.isnan(atr[PERIOD - 1 :]).any()
    first_valid = int(np.flatnonzero(~np.isnan(atr))[0])
    assert first_valid == PERIOD - 1


def test_compute_atr_rejects_non_positive_period() -> None:
    bars = synthetic_bars(20)
    highs, lows, closes = ohlc_arrays(bars)

    with pytest.raises(ValueError):
        compute_atr(highs, lows, closes, 0)


def test_compute_atr_returns_all_nan_when_history_is_shorter_than_period() -> None:
    bars = synthetic_bars(PERIOD - 1)
    highs, lows, closes = ohlc_arrays(bars)

    atr = compute_atr(highs, lows, closes, PERIOD)

    assert atr.shape == (PERIOD - 1,)
    assert np.isnan(atr).all()


# ---------------------------------------------------------------------------
# 2. Les trois appelants produisent le même nombre que l'autorité
# ---------------------------------------------------------------------------


def test_technical_extractor_atr_matches_authority() -> None:
    bars = synthetic_bars(120)
    highs, lows, closes = ohlc_arrays(bars)
    expected = reference_wilder_atr(highs, lows, closes, PERIOD)

    feature_sets = TechnicalFeatureExtractor().extract(bars)
    produced = np.array(
        [
            np.nan if fs.features["atr_14"] is None else fs.features["atr_14"]
            for fs in feature_sets
        ]
    )

    np.testing.assert_allclose(produced, expected, rtol=0, atol=1e-12)
    # Le warmup remonte jusqu'au FeatureStore sous forme de None, pas de 0.0 :
    # une volatilité nulle serait consommée comme une volatilité mesurée.
    assert all(fs.features["atr_14"] is None for fs in feature_sets[: PERIOD - 1])


def test_live_feature_extractor_atr_matches_authority() -> None:
    bars = synthetic_bars(120)
    highs, lows, closes = ohlc_arrays(bars)
    expected = reference_wilder_atr(highs, lows, closes, PERIOD)

    snapshot = RichMarketSnapshot(
        symbol=SYMBOL,
        timestamp=bars[-1].timestamp,
        latest_bar=bars[-1],
        history=history_frame(bars),
    )
    features = LiveFeatureExtractor().extract(snapshot)

    assert features.atr == pytest.approx(expected[-1], abs=1e-12)


def test_ai_decision_engine_atr_matches_authority() -> None:
    """L'`AiDecisionEngine` n'a plus d'ATR à lui : il consomme l'autorité.

    L'historique est borné par la deque du moteur ; la référence est donc
    calculée sur exactement les mêmes barres que celles qu'il conserve.
    """
    engine = AiDecisionEngine(orchestrator=object(), window_size=5)  # type: ignore[arg-type]
    kept = engine._history.maxlen
    assert kept is not None

    bars = synthetic_bars(kept)
    for bar in bars:
        engine.on_market_event(MarketEvent(timestamp=bar.timestamp, bar=bar))

    highs, lows, closes = ohlc_arrays(bars)
    expected = reference_wilder_atr(highs, lows, closes, ATR_PERIOD)
    valid = expected[~np.isnan(expected)]

    stats = engine._atr_stats()
    assert stats is not None
    current_atr, avg_atr = stats

    assert current_atr == pytest.approx(float(valid[-1]), abs=1e-12)
    assert avg_atr == pytest.approx(float(valid.mean()), abs=1e-12)


def test_ai_decision_engine_refuses_to_fabricate_an_atr() -> None:
    """En deçà de `ATR_PERIOD + 1` barres, le moteur renvoie None, pas un nombre.

    L'ancien `mean(high - low)` produisait une valeur dès la première barre et
    l'envoyait au Council sous la clé `atr` : un contexte de risque fabriqué.
    """
    engine = AiDecisionEngine(orchestrator=object(), window_size=5)  # type: ignore[arg-type]
    for bar in synthetic_bars(ATR_PERIOD):
        engine.on_market_event(MarketEvent(timestamp=bar.timestamp, bar=bar))

    assert engine._atr_stats() is None


# ---------------------------------------------------------------------------
# 3. Les formules retirées divergent — le test attraperait un retour en arrière
# ---------------------------------------------------------------------------


def test_removed_formulas_do_diverge_from_the_authority() -> None:
    """Preuve que la consolidation a corrigé un écart, pas dédupliqué du code identique.

    L'écart se mesure sur toute la série, pas sur la dernière barre : la moyenne
    simple oscille autour de Wilder et repasse périodiquement à son contact.
    Sur cette série elle ne dévie que de 0,6 % en fin de parcours alors qu'elle
    atteint 16 % au milieu — un test ancré sur `[-1]` laisserait donc passer un
    retour en arrière selon la graine tirée.
    """
    bars = synthetic_bars(120)
    highs, lows, closes = ohlc_arrays(bars)
    df = history_frame(bars)
    reference = reference_wilder_atr(highs, lows, closes, PERIOD)
    established = slice(PERIOD, None)

    prev_close = df["close"].shift(1)
    true_range = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    def max_relative_deviation(series: Any) -> float:
        deviation = np.abs(series[established] - reference[established])
        return float(np.nanmax(deviation / reference[established]))

    # technical_extractor : convergent asymptotiquement, mais sans amorce SMA il
    # démarre à l'indice 0 et sert PERIOD - 1 barres fausses sans NaN.
    ewm_atr = true_range.ewm(alpha=1 / PERIOD, adjust=False).mean().to_numpy()
    assert not np.isnan(ewm_atr[0])
    assert abs(ewm_atr[PERIOD - 1] - reference[PERIOD - 1]) > 0.01
    assert max_relative_deviation(ewm_atr) > 0.05

    # reflection/extractor : moyenne simple du True Range, pas un lissage.
    rolling_atr = true_range.rolling(PERIOD).mean().to_numpy()
    assert max_relative_deviation(rolling_atr) > 0.05

    # ai_decision_engine : aucun True Range, les gaps entre barres sont ignorés,
    # donc la volatilité est structurellement sous-estimée.
    naive_atr = np.array(
        [
            float(np.mean(highs[max(0, i - PERIOD + 1) : i + 1] - lows[max(0, i - PERIOD + 1) : i + 1]))
            for i in range(len(highs))
        ]
    )
    assert max_relative_deviation(naive_atr) > 0.05
    assert naive_atr[-1] < reference[-1]
