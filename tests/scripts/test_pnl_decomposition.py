"""Décomposition brut/coût : arithmétique, gardes, et identité contre le vrai broker.

Le test qui compte est `test_commission_identity_holds_against_real_broker` : la
mesure A repose entièrement sur `commission = turnover * commission_rate`, une
identité déduite du code de `SimulatedBroker` et NON vérifiée par la
décomposition elle-même (la commission n'est pas enregistrée dans
`trades_history`). Si le broker change sa facturation — frais fixe par ordre,
palier de volume — le script rendrait un brut faux sans rien signaler. Ce test
est le seul garde-fou de cette hypothèse.

Aucun modèle, aucun parquet, aucun réseau : flux de FeatureSets en mémoire.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterator, List, Optional

import pytest

from aegis_trade.domain.core import AssetClass, Symbol, TimeFrame
from aegis_trade.domain.execution import FillEvent, OrderIntent
from aegis_trade.domain.features import FeatureSet
from aegis_trade.domain.ports.data_feed import IDataFeed
from aegis_trade.domain.signal import Signal
from aegis_trade.domain.strategy import IStrategy
from aegis_trade.engine.backtester import Backtester
from aegis_trade.infrastructure.brokers.simulated_broker import SimulatedBroker
from scripts.diagnose_pnl_decomposition import decompose_pnl, reconcile

SYMBOL = Symbol("CRASH1000", AssetClass.INDICES)
TIMEFRAME = TimeFrame.M1
INITIAL_CAPITAL = 100_000.0


def _trade(pnl: float, turnover: float) -> Dict[str, Any]:
    return {"timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc), "pnl": pnl, "turnover": turnover, "exposure": 1}


class _AlternatingStrategy(IStrategy):
    """Retourne l'exposition à chaque barre : force un aller-retour par paire.

    Une stratégie qui garderait sa position ne produirait qu'une poignée
    d'exécutions et testerait mal une identité qui porte sur leur cumul.
    """

    def __init__(self) -> None:
        self._direction = 1

    def generate_signals(self, features: FeatureSet) -> List[Signal]:
        signal = Signal(
            symbol=features.symbol,
            direction=self._direction,
            strength=1.0,
            timestamp=features.timestamp,
        )
        self._direction = -self._direction
        return [signal]


class _RecordingBroker(SimulatedBroker):
    """`SimulatedBroker` qui conserve la commission réellement prélevée.

    C'est la valeur de référence : la décomposition la RECONSTITUE depuis le
    turnover, elle ne la lit jamais.
    """

    def __init__(self, commission_rate: float, slippage_bps: float) -> None:
        super().__init__(commission_rate=commission_rate, slippage_bps=slippage_bps)
        self.commissions: List[float] = []

    def execute_order(self, order: OrderIntent) -> Optional[FillEvent]:
        fill = super().execute_order(order)
        if fill is not None:
            self.commissions.append(fill.commission)
        return fill


class _ListFeed(IDataFeed):
    def __init__(self, feature_sets: List[FeatureSet]) -> None:
        self._feature_sets = feature_sets

    def get_feature_stream(
        self, symbol: Symbol, timeframe: TimeFrame
    ) -> Iterator[FeatureSet]:
        return iter(self._feature_sets)


def _price_series(prices: List[float]) -> List[FeatureSet]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        FeatureSet(
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            timestamp=start + timedelta(minutes=index),
            features={"close_price": price},
        )
        for index, price in enumerate(prices)
    ]


class TestDecomposeArithmetic:
    def test_gross_is_net_plus_commission(self) -> None:
        # 10 000 de turnover à 1 % = 100 de commission. Le pnl enregistré est
        # déjà net : un brut de 250 se présente donc comme un net de 150.
        result = decompose_pnl(
            trades=[_trade(pnl=150.0, turnover=10_000.0)],
            commission_rate=0.01,
            initial_capital=INITIAL_CAPITAL,
        )

        assert result.total_commission == pytest.approx(100.0)
        assert result.net_pnl == pytest.approx(150.0)
        assert result.gross_pnl == pytest.approx(250.0)
        assert result.executions == 1

    def test_returns_are_fractions_of_initial_capital(self) -> None:
        result = decompose_pnl(
            trades=[_trade(pnl=-1_000.0, turnover=200_000.0)],
            commission_rate=0.005,
            initial_capital=INITIAL_CAPITAL,
        )

        assert result.total_commission == pytest.approx(1_000.0)
        assert result.cost_return == pytest.approx(0.01)
        assert result.net_return_realized == pytest.approx(-0.01)
        # Brut exactement nul : le péage explique toute la perte.
        assert result.gross_return == pytest.approx(0.0)

    def test_zero_gross_is_not_an_edge(self) -> None:
        """Le verdict est strict : un brut nul ne finance aucune rotation."""
        result = decompose_pnl(
            trades=[_trade(pnl=-100.0, turnover=10_000.0)],
            commission_rate=0.01,
            initial_capital=INITIAL_CAPITAL,
        )

        assert result.gross_pnl == pytest.approx(0.0)
        assert result.has_directional_edge is False

    def test_positive_gross_is_an_edge(self) -> None:
        result = decompose_pnl(
            trades=[_trade(pnl=-99.0, turnover=10_000.0)],
            commission_rate=0.01,
            initial_capital=INITIAL_CAPITAL,
        )

        assert result.gross_pnl == pytest.approx(1.0)
        assert result.has_directional_edge is True

    def test_rejected_orders_are_not_executions(self) -> None:
        """Une ligne rejetée par le risk manager n'a rien exécuté."""
        rejected: Dict[str, Any] = {
            "timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "pnl": 0.0,
            "turnover": 0.0,
            "exposure": 0,
            "rejected": True,
            "reason": "max exposure",
        }
        result = decompose_pnl(
            trades=[_trade(pnl=10.0, turnover=1_000.0), rejected],
            commission_rate=0.01,
            initial_capital=INITIAL_CAPITAL,
        )

        assert result.executions == 1
        assert result.rejected == 1
        assert result.total_turnover == pytest.approx(1_000.0)

    def test_empty_history_decomposes_to_zero(self) -> None:
        result = decompose_pnl(
            trades=[], commission_rate=0.01, initial_capital=INITIAL_CAPITAL
        )

        assert result.executions == 0
        assert result.gross_pnl == pytest.approx(0.0)
        assert result.has_directional_edge is False

    def test_zero_commission_leaves_net_equal_to_gross(self) -> None:
        """Le contrefactuel B : sans péage, les deux termes se confondent."""
        result = decompose_pnl(
            trades=[_trade(pnl=500.0, turnover=50_000.0)],
            commission_rate=0.0,
            initial_capital=INITIAL_CAPITAL,
        )

        assert result.total_commission == pytest.approx(0.0)
        assert result.gross_pnl == pytest.approx(result.net_pnl)

    def test_negative_commission_rate_is_refused(self) -> None:
        with pytest.raises(ValueError, match="commission_rate"):
            decompose_pnl(trades=[], commission_rate=-0.001, initial_capital=INITIAL_CAPITAL)

    def test_non_positive_capital_is_refused(self) -> None:
        with pytest.raises(ValueError, match="initial_capital"):
            decompose_pnl(trades=[], commission_rate=0.001, initial_capital=0.0)


