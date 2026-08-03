"""À quel horizon de détention le mouvement de Crash 1000 dépasse-t-il le coût ?

Le diagnostic à 1 barre a montré que le marché lui-même ne bouge JAMAIS de 30 bps
en une barre M1 (médiane 0.61 bps sur 1499 barres hors-échantillon). Le rejet
n'est donc pas un défaut du modèle : à cet horizon, aucun prédicteur ne peut
couvrir un aller-retour de 30 bps, Kronos compris.

Ce script mesure la distribution du mouvement absolu à plusieurs horizons, pour
savoir si l'hypothèse est récupérable en allongeant la détention ou si elle est
morte quel que soit l'horizon accessible.

Mesure pure : aucun seuil n'est ajusté ici.
"""

import logging

import numpy as np

from aegis_trade.domain.core import AssetClass, Symbol, TimeFrame
from aegis_trade.domain.tradability import absolute_moves, tradable_window_ratio
from aegis_trade.infrastructure.brokers.simulated_broker import SimulatedBroker

from train_qlib_model import PRICE_KEY, build_feature_sets, load_bars, split_train_test

logging.basicConfig(level=logging.WARNING)

BPS = 10_000.0
HORIZONS = (1, 5, 15, 30, 60, 120, 240, 480)


def main() -> int:
    symbol = Symbol("CRASH1000", AssetClass.INDICES)
    bars = load_bars(symbol, TimeFrame("M1"), "crash1000.parquet")
    _, test_sets = split_train_test(build_feature_sets(bars), 0.7)

    prices = [f.features[PRICE_KEY] for f in test_sets]

    cost = SimulatedBroker(commission_rate=0.001, slippage_bps=5.0).cost_model
    threshold = cost.breakeven_return()

    print("\n" + "=" * 78)
    print("  MOUVEMENT ABSOLU PAR HORIZON vs COÛT ALLER-RETOUR — CRASH1000 M1, hors-échantillon")
    print("=" * 78)
    print(f"  Coût aller-retour : {threshold * BPS:.2f} bps  |  {len(prices)} barres de test\n")
    print(f"  {'Horizon':>8}  {'|méd| bps':>10}  {'|p95| bps':>10}  {'|max| bps':>10}  {'% > coût':>9}")
    print("  " + "-" * 74)

    for horizon in HORIZONS:
        if horizon >= len(prices):
            continue
        # Même fonction de domaine que le gate de faisabilité : script et gate ne
        # peuvent pas diverger sur ce qui compte comme fenêtre tradable.
        moves = np.array(absolute_moves(prices, horizon), dtype=np.float64)
        pct_above = tradable_window_ratio(prices, horizon, cost) * 100.0
        print(
            f"  {horizon:>6} b  {np.median(moves) * BPS:>10.2f}  "
            f"{np.percentile(moves, 95) * BPS:>10.2f}  {np.max(moves) * BPS:>10.2f}  "
            f"{pct_above:>8.2f} %"
        )

    print("\n  Lecture : la colonne '% > coût' est la fraction des fenêtres où le mouvement")
    print("  réalisé suffit à payer un aller-retour. Un modèle parfait ne pourrait pas")
    print("  dépasser cette borne — c'est un plafond de microstructure, pas de prédiction.")

    # Le 30 bps ci-dessus est le coût du broker SIMULÉ, pas une mesure Deriv (cf.
    # ADR 0018). Sans ce balayage, la conclusion resterait suspendue à un chiffre
    # non mesuré : un lecteur pourrait l'écarter en supposant un broker moins cher.
    print("\n" + "=" * 78)
    print("  BALAYAGE : le verdict à 1 barre tient-il pour un broker MOINS cher ?")
    print("=" * 78)
    moves_1b = np.array(absolute_moves(prices, 1), dtype=np.float64)
    print(f"  {'coût A/R':>10}  {'% barres > coût':>16}")
    print("  " + "-" * 30)
    for cost_bps in (30.0, 10.0, 4.0, 2.0, 1.0, 0.5):
        share = float(np.mean(moves_1b >= (cost_bps / BPS)) * 100.0)
        print(f"  {cost_bps:>7.1f} bps  {share:>15.2f} %")
    print("\n  Mouvement médian à 1 barre : "
          f"{np.median(moves_1b) * BPS:.2f} bps — plancher que tout coût doit passer sous.")
    print("=" * 78 + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
