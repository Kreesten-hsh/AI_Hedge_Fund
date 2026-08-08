"""Décompose le P&L d'un backtest en terme BRUT et terme COÛT.

Étape 1 du diagnostic SIG-02. Les ADR 0018→0023 ont travaillé un seul terme de
l'inégalité — le coût — avec rigueur. L'autre terme n'a jamais été isolé : le
rendement net de −14.97 % (Crash h5) et −16.87 % (Boom h10) mélange l'absence
éventuelle d'edge directionnel et le péage de la rotation. Les trois rejets
(SIG-01, Crash h5, Boom h10) sont donc tous inconcluants sur la question « le
signal existe-t-il ».

Verdict rendu par ce script :

- **brut ≤ 0** → pas d'edge directionnel. Le coût n'était pas le problème, et
  l'horizon, la marge et le modèle ne le sont pas non plus.
- **brut > 0** → l'edge existe mais la rotation le mange. Piste : moins de
  trades, plus gros.

Deux mesures, pas une, parce qu'aucune ne suffit seule :

**A — décomposition comptable.** Exacte et additive. `SimulatedBroker` prélève
`fill_price * quantity * commission_rate` (`simulated_broker.py:46-47`), et
`trades_history` enregistre `turnover = quantity * fill_price`
(`backtester.py:211`) : la commission de chaque exécution se reconstitue donc
sans instrumenter le broker, et `brut = net + commission` est une identité, pas
une estimation. Sa limite : les tailles de position observées sont celles d'un
capital déjà rongé par les frais.

**B — contrefactuel à péage nul.** Le même modèle, avec le même seuil d'entrée,
face à un broker sans frais. Répond à « qu'aurait gagné ce signal sans
friction ». Sa limite : le capital ne fond plus, donc le sizer engage des
montants différents et le résultat n'est PAS le terme brut de A. Les deux se
lisent ensemble, jamais l'un à la place de l'autre.

Le seuil d'entrée reste dérivé du coût RÉEL dans les deux runs. `MLStrategy`
refuse un coût nul (`ValueError` explicite), et surtout : changer le seuil
changerait la population de trades et la comparaison ne porterait plus sur le
même signal. Seul le péage du broker passe à zéro.

Aucun modèle n'est exporté : ce script mesure, il ne produit pas d'artefact
validable.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import stdev
from typing import Any, Dict, List, Sequence

from aegis_trade.application.strategy.ml_strategy import MLStrategy
from aegis_trade.domain.core import AssetClass, Symbol, TimeFrame
from aegis_trade.engine.backtester import Backtester
from aegis_trade.infrastructure.brokers.simulated_broker import SimulatedBroker
from aegis_trade.providers.qlib.dataset_builder import DatasetBuilder
from aegis_trade.providers.qlib.model_factory import ModelFactory
from aegis_trade.providers.qlib.predictor import QlibPredictor
from aegis_trade.providers.qlib.trainer import QlibTrainer
from train_qlib_model import (
    PRICE_KEY,
    ListDataFeed,
    build_feature_sets,
    load_bars,
    split_train_test,
)

logger = logging.getLogger("diagnose_pnl_decomposition")

REPO_ROOT = Path(__file__).resolve().parent.parent

# Tolérance de la réconciliation comptable, en dollars sur un capital de 100k.
# Le seul écart attendu est l'accumulation d'erreurs de représentation flottante
# sur quelques milliers d'exécutions ; au-delà, l'identité
# `capital_final = capital_initial + Σ pnl` est fausse et la décomposition ne
# décrit pas le run.
RECONCILIATION_TOLERANCE = 1e-6

# |t| au-delà duquel le brut cumulé est tenu pour distinguable de zéro. Le t
# calculé ici est déjà une borne SUPÉRIEURE (exécutions corrélées) : un |t| qui
# ne franchit pas ce seuil sur la borne optimiste ne le franchira sur aucune
# correction. Le seuil ne sert donc qu'à clore, jamais à conclure positivement.
SIGNIFICANCE_T = 2.0


@dataclass(frozen=True, slots=True)
class PnlDecomposition:
    """Décomposition additive du P&L réalisé d'un backtest.

    Toutes les valeurs monétaires sont en devise du compte. `gross_pnl` est le
    P&L de marché AVANT péage : c'est le terme qui répond à « y a-t-il un edge
    directionnel ». `net_pnl` est ce que le tearsheet rapporte.
    """

    executions: int
    rejected: int
    total_turnover: float
    total_commission: float
    gross_pnl: float
    net_pnl: float
    initial_capital: float
    # Dispersion du brut par exécution. Sans elle, un brut cumulé positif ne se
    # distingue pas d'une suite de coups favorables : c'est la même erreur que
    # lire un `dir_acc` in-sample comme une preuve de signal.
    gross_std_per_execution: float

    @property
    def gross_return(self) -> float:
        """P&L brut en fraction du capital initial."""
        return self.gross_pnl / self.initial_capital

    @property
    def cost_return(self) -> float:
        """Péage cumulé en fraction du capital initial."""
        return self.total_commission / self.initial_capital

    @property
    def net_return_realized(self) -> float:
        """P&L net réalisé en fraction du capital initial.

        Distinct du `total_return` du tearsheet, qui inclut le non-réalisé de la
        position éventuellement ouverte à la dernière barre.
        """
        return self.net_pnl / self.initial_capital

    @property
    def gross_mean_per_execution(self) -> float:
        """Brut moyen par exécution, en devise."""
        if self.executions == 0:
            return 0.0
        return self.gross_pnl / self.executions

    @property
    def gross_t_stat(self) -> float:
        """t de Student du brut moyen par exécution contre zéro.

        **Optimiste par construction, et de beaucoup.** Les exécutions ne sont pas
        indépendantes : elles vont par paires ouverture/fermeture, et les
        rendements à `horizon` barres se chevauchent. Le t réel est plus proche de
        cette valeur divisée par la racine du facteur de chevauchement. Sert de
        borne SUPÉRIEURE : un |t| déjà faible ici clôt la question, un |t| élevé
        ne prouve rien à lui seul.
        """
        if self.executions < 2 or self.gross_std_per_execution <= 0.0:
            return 0.0
        standard_error = self.gross_std_per_execution / math.sqrt(self.executions)
        return self.gross_mean_per_execution / standard_error

    @property
    def gross_bps_per_execution(self) -> float:
        """Brut par exécution, rapporté au notionnel transigé.

        C'est la seule échelle où le brut se compare au coût. Le cumul en % du
        capital ne le permet pas : il dépend du nombre de trades, que la
        comparaison cherche justement à neutraliser.
        """
        if self.total_turnover <= 0.0:
            return 0.0
        return (self.gross_pnl / self.total_turnover) * 10_000.0

    @property
    def has_directional_edge(self) -> bool:
        """Verdict de l'étape 1. Strict : un brut nul n'est pas un edge."""
        return self.gross_pnl > 0.0

    def to_report(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = asdict(self)
        payload.update(
            {
                "gross_return": self.gross_return,
                "cost_return": self.cost_return,
                "net_return_realized": self.net_return_realized,
                "gross_mean_per_execution": self.gross_mean_per_execution,
                "gross_t_stat": self.gross_t_stat,
                "gross_bps_per_execution": self.gross_bps_per_execution,
                "has_directional_edge": self.has_directional_edge,
            }
        )
        return payload


def decompose_pnl(
    trades: Sequence[Dict[str, Any]],
    commission_rate: float,
    initial_capital: float,
) -> PnlDecomposition:
    """Sépare le P&L réalisé en terme brut et terme coût.

    `trades` est le `trades_history` d'un `Backtester`. Chaque entrée est une
    EXÉCUTION, pas un aller-retour : 3618 lignes valent ~1809 allers-retours.

    L'identité exploitée est `commission = turnover * commission_rate`, vraie
    parce que le broker facture sur la valeur transigée au prix de fill et que
    le turnover est calculé sur ce même prix. Elle cesserait de tenir si un
    broker ajoutait un frais fixe par ordre : ce script rendrait alors un brut
    surévalué, silencieusement. La garde ci-dessous ne couvre pas ce cas — elle
    ne peut pas : la commission n'est pas enregistrée séparément dans
    `trades_history`. C'est la dette assumée de la mesure A.

    Les lignes rejetées par le risk manager (`rejected: True`) ne sont pas des
    exécutions : elles portent un turnover et un P&L nuls et sont comptées à
    part plutôt que gonfler le nombre d'exécutions.

    :raises ValueError: si `commission_rate` est négatif ou `initial_capital`
        non strictement positif — un rendement rapporté à un capital nul n'a
        pas de sens.
    """
    if commission_rate < 0.0:
        raise ValueError(f"commission_rate ne peut pas être négatif (reçu {commission_rate}).")
    if initial_capital <= 0.0:
        raise ValueError(
            f"initial_capital doit être strictement positif (reçu {initial_capital})."
        )

    executions = 0
    rejected = 0
    total_turnover = 0.0
    net_pnl = 0.0
    gross_per_execution: List[float] = []

    for trade in trades:
        if trade.get("rejected"):
            rejected += 1
            continue
        executions += 1
        turnover = float(trade["turnover"])
        pnl = float(trade["pnl"])
        total_turnover += turnover
        net_pnl += pnl
        # `pnl` est déjà net de commission (`backtester.py:210`) : le brut de
        # cette exécution se reconstitue en rajoutant son propre péage.
        gross_per_execution.append(pnl + turnover * commission_rate)

    total_commission = total_turnover * commission_rate

    return PnlDecomposition(
        executions=executions,
        rejected=rejected,
        total_turnover=total_turnover,
        total_commission=total_commission,
        gross_pnl=net_pnl + total_commission,
        net_pnl=net_pnl,
        initial_capital=initial_capital,
        gross_std_per_execution=(
            stdev(gross_per_execution) if len(gross_per_execution) > 1 else 0.0
        ),
    )


def reconcile(backtester: Backtester, decomposition: PnlDecomposition) -> float:
    """Écart entre le capital final du backtester et celui recomposé.

    Contrôle d'intégrité de la mesure A : si la somme des `pnl` de
    `trades_history` ne redonne pas le capital final, la décomposition ne décrit
    pas le run qui a produit les métriques de l'ADR, et le chiffre ne vaut rien.
    """
    expected = decomposition.initial_capital + decomposition.net_pnl
    return abs(backtester.capital - expected)


def run_backtest(
    strategy: MLStrategy,
    feature_sets: List[Any],
    symbol: Symbol,
    timeframe: TimeFrame,
    commission_rate: float,
    slippage_bps: float,
) -> tuple[Backtester, PnlDecomposition, float]:
    """Exécute un backtest et en rend la décomposition, avec son écart de réconciliation."""
    broker = SimulatedBroker(commission_rate=commission_rate, slippage_bps=slippage_bps)
    backtester = Backtester(
        data_feed=ListDataFeed(feature_sets),
        strategy=strategy,
        broker=broker,
    )
    tearsheet = backtester.run(symbol, timeframe)
    decomposition = decompose_pnl(
        trades=backtester.trades_history,
        commission_rate=commission_rate,
        initial_capital=backtester.initial_capital,
    )
    logger.info(
        "Backtest terminé (commission %.8f) : total_return tearsheet %.6f.",
        commission_rate,
        float(tearsheet.total_return),
    )
    return backtester, decomposition, reconcile(backtester, decomposition)


def _print_block(title: str, decomposition: PnlDecomposition, drift: float) -> None:
    print(f"\n  {title}")
    print(f"    exécutions            : {decomposition.executions}")
    if decomposition.rejected:
        print(f"    rejetées (risk)       : {decomposition.rejected}")
    print(f"    turnover cumulé       : {decomposition.total_turnover:,.2f}")
    print(
        f"    coût cumulé           : {decomposition.total_commission:,.2f}"
        f"  ({decomposition.cost_return * 100.0:+.4f} % du capital)"
    )
    print(
        f"    P&L BRUT              : {decomposition.gross_pnl:,.2f}"
        f"  ({decomposition.gross_return * 100.0:+.4f} %)"
    )
    print(
        f"      par exécution       : {decomposition.gross_bps_per_execution:+.4f} bps"
        f"  |  t = {decomposition.gross_t_stat:+.2f} (borne SUPÉRIEURE)"
    )
    print(
        f"    P&L net réalisé       : {decomposition.net_pnl:,.2f}"
        f"  ({decomposition.net_return_realized * 100.0:+.4f} %)"
    )
    print(f"    réconciliation        : écart {drift:.2e}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Décompose le P&L d'un backtest en brut / coût (étape 1 SIG-02)."
    )
    parser.add_argument("--symbol", default="CRASH1000")
    parser.add_argument("--timeframe", default="M1")
    parser.add_argument("--parquet", default="crash1000.parquet")
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--n-estimators", type=int, default=300)
    parser.add_argument(
        "--horizon",
        type=int,
        required=True,
        help="Horizon du label, en barres. 5 pour Crash 1000, 10 pour Boom 1000.",
    )
    parser.add_argument(
        "--commission-rate",
        type=float,
        required=True,
        help=(
            "Coût aller-retour par unité de notionnel. Obligatoire : le défaut de "
            "0.001 de train_qlib_model.py vaut ~40x le coût mesuré et fausserait "
            "la décomposition."
        ),
    )
    parser.add_argument("--slippage-bps", type=float, default=0.0)
    parser.add_argument("--safety-margin", type=float, default=1.0)
    parser.add_argument(
        "--json-out",
        default=None,
        help="Chemin d'écriture du rapport JSON. Rien n'est écrit si absent.",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        help=(
            "INFO produit ~34 Mo par run (une ligne par barre) : garder WARNING "
            "sauf investigation, et rediriger hors du dépôt."
        ),
    )
    args = parser.parse_args()

    # `force=True` est indispensable, pas défensif : importer `train_qlib_model`
    # exécute son `logging.basicConfig(level=INFO)` de niveau module AVANT
    # d'arriver ici, et un second appel sans `force` est un no-op silencieux. Sans
    # ça, `--log-level` ne fait rien et un run produit ~34 Mo de log (une ligne
    # par barre d'inférence).
    level = logging.getLevelName(args.log_level.upper())
    if not isinstance(level, int):
        raise SystemExit(f"Niveau de log inconnu : {args.log_level!r}.")
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,
    )

    symbol = Symbol(args.symbol, AssetClass.INDICES)
    timeframe = TimeFrame(args.timeframe)

    bars = load_bars(symbol, timeframe, args.parquet)
    feature_sets = build_feature_sets(bars)
    train_sets, test_sets = split_train_test(feature_sets, args.train_ratio)

    # Le modèle est réentraîné à l'identique plutôt que rechargé : aucun artefact
    # n'existe dans `data/models/` (export conditionnel, campagnes recalées). La
    # graine 42 de `LightGBMModel.DEFAULT_PARAMS` rend le run reproductible —
    # propriété déjà vérifiée sur la campagne Crash.
    builder = DatasetBuilder(price_key=PRICE_KEY, horizon=args.horizon)
    model = ModelFactory.create_model(
        "lightgbm", n_estimators=args.n_estimators, verbose=-1
    )
    report = QlibTrainer().train(model, builder.build_supervised(train_sets))

    real_cost = SimulatedBroker(
        commission_rate=args.commission_rate, slippage_bps=args.slippage_bps
    ).cost_model
    strategy = MLStrategy.from_cost_model(
        predictor=QlibPredictor(model),
        cost_model=real_cost,
        safety_margin=args.safety_margin,
    )

    # Mesure A : le run de référence, celui qui a produit les chiffres de l'ADR.
    _, actual, actual_drift = run_backtest(
        strategy, test_sets, symbol, timeframe, args.commission_rate, args.slippage_bps
    )
    # Mesure B : même seuil, péage nul. La stratégie est sans état, elle se
    # réutilise sans réinitialisation.
    _, frictionless, frictionless_drift = run_backtest(
        strategy, test_sets, symbol, timeframe, 0.0, 0.0
    )

    print("\n" + "=" * 70)
    print(f"  DÉCOMPOSITION P&L — {symbol.name} {timeframe.value} h{args.horizon}")
    print("=" * 70)
    print(
        f"  Coût A/R {real_cost.round_trip_cost * 10_000.0:.4f} bps"
        f"  |  Seuil {strategy.buy_threshold:.6f}"
        f"  |  {len(train_sets)} train / {len(test_sets)} test"
    )
    _print_block("A — run de référence (péage réel)", actual, actual_drift)
    _print_block("B — contrefactuel sans frais", frictionless, frictionless_drift)

    # Le brut par exécution est doublé : un aller-retour vaut deux exécutions, et
    # `round_trip_cost` est déjà budgété sur les deux jambes. Comparer un brut
    # par exécution à un coût par aller-retour surestimerait le péage d'un
    # facteur 2.
    gross_bps_round_trip = 2.0 * actual.gross_bps_per_execution
    cost_bps_round_trip = real_cost.round_trip_cost * 10_000.0

    print("\n  VERDICT (sur A, le seul terme additif)")
    print(
        f"    edge brut {gross_bps_round_trip:+.4f} bps/A-R"
        f"  contre coût {cost_bps_round_trip:.4f} bps/A-R"
    )
    print(
        f"    Significativité du brut : |t| <= {abs(actual.gross_t_stat):.2f}"
        " — borne supérieure, exécutions corrélées."
    )

    # Le SIGNE du brut est lu avant son ampleur, parce que c'est la question
    # binaire de l'étape 1. Mais un signe positif porté par un |t| sous 2 ne dit
    # rien : c'est la même erreur que lire un `dir_acc` in-sample comme une
    # preuve de signal. L'ordre des trois branches ci-dessous est donc : brut
    # négatif (tranché), brut positif mais indistinct de zéro (non tranché),
    # brut positif et significatif (tranché dans l'autre sens).
    is_distinguishable = abs(actual.gross_t_stat) > SIGNIFICANCE_T

    if not actual.has_directional_edge:
        print("    BRUT <= 0 — PAS d'edge directionnel. Le coût n'était pas le")
        print("    problème ; l'horizon, la marge et le modèle ne le sont pas non plus.")
    elif not is_distinguishable:
        print("    BRUT > 0 de signe seulement : |t| est sous le seuil, le brut")
        print("    n'est PAS distinguable de zéro. Aucun edge n'est démontré — un")
        print("    cumul positif sur des trades corrélés se produit par hasard.")
        print(f"    Pour mémoire, le péage vaudrait {cost_bps_round_trip / gross_bps_round_trip:.1f}x")
        print("    ce brut : même réel, il ne financerait pas la rotation.")
    else:
        shortfall = cost_bps_round_trip / gross_bps_round_trip
        print("    BRUT > 0 et distinguable de zéro — un edge directionnel existe.")
        print(f"    Mais le péage vaut {shortfall:.1f}x l'edge : non finançable en l'état.")
        # « Trades plus gros » ne change RIEN : le brut et le coût sont tous deux
        # linéaires en notionnel, leur rapport est invariant d'échelle. Seule la
        # baisse du NOMBRE d'allers-retours à temps de marché égal réduit le
        # turnover, donc le péage — et encore, uniquement si le brut par trade ne
        # baisse pas proportionnellement. C'est une hypothèse à mesurer, pas une
        # conclusion de ce script.
        print("    Augmenter la taille ne peut pas aider : brut et coût sont tous")
        print("    deux linéaires en notionnel, leur rapport est invariant.")
        print("    Seule piste ouverte : moins d'allers-retours à temps de marché")
        print("    égal. À mesurer, pas à supposer.")
    print("=" * 70 + "\n")

    drift = max(actual_drift, frictionless_drift)
    if drift > RECONCILIATION_TOLERANCE:
        logger.error(
            "Réconciliation comptable échouée (écart %.6e > %.0e) : la "
            "décomposition ne décrit pas le run, le verdict est nul.",
            drift,
            RECONCILIATION_TOLERANCE,
        )
        return 1

    if args.json_out:
        payload = {
            "symbol": symbol.name,
            "timeframe": timeframe.value,
            "horizon": args.horizon,
            "commission_rate": args.commission_rate,
            "slippage_bps": args.slippage_bps,
            "safety_margin": args.safety_margin,
            "round_trip_bps": real_cost.round_trip_cost * 10_000.0,
            "buy_threshold": strategy.buy_threshold,
            "train_rows": len(train_sets),
            "test_rows": len(test_sets),
            "training_report": report,
            "actual": actual.to_report(),
            "frictionless": frictionless.to_report(),
        }
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        print(f"  Rapport écrit : {out_path}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
