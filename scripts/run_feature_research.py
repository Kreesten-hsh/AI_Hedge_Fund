"""IC / IR / stabilité par feature sur les séries réelles — étape 2 du diagnostic SIG-02.

L'étape « Recherche de features » du pipeline de `CLAUDE.md` n'a jamais tourné
sur Crash 1000 ni Boom 1000 : LightGBM a été entraîné sur 23 features dont le
pouvoir prédictif n'avait jamais été mesuré sur ces séries. Ce script pose la
question dans l'ordre — le signal existe-t-il, indépendamment du modèle et du
coût ?

**Le seul rapport d'Alpha Research existant est inutilisable** : il affiche
`ic_mean 0.9645` pour `macd_signal` sur BTCUSD D1. L'audit a tranché — ce n'est
pas une découverte, c'est une fuite de cible dans
`scripts/generate_dummy_features.py`, qui écrit le rendement de demain plus un
bruit dans cette colonne. Le `macd_signal` de `TechnicalFeatureExtractor` est
une vraie ligne de signal MACD ; le moteur n'était pas en cause, le jeu de
données de démonstration l'était.

**Mesuré sur TRAIN et TEST séparément, jamais sur le flux complet.** Découpage
chronologique identique à celui de la campagne SIG-02 (`--train-ratio 0.7`),
pour que les IC se lisent en regard des métriques de l'ADR. C'est aussi le seul
garde-fou contre les features de NIVEAU (`ema_50`, `bb_upper`, `vwap`,
`typical_price`) : sur une série qui dérive, un niveau se corrèle au temps, donc
à tout ce qui a une tendance. Un IC de niveau né de la dérive change de signe ou
s'effondre hors échantillon — la comparaison train/test le démasque sans qu'il
faille un test de stationnarité en plus.

Un IC ne se lit jamais seul ici : chaque ligne porte son nombre d'observations
EFFECTIVES (corrigé du chevauchement des rendements forward) et le t calculé
dessus. Lire un IC sans sa taille d'échantillon est la même faute que lire un
`dir_acc` in-sample comme une validation.

Aucun modèle n'est entraîné, aucun artefact n'est promu : ce script mesure.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence

from aegis_trade.domain.core import AssetClass, Symbol, TimeFrame
from aegis_trade.domain.features import FeatureSet
from aegis_trade.domain.research import FeatureScore, ResearchMetadata
from aegis_trade.infrastructure.research.research_engine import (
    SIGNIFICANCE_T,
    ResearchEngine,
)
from train_qlib_model import (
    PRICE_KEY,
    build_feature_sets,
    load_bars,
    split_train_test,
)

logger = logging.getLogger("run_feature_research")

REPO_ROOT = Path(__file__).resolve().parent.parent

# Colonnes exclues de l'évaluation. `close_price` est joint aux features par
# `build_feature_sets` pour que le Backtester valorise les positions ; ce n'est
# pas un signal candidat, et le laisser dans le classement noierait les vraies
# features sous un niveau de prix trivialement corrélé à lui-même.
NON_CANDIDATE_FEATURES = frozenset({PRICE_KEY})


@dataclass(frozen=True, slots=True)
class SegmentedScore:
    """Un même feature mesuré sur les deux segments, mis en regard.

    C'est la lecture qui décide : un IC qui ne survit pas au passage du train au
    test n'est pas un signal, quelle que soit sa taille sur le train.
    """

    feature_name: str
    ic_train: float
    ic_test: float
    t_test: float
    effective_test: int
    significant_test: bool
    ir_test: float
    stability_test: float

    @property
    def survives(self) -> bool:
        """Significatif hors échantillon ET de même signe qu'en apprentissage.

        Le signe compte autant que l'ampleur : une relation qui s'inverse d'un
        segment à l'autre est plus dangereuse qu'une relation absente, parce
        qu'elle se négocie à l'envers.
        """
        if not self.significant_test:
            return False
        return self.ic_train * self.ic_test > 0.0


def _strip_non_candidates(feature_sets: Sequence[FeatureSet]) -> List[FeatureSet]:
    """Retire les colonnes qui ne sont pas des signaux candidats.

    `return_1d` est CONSERVÉ : le moteur en a besoin pour reconstruire le chemin
    de prix et calculer les rendements forward. Il est évalué comme les autres,
    ce qui est légitime — un rendement passé est un candidat momentum/reversion
    aussi valable qu'un autre.
    """
    stripped: List[FeatureSet] = []
    for fset in feature_sets:
        features = {
            name: value
            for name, value in fset.features.items()
            if name not in NON_CANDIDATE_FEATURES
        }
        stripped.append(
            FeatureSet(
                symbol=fset.symbol,
                timeframe=fset.timeframe,
                timestamp=fset.timestamp,
                features=features,
            )
        )
    return stripped


def evaluate_segment(
    feature_sets: Sequence[FeatureSet],
    symbol: Symbol,
    timeframe: TimeFrame,
    horizon: int,
) -> Dict[str, FeatureScore]:
    """Évalue un segment et rend ses scores par feature."""
    if not feature_sets:
        raise ValueError("Segment vide : rien à évaluer.")

    metadata = ResearchMetadata(
        symbol=symbol,
        timeframe=timeframe,
        start_time=feature_sets[0].timestamp,
        end_time=feature_sets[-1].timestamp,
        forward_returns_lag=horizon,
    )
    result = ResearchEngine().evaluate(list(feature_sets), metadata)
    return result.feature_scores


def merge_segments(
    train_scores: Dict[str, FeatureScore],
    test_scores: Dict[str, FeatureScore],
) -> List[SegmentedScore]:
    """Apparie les scores des deux segments, triés par |IC test| décroissant.

    Le tri porte sur le TEST : classer sur le train reviendrait à sélectionner
    sur les données qui ont servi à ajuster le modèle, ce qui est précisément la
    faute que ce diagnostic instruit.
    """
    merged: List[SegmentedScore] = []
    for name, test_score in test_scores.items():
        train_score = train_scores.get(name)
        merged.append(
            SegmentedScore(
                feature_name=name,
                ic_train=train_score.ic_spearman if train_score else 0.0,
                ic_test=test_score.ic_spearman,
                t_test=test_score.ic_t_stat,
                effective_test=test_score.effective_observations,
                significant_test=test_score.is_significant,
                ir_test=test_score.ic_information_ratio,
                stability_test=test_score.stability,
            )
        )
    merged.sort(key=lambda score: abs(score.ic_test), reverse=True)
    return merged


def _print_table(scores: Sequence[SegmentedScore]) -> None:
    header = (
        f"  {'feature':<18} {'IC train':>9} {'IC test':>9} {'t test':>8} "
        f"{'n_eff':>7} {'IR test':>8} {'stab':>6}  verdict"
    )
    print(header)
    print("  " + "-" * (len(header) - 2))
    for score in scores:
        verdict = "SURVIT" if score.survives else ""
        if score.significant_test and not score.survives:
            verdict = "signe inversé"
        print(
            f"  {score.feature_name:<18} {score.ic_train:>+9.4f} {score.ic_test:>+9.4f} "
            f"{score.t_test:>+8.2f} {score.effective_test:>7d} "
            f"{score.ir_test:>+8.3f} {score.stability_test:>6.2f}  {verdict}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="IC / IR / stabilité par feature, train vs test (étape 2 SIG-02)."
    )
    parser.add_argument("--symbol", default="CRASH1000")
    parser.add_argument("--timeframe", default="M1")
    parser.add_argument("--parquet", default="crash1000.parquet")
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument(
        "--horizons",
        type=int,
        nargs="+",
        default=[5, 10],
        help="Horizons de rendement forward, en barres.",
    )
    parser.add_argument(
        "--json-out",
        default=None,
        help="Chemin d'écriture du rapport JSON. Rien n'est écrit si absent.",
    )
    parser.add_argument("--log-level", default="WARNING")
    args = parser.parse_args()

    # `force=True` : importer `train_qlib_model` exécute son
    # `logging.basicConfig(level=INFO)` de niveau module avant d'arriver ici, et
    # un second appel sans `force` est un no-op silencieux.
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
    feature_sets = _strip_non_candidates(build_feature_sets(bars))
    train_sets, test_sets = split_train_test(feature_sets, args.train_ratio)

    print("\n" + "=" * 96)
    print(f"  RECHERCHE DE FEATURES — {symbol.name} {timeframe.value}")
    print("=" * 96)
    print(
        f"  {len(train_sets)} barres train / {len(test_sets)} test"
        f"  |  seuil de significativité |t| > {SIGNIFICANCE_T}"
    )
    print(
        "  n_eff corrige le chevauchement des rendements forward (n / horizon)."
        "\n  « SURVIT » = significatif sur le TEST et de même signe que sur le train."
    )

    report: Dict[str, Any] = {
        "symbol": symbol.name,
        "timeframe": timeframe.value,
        "train_ratio": args.train_ratio,
        "train_rows": len(train_sets),
        "test_rows": len(test_sets),
        "significance_t": SIGNIFICANCE_T,
        "horizons": {},
    }

    survivors_total = 0
    for horizon in args.horizons:
        train_scores = evaluate_segment(train_sets, symbol, timeframe, horizon)
        test_scores = evaluate_segment(test_sets, symbol, timeframe, horizon)
        merged = merge_segments(train_scores, test_scores)
        survivors = [score for score in merged if score.survives]
        survivors_total += len(survivors)

        print(f"\n  HORIZON {horizon} barres")
        _print_table(merged)
        print(f"\n    {len(survivors)}/{len(merged)} features survivent au test.")

        report["horizons"][str(horizon)] = {
            "survivors": [score.feature_name for score in survivors],
            "scores": [
                {
                    "feature": score.feature_name,
                    "ic_train": score.ic_train,
                    "ic_test": score.ic_test,
                    "t_test": score.t_test,
                    "effective_observations_test": score.effective_test,
                    "significant_test": score.significant_test,
                    "ir_test": score.ir_test,
                    "stability_test": score.stability_test,
                    "survives": score.survives,
                }
                for score in merged
            ],
        }

    print("\n  VERDICT")
    if survivors_total == 0:
        print("    AUCUNE feature ne porte de relation mesurable avec le rendement")
        print("    futur hors échantillon, à aucun des horizons testés. Entraîner un")
        print("    modèle sur ces features revient à ajuster du bruit : c'est le pas")
        print("    que le pipeline interdit, et il a été franchi.")
    else:
        print(f"    {survivors_total} couple(s) feature/horizon survivent au test.")
        print("    Ce n'est PAS un feu vert : aucune correction pour tests multiples")
        print("    n'est appliquée, et 23 features x 2 horizons produisent des |t| > 2")
        print("    par hasard seul. À confirmer sur un segment jamais touché.")
    print("=" * 96 + "\n")

    if args.json_out:
        report["survivors_total"] = survivors_total
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
        print(f"  Rapport écrit : {out_path}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
