"""Entraînement du modèle LightGBM sur données réelles + passage obligatoire des validateurs.

Contournement LightGBM-direct : `qlib.init()` est inatteignable tant que
`mlflow 1.27.0` est installé (qlib 0.9.7 importe `mlflow.exceptions`, absent de
cette distribution). L'entraînement passe donc par `lightgbm` directement, sur
les features du FeatureStore. Contournement temporaire, levé au Lot 5 après
upgrade de mlflow.

Le modèle n'est exporté QUE s'il passe les campagnes de validation. Un modèle
qui échoue laisse `data/models/` inchangé : aucun artefact non validé ne peut
être ramassé par erreur en aval.
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, Iterator, List

from aegis_trade.application.strategy.ml_strategy import MLStrategy
from aegis_trade.application.validation.config import ValidationConfig
from aegis_trade.application.validation.validation_runner import ValidationRunner
from aegis_trade.domain.core import AssetClass, MarketBar, Symbol, TimeFrame
from aegis_trade.domain.features import FeatureSet
from aegis_trade.domain.ports.data_feed import IDataFeed
from aegis_trade.domain.validation import ValidationCampaignType
from aegis_trade.engine.scoring_engine import ScoringEngine
from aegis_trade.infrastructure.brokers.simulated_broker import SimulatedBroker
from aegis_trade.infrastructure.data.parquet_storage import ParquetStorage
from aegis_trade.infrastructure.features.technical_extractor import (
    TechnicalFeatureExtractor,
)
from aegis_trade.infrastructure.validation.registry import ValidationRegistry
from aegis_trade.providers.qlib.dataset_builder import DatasetBuilder
from aegis_trade.providers.qlib.model_factory import LightGBMModel, ModelFactory
from aegis_trade.providers.qlib.predictor import QlibPredictor
from aegis_trade.providers.qlib.trainer import QlibTrainer

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("train_qlib_model")

REPO_ROOT = Path(__file__).resolve().parent.parent

# Clé de prix unique du pipeline : lue par le Backtester pour valoriser les
# positions, et par le DatasetBuilder pour construire le label forward.
PRICE_KEY = "close_price"


class ListDataFeed(IDataFeed):
    """Flux séquentiel sur une liste de FeatureSets déjà en mémoire."""

    def __init__(self, feature_sets: List[FeatureSet]) -> None:
        self._feature_sets = feature_sets

    def get_feature_stream(
        self, symbol: Symbol, timeframe: TimeFrame
    ) -> Iterator[FeatureSet]:
        return iter(self._feature_sets)


def load_bars(symbol: Symbol, timeframe: TimeFrame, parquet_name: str) -> List[MarketBar]:
    """Charge les barres brutes depuis le data lake local."""
    storage = ParquetStorage(data_dir=str(REPO_ROOT / "data" / "market_data"))
    # Les fichiers d'ingestion ne suivent pas la convention <symbol>_<tf>.parquet
    # de ParquetStorage : on pointe le chemin réel plutôt que de renommer un
    # dataset déjà référencé par son hash dans les artefacts de validation.
    storage._get_file_path = lambda *_: str(  # type: ignore[method-assign]
        REPO_ROOT / "data" / "market_data" / parquet_name
    )
    bars = list(storage.load_bars(symbol, timeframe))
    if not bars:
        raise SystemExit(f"Aucune barre chargée depuis {parquet_name}.")
    logger.info("%d barres chargées depuis %s.", len(bars), parquet_name)
    return bars


def build_feature_sets(bars: List[MarketBar]) -> List[FeatureSet]:
    """Extrait les features techniques et y joint le prix de clôture.

    L'extracteur n'émet pas le prix brut (il ne produit que des indicateurs).
    Sans cette jointure, le Backtester retomberait sur son prix par défaut de
    100.0 et toute la validation porterait sur une équité plate.
    """
    extractor = TechnicalFeatureExtractor()
    feature_sets = extractor.extract(bars)

    ordered_bars = sorted(bars, key=lambda b: b.timestamp)
    enriched: List[FeatureSet] = []
    for fset, bar in zip(feature_sets, ordered_bars):
        if fset.timestamp != bar.timestamp:
            raise RuntimeError(
                "Désalignement features/barres : "
                f"{fset.timestamp.isoformat()} != {bar.timestamp.isoformat()}"
            )
        features: Dict[str, float] = dict(fset.features)
        features[PRICE_KEY] = float(bar.close)
        enriched.append(
            FeatureSet(
                symbol=fset.symbol,
                timeframe=fset.timeframe,
                timestamp=fset.timestamp,
                features=features,
            )
        )
    logger.info("%d FeatureSets construits.", len(enriched))
    return enriched


def split_train_test(
    feature_sets: List[FeatureSet], train_ratio: float
) -> tuple[List[FeatureSet], List[FeatureSet]]:
    """Découpe chronologique stricte : le test est postérieur à l'entraînement.

    Un découpage aléatoire mélangerait passé et futur et rendrait toute métrique
    de validation ininterprétable.
    """
    cut = int(len(feature_sets) * train_ratio)
    return feature_sets[:cut], feature_sets[cut:]


def main() -> int:
    parser = argparse.ArgumentParser(description="Entraîne et valide le modèle LightGBM.")
    parser.add_argument("--symbol", default="CRASH1000")
    parser.add_argument("--timeframe", default="M1")
    parser.add_argument("--parquet", default="crash1000.parquet")
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--n-estimators", type=int, default=300)
    parser.add_argument(
        "--horizon",
        type=int,
        default=1,
        help=(
            "Distance en barres du label forward. 1 est REFUTÉ économiquement sur "
            "CRASH1000 (ADR 0019/0020 : budget de coût 0.60-0.69 bps). Lire la "
            "table de `diagnose_cost_budget_by_horizon.py` avant de choisir."
        ),
    )
    parser.add_argument("--commission-rate", type=float, default=0.001)
    parser.add_argument("--slippage-bps", type=float, default=5.0)
    parser.add_argument(
        "--safety-margin",
        type=float,
        default=1.0,
        help=(
            "Multiplicateur du coût aller-retour pour le seuil d'entrée. "
            "1.0 = seuil de rentabilité strict. Refuse toute valeur < 1.0."
        ),
    )
    parser.add_argument(
        "--output", default="data/models/lightgbm_latest.txt", help="Chemin d'export"
    )
    args = parser.parse_args()

    symbol = Symbol(args.symbol, AssetClass.INDICES)
    timeframe = TimeFrame(args.timeframe)

    # 1. Données réelles -> features
    bars = load_bars(symbol, timeframe, args.parquet)
    feature_sets = build_feature_sets(bars)
    train_sets, test_sets = split_train_test(feature_sets, args.train_ratio)
    logger.info("Split chronologique : %d train / %d test.", len(train_sets), len(test_sets))

    # 2. Entraînement sur le segment d'entraînement uniquement
    builder = DatasetBuilder(price_key=PRICE_KEY, horizon=args.horizon)
    train_dataset = builder.build_supervised(train_sets)
    model = ModelFactory.create_model(
        "lightgbm", n_estimators=args.n_estimators, verbose=-1
    )
    report = QlibTrainer().train(model, train_dataset)
    logger.info("Rapport d'entraînement : %s", json.dumps(report, indent=2))

    # 3. Validation sur le segment de test, jamais vu à l'entraînement.
    # Le broker de validation et la stratégie partagent la MÊME source de coût :
    # le seuil d'entrée budgète exactement le péage que la simulation appliquera.
    def broker_factory() -> SimulatedBroker:
        return SimulatedBroker(
            commission_rate=args.commission_rate, slippage_bps=args.slippage_bps
        )

    cost_model = broker_factory().cost_model
    strategy = MLStrategy.from_cost_model(
        predictor=QlibPredictor(model),
        cost_model=cost_model,
        safety_margin=args.safety_margin,
    )
    logger.info(
        "Coût aller-retour %.2f bps -> seuil d'entrée %.6f (marge %.2fx).",
        cost_model.round_trip_cost * 10_000.0,
        strategy.buy_threshold,
        args.safety_margin,
    )
    config = ValidationConfig(
        markets=[symbol],
        timeframes=[timeframe],
        active_campaigns=[
            ValidationCampaignType.HOLD_OUT,
            ValidationCampaignType.WALK_FORWARD,
            ValidationCampaignType.MONTE_CARLO,
            ValidationCampaignType.BENCHMARK,
        ],
    )
    runner = ValidationRunner(
        registry=ValidationRegistry(registry_dir=str(REPO_ROOT / ".validation_registry")),
        scoring_engine=ScoringEngine(),
    )
    artifact = runner.run_validation(
        strategy=strategy,
        data_feed=ListDataFeed(test_sets),
        broker_factory=broker_factory,
        config=config,
    )

    print("\n" + "=" * 70)
    print(f"  VALIDATION — {symbol.name} {timeframe.value}")
    print("=" * 70)
    print(
        f"  Coût aller-retour : {cost_model.round_trip_cost * 10_000.0:.2f} bps"
        f"  |  Seuil d'entrée : {strategy.buy_threshold:.6f}"
    )
    for campaign in artifact.report.campaigns:
        status = "PASS" if campaign.passed else "FAIL"
        print(f"  [{status}] {campaign.campaign_type.value:<16} {campaign.metrics}")
    print(f"\n  Score : {artifact.report.strategy_score}/100")
    print(f"  Approuvé : {artifact.report.is_approved}")
    print("=" * 70 + "\n")

    # 4. Export conditionnel. Un modèle recalé ne laisse aucun artefact derrière
    # lui : c'est la seule garantie que `data/models/` ne contient que du validé.
    if not artifact.report.is_approved:
        logger.error(
            "Modèle NON approuvé (score %.1f) — aucun export. "
            "L'hypothèse est rejetée, pas contournée.",
            artifact.report.strategy_score,
        )
        return 1

    if not isinstance(model, LightGBMModel):
        raise TypeError("Export supporté uniquement pour LightGBMModel.")
    output_path = REPO_ROOT / args.output
    model.save(str(output_path))
    logger.info("Modèle approuvé et exporté : %s", output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