class TestSignificanceAndScale:
    """Le brut cumulé ne suffit pas : il faut son échelle et sa dispersion."""

    def test_gross_bps_is_measured_against_turnover(self) -> None:
        """Le brut par exécution se rapporte au notionnel, pas au capital.

        C'est la seule échelle comparable au coût : le cumul en % du capital
        dépend du nombre de trades, que la comparaison veut neutraliser.
        """
        # 100 de brut sur 1 000 000 de turnover = 1 bp.
        result = decompose_pnl(
            trades=[_trade(pnl=100.0, turnover=1_000_000.0)],
            commission_rate=0.0,
            initial_capital=INITIAL_CAPITAL,
        )

        assert result.gross_bps_per_execution == pytest.approx(1.0)

    def test_gross_bps_is_zero_without_turnover(self) -> None:
        result = decompose_pnl(
            trades=[], commission_rate=0.0, initial_capital=INITIAL_CAPITAL
        )

        assert result.gross_bps_per_execution == pytest.approx(0.0)

    def test_identical_trades_have_no_dispersion(self) -> None:
        """Un brut constant a un écart-type nul, donc aucun t exploitable."""
        trades = [_trade(pnl=10.0, turnover=1_000.0) for _ in range(5)]
        result = decompose_pnl(
            trades=trades, commission_rate=0.0, initial_capital=INITIAL_CAPITAL
        )

        assert result.gross_std_per_execution == pytest.approx(0.0)
        assert result.gross_t_stat == pytest.approx(0.0)

    def test_t_stat_grows_with_sample_at_equal_dispersion(self) -> None:
        """Même moyenne, même dispersion, plus d'observations → t plus grand."""
        pattern = [12.0, 8.0]
        small = [_trade(pnl=value, turnover=1_000.0) for value in pattern * 5]
        large = [_trade(pnl=value, turnover=1_000.0) for value in pattern * 50]

        t_small = decompose_pnl(small, 0.0, INITIAL_CAPITAL).gross_t_stat
        t_large = decompose_pnl(large, 0.0, INITIAL_CAPITAL).gross_t_stat

        assert t_large > t_small > 0.0

    def test_t_stat_is_negative_for_losing_gross(self) -> None:
        trades = [_trade(pnl=-12.0, turnover=1_000.0), _trade(pnl=-8.0, turnover=1_000.0)]
        result = decompose_pnl(trades, 0.0, INITIAL_CAPITAL)

        assert result.gross_t_stat < 0.0

    def test_single_execution_yields_no_t_stat(self) -> None:
        """Un seul trade ne porte aucune dispersion : le t n'est pas défini."""
        result = decompose_pnl(
            trades=[_trade(pnl=10.0, turnover=1_000.0)],
            commission_rate=0.0,
            initial_capital=INITIAL_CAPITAL,
        )

        assert result.executions == 1
        assert result.gross_t_stat == pytest.approx(0.0)

    def test_dispersion_is_computed_on_gross_not_net(self) -> None:
        """La dispersion porte sur le brut : deux trades de même net mais de
        turnover différent n'ont pas le même brut, donc pas un écart-type nul."""
        trades = [
            _trade(pnl=10.0, turnover=1_000.0),
            _trade(pnl=10.0, turnover=100_000.0),
        ]
        result = decompose_pnl(trades, commission_rate=0.01, initial_capital=INITIAL_CAPITAL)

        assert result.gross_std_per_execution > 0.0


