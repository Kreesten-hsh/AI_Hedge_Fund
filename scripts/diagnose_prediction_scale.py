"""Diagnostic : l'amplitude prédite par le modèle est-elle du même ordre que le coût ?

La validation `val_20260803_205954` a produit ZÉRO trade : avec un seuil dérivé du
coût réel (30 bps aller-retour), aucune prédiction n'a franchi la zone morte. Ce
script mesure l'écart d'ordre de grandeur entre ce que le modèle prédit et ce que
coûte un trade — le chiffre qui décide si l'hypothèse « signal exploitable sur
cette configuration de features » est récupérable ou fausse.

Aucun ajustement de seuil ici : on mesure, on ne recalibre pas après lecture du
résultat (ce serait du gate-adjusting, cf. ADR 0018).
"""

import logging

import numpy as np

from aegis_trade.domain.core import AssetClass, Symbol, TimeFrame
from aegis_trade.infrastructure.brokers.simulated_broker import SimulatedBroker
from aegis_trade.providers.qlib.dataset_builder import DatasetBuilder
from aegis_trade.providers.qlib.model_factory import ModelFactory
from aegis_trade.providers.qlib.predictor import QlibPredictor
from aegis_trade.providers.qlib.trainer import QlibTrainer

from train_qlib_model import (
    PRICE_KEY,
    build_feature_sets,
    load_bars,
    split_train_test,
)

logging.basicConfig(level=logging.WARNING)

BPS = 10_000.0


def main() -> int:
    symbol = Symbol("CRASH1000", AssetClass.INDICES)
    timeframe = TimeFrame("M1")

    bars = load_bars(symbol, timeframe, "crash1000.parquet")
    feature_sets = build_feature_sets(bars)
    train_sets, test_sets = split_train_test(feature_sets, 0.7)

    builder = DatasetBuilder(price_key=PRICE_KEY)
    model = ModelFactory.create_model("lightgbm", n_estimators=300, verbose=-1)
    QlibTrainer().train(model, builder.build_supervised(train_sets))

    predictor = QlibPredictor(model)
    predictions = []
    for fset in test_sets:
        preds = predictor.predict(builder.build_from_features([fset]))
        if preds:
            predictions.append(preds[0])

    pred = np.array(predictions, dtype=np.float64)

    # Le mouvement réel à 1 barre, pour savoir si le plafond vient du modèle ou du marché.
    realized = np.array(
        [
            (
                test_sets[i + 1].features[PRICE_KEY] / test_sets[i].features[PRICE_KEY]
            )
            - 1.0
            for i in range(len(test_sets) - 1)
        ],
        dtype=np.float64,
    )

    cost = SimulatedBroker(commission_rate=0.001, slippage_bps=5.0).cost_model
    threshold = cost.breakeven_return()

    print("\n" + "=" * 72)
    print("  DIAGNOSTIC D'ORDRE DE GRANDEUR — prédiction vs coût")
    print("=" * 72)
    print(f"  Seuil de rentabilité (aller-retour)   : {threshold * BPS:8.2f} bps")
    print(f"  Prédictions évaluées                  : {len(pred)}")
    print("\n  PRÉDICTIONS DU MODÈLE (rendement attendu 1 barre)")
    print(f"    |médiane|                           : {np.median(np.abs(pred)) * BPS:8.4f} bps")
    print(f"    |p95|                               : {np.percentile(np.abs(pred), 95) * BPS:8.4f} bps")
    print(f"    |max|                               : {np.max(np.abs(pred)) * BPS:8.4f} bps")
    print(f"    au-dessus du seuil                  : {int(np.sum(np.abs(pred) >= threshold))}")
    print("\n  MOUVEMENT RÉEL DU MARCHÉ (1 barre, hors-échantillon)")
    print(f"    |médiane|                           : {np.median(np.abs(realized)) * BPS:8.4f} bps")
    print(f"    |p95|                               : {np.percentile(np.abs(realized), 95) * BPS:8.4f} bps")
    print(f"    |max|                               : {np.max(np.abs(realized)) * BPS:8.4f} bps")
    print(f"    au-dessus du seuil                  : {int(np.sum(np.abs(realized) >= threshold))}"
          f" / {len(realized)} ({np.mean(np.abs(realized) >= threshold) * 100:.2f} %)")
    print("\n  RATIOS")
    print(f"    seuil / |max| prédit                : {threshold / max(np.max(np.abs(pred)), 1e-12):8.1f} x")
    print(f"    seuil / |médiane| réelle            : {threshold / max(np.median(np.abs(realized)), 1e-12):8.1f} x")
    print("=" * 72 + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
