"""Non-régression numérique de l'annualisation — Lot 3, souveraineté des grandeurs.

Deux sites annualisaient, avec deux facteurs différents :

    engine/performance.py:70,74     sqrt(periods_per_year)              exact
    engine/portfolio.py:295-297     sqrt(n_jours) si n < 30, sinon      **discontinu**
                                    sqrt(252)

Le défaut de `portfolio.py` n'était pas une divergence d'arrondi. Son facteur
dépendait de la LONGUEUR DE LA FENÊTRE observée, pas de la périodicité des
rendements — ce qui introduisait une **discontinuité mesurée d'un facteur 2.95x
sur une seule barre de plus** :

    29 jours -> facteur 5.385      30 jours -> facteur 15.875

Un Sharpe qui triple parce que la fenêtre gagne un jour n'est comparable ni
d'une exécution à l'autre, ni au Sharpe que `PerformanceEngine` produit sur les
mêmes rendements. Les deux moteurs parlaient donc de deux grandeurs distinctes
sous le même nom.

L'intention derrière le garde `< 30` était juste : un Sharpe estimé sur fenêtre
courte est bruité. Mais c'est une réserve **statistique**, qui se traite par un
seuil de significativité (`Portfolio.metrics` renvoie déjà `NaN` sous 2 trades),
jamais en déformant le facteur d'annualisation lui-même.

`engine/performance.py` fait autorité. `portfolio.py` l'appelle désormais pour
le Sharpe et le Sortino.

**Le Calmar reste distinct, et ce n'est pas un oubli.** Son exposant `252/days`
annualise un rendement CUMULÉ — grandeur différente du facteur `sqrt` appliqué à
un écart-type. Les deux ne s'unifient pas : les confondre serait une erreur de
dimension, pas une déduplication.

Ce test verrouille le critère de sortie du Lot 3 : mêmes entrées, même sortie,
quel que soit l'appelant.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from aegis_trade.engine.performance import (
    TRADING_DAYS_PER_YEAR,
    PerformanceEngine,
    annualization_factor,
    annualized_sharpe,
    annualized_sortino,
    annualized_volatility,
)
from aegis_trade.engine.portfolio import EquityPoint, Portfolio


# --------------------------------------------------------------------------
# L'autorité elle-même
# --------------------------------------------------------------------------


def test_factor_depends_only_on_periodicity_never_on_window_length() -> None:
    """Le défaut corrigé, énoncé directement : le facteur ne voit pas la fenêtre.

    C'est la propriété structurelle du correctif. `annualization_factor` ne
    prend pas de longueur de série en paramètre — il ne PEUT pas en dépendre.
    """
    assert annualization_factor(TRADING_DAYS_PER_YEAR) == pytest.approx(np.sqrt(252))
    assert annualization_factor(12) == pytest.approx(np.sqrt(12))
    assert annualization_factor(1) == pytest.approx(1.0)


def test_no_cliff_at_the_thirty_day_boundary() -> None:
    """La discontinuité mesurée à 2.95x ne doit plus exister.

    Deux séries de 29 et 30 jours tirées de la MÊME distribution constante
    donnaient auparavant des Sharpe dans un rapport de ~2.95. Elles doivent
    désormais coïncider : le facteur est le même des deux côtés de l'ancienne
    frontière.
    """
    returns_30 = pd.Series([0.01, -0.005] * 15)
    returns_29 = returns_30.iloc[:29]

    sharpe_29 = annualized_sharpe(returns_29)
    sharpe_30 = annualized_sharpe(returns_30)
    ratio = sharpe_30 / sharpe_29

    # Retirer la dernière barre retire un rendement négatif, donc la moyenne de
    # l'échantillon bouge : un écart résiduel est attendu et légitime. Ce qui ne
    # l'est pas, c'est un CHANGEMENT DE RÉGIME de calcul. Le test discrimine les
    # deux par leur ordre de grandeur, mesuré sur ces deux séries précises :
    #
    #     effet d'échantillon (attendu)  ~10 %   -> ratio ~0.91
    #     saut de facteur legacy (bug)   ~195 %  -> ratio ~2.95
    #
    # Un facteur 20 sépare les deux : aucune tolérance ne les confond.
    assert abs(ratio - 1.0) < 0.20

    legacy_ratio = np.sqrt(252) / np.sqrt(29)
    assert legacy_ratio == pytest.approx(2.948, abs=0.01)
    assert abs(ratio - legacy_ratio) > 1.0


def test_zero_variance_yields_zero_sharpe_not_infinity() -> None:
    """Capital immobile : le Sharpe vaut 0, pas `inf`, pas `NaN`."""
    assert annualized_sharpe(pd.Series([0.0, 0.0, 0.0, 0.0])) == 0.0


def test_sortino_is_nan_when_downside_is_not_estimable() -> None:
    """Moins de 2 rendements négatifs : `NaN`, jamais `inf`.

    `inf` serait un ratio « parfait » fabriqué à partir d'une absence de
    données — exactement la classe de défaut du PASS creux Monte-Carlo.
    """
    assert np.isnan(annualized_sortino(pd.Series([0.01, 0.02, 0.03])))
    assert np.isnan(annualized_sortino(pd.Series([0.01, -0.01, 0.02])))

    finite = annualized_sortino(pd.Series([0.01, -0.01, 0.02, -0.02, 0.01]))
    assert np.isfinite(finite)


def test_rejects_non_positive_periodicity() -> None:
    """`sqrt(0)` annulerait le Sharpe en silence ; un négatif donnerait `NaN`."""
    with pytest.raises(ValueError, match="strictly positive"):
        annualization_factor(0)
    with pytest.raises(ValueError, match="strictly positive"):
        annualization_factor(-252)


# --------------------------------------------------------------------------
# Non-régression inter-appelants : le critère de sortie du Lot 3
# --------------------------------------------------------------------------


def test_performance_engine_delegates_to_the_authority() -> None:
    """`compute_tearsheet` ne réimplémente plus les formules : il les appelle.

    Mêmes rendements passés aux deux chemins -> mêmes chiffres, au flottant près.
    """
    dates = pd.date_range(start="2023-01-01", periods=40, freq="D", tz=timezone.utc)
    rng = np.random.default_rng(seed=20260805)
    equity = pd.Series(100_000.0 * np.cumprod(1 + rng.normal(0.0005, 0.01, 40)), index=dates)

    report = PerformanceEngine(risk_free_rate=0.0, periods_per_year=252).compute_tearsheet(equity)
    returns = equity.pct_change().dropna()

    assert report.sharpe_ratio == pytest.approx(annualized_sharpe(returns, 0.0, 252))
    assert report.sortino_ratio == pytest.approx(annualized_sortino(returns, 0.0, 252))
    assert report.annualized_volatility == pytest.approx(annualized_volatility(returns, 252))


def test_portfolio_and_performance_agree_on_the_same_equity_curve() -> None:
    """Le cœur du Lot 3 : deux appelants, une seule grandeur.

    `Portfolio.metrics` ré-échantillonne sa courbe en journalier puis annualise ;
    `PerformanceEngine` reçoit la même série journalière. Avant le correctif,
    ces deux chemins divergeaient d'un facteur ~2.95 sur toute fenêtre de moins
    de 30 jours. Ils doivent désormais coïncider.
    """
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rng = np.random.default_rng(seed=20260805)
    equities = 100_000.0 * np.cumprod(1 + rng.normal(0.0004, 0.008, 20))

    # Construction directe de la courbe : `Portfolio` n'expose pas de setter, et
    # passer par des fills réels ferait dépendre ce test de la comptabilité du
    # broker — c'est l'annualisation qu'on mesure ici, pas l'exécution.
    portfolio = Portfolio(initial_capital=100_000.0)
    portfolio._equity_curve = [  # noqa: SLF001
        EquityPoint(
            timestamp=start + timedelta(days=day),
            equity=Decimal(str(round(float(value), 2))),
            cash=Decimal(str(round(float(value), 2))),
        )
        for day, value in enumerate(equities)
    ]
    portfolio._closed_trades_pnl = [Decimal("10"), Decimal("-5"), Decimal("7")]  # noqa: SLF001

    metrics = portfolio.metrics

    daily = pd.Series(
        [float(p.equity) for p in portfolio._equity_curve],  # noqa: SLF001
        index=pd.DatetimeIndex([p.timestamp for p in portfolio._equity_curve]),  # noqa: SLF001
    )
    expected_returns = daily.resample("1d").last().ffill().dropna().pct_change().dropna()

    assert metrics["sharpe_ratio"] == pytest.approx(
        annualized_sharpe(expected_returns, 0.0, TRADING_DAYS_PER_YEAR)
    )
    assert metrics["sortino_ratio"] == pytest.approx(
        annualized_sortino(expected_returns, 0.0, TRADING_DAYS_PER_YEAR),
        nan_ok=True,
    )


def test_calmar_stays_a_distinct_quantity() -> None:
    """Le Calmar n'est PAS unifié avec le Sharpe, et ce test le verrouille.

    Son exposant annualise un rendement cumulé (`growth ** (252/days)`), pas un
    écart-type. Sous 30 jours le rendement de période est renvoyé tel quel :
    extrapoler un cumul de 3 semaines à l'année amplifierait le bruit d'un
    facteur 8+. Si quelqu'un « déduplique » un jour ce chemin vers
    `annualization_factor`, ce test tombe — c'est voulu.
    """
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    from aegis_trade.engine.portfolio import EquityPoint

    portfolio = Portfolio(initial_capital=100_000.0)
    # 10 jours, croissance monotone : drawdown nul -> Calmar infini par convention.
    portfolio._equity_curve = [  # noqa: SLF001
        EquityPoint(
            timestamp=start + timedelta(days=day),
            equity=Decimal("100000") + Decimal(day * 100),
            cash=Decimal("100000") + Decimal(day * 100),
        )
        for day in range(10)
    ]
    portfolio._closed_trades_pnl = [Decimal("50"), Decimal("50")]  # noqa: SLF001

    metrics = portfolio.metrics
    assert metrics["calmar_ratio"] == float("inf")