class TestIdentityAgainstRealBroker:
    def test_commission_identity_holds_against_real_broker(self) -> None:
        """`turnover * rate` doit redonner la commission RÉELLEMENT prélevée.

        Toute la mesure A repose sur cette égalité. Elle est vérifiée ici sur un
        run complet du vrai `Backtester` et du vrai `SimulatedBroker`, pas sur
        des dictionnaires fabriqués.
        """
        feed = _ListFeed(_price_series([100.0 + index * 0.5 for index in range(40)]))
        broker = _RecordingBroker(commission_rate=0.0001, slippage_bps=0.0)
        backtester = Backtester(
            data_feed=feed,
            strategy=_AlternatingStrategy(),
            broker=broker,
            starting_capital=INITIAL_CAPITAL,
        )
        backtester.run(SYMBOL, TIMEFRAME)

        assert broker.commissions, "Le scénario doit produire des exécutions."

        result = decompose_pnl(
            trades=backtester.trades_history,
            commission_rate=broker.commission_rate,
            initial_capital=INITIAL_CAPITAL,
        )

        assert result.executions == len(broker.commissions)
        assert result.total_commission == pytest.approx(sum(broker.commissions))

    def test_slippage_is_not_counted_as_commission(self) -> None:
        """Le slippage déforme le prix de fill, il n'est pas facturé à part.

        Le turnover est calculé sur le prix APRÈS slippage : l'identité tient
        toujours. Sans ce test, un futur passage à `--slippage-bps` non nul
        pourrait faire croire à une fuite de coût dans le brut.
        """
        feed = _ListFeed(_price_series([100.0 + index * 0.5 for index in range(40)]))
        broker = _RecordingBroker(commission_rate=0.0001, slippage_bps=5.0)
        backtester = Backtester(
            data_feed=feed,
            strategy=_AlternatingStrategy(),
            broker=broker,
            starting_capital=INITIAL_CAPITAL,
        )
        backtester.run(SYMBOL, TIMEFRAME)

        result = decompose_pnl(
            trades=backtester.trades_history,
            commission_rate=broker.commission_rate,
            initial_capital=INITIAL_CAPITAL,
        )

        assert result.total_commission == pytest.approx(sum(broker.commissions))

    def test_reconciliation_closes_on_a_real_run(self) -> None:
        """La somme des `pnl` doit redonner le capital final du backtester."""
        feed = _ListFeed(_price_series([100.0 + index * 0.5 for index in range(40)]))
        broker = _RecordingBroker(commission_rate=0.0001, slippage_bps=0.0)
        backtester = Backtester(
            data_feed=feed,
            strategy=_AlternatingStrategy(),
            broker=broker,
            starting_capital=INITIAL_CAPITAL,
        )
        backtester.run(SYMBOL, TIMEFRAME)

        result = decompose_pnl(
            trades=backtester.trades_history,
            commission_rate=broker.commission_rate,
            initial_capital=INITIAL_CAPITAL,
        )

        assert reconcile(backtester, result) < 1e-6
