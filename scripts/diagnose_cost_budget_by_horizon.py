"""Quel coût aller-retour chaque horizon peut-il financer, et le M15 tient-il ?

Deux questions tranchées d'un coup, sur données réelles, sans entraîner de modèle.

**1. Renverser l'hypothèse de coût.** L'ADR 0019 a conclu que l'espace économique
n'existe qu'à partir de ~60 barres M1. Cette fenêtre est calculée avec les 30 bps
du `SimulatedBroker`, qui ne sont pas une mesure Deriv (ADR 0018). Le catalogue
d'offres Deriv (`active_symbols`, `contracts_for`, `proposal`) revient vide depuis
l'environnement de développement, et `ticks_history` ne renvoie que des prix
uniques : le spread réel n'est pas lisible par API ici. Choisir l'horizon cible à
partir d'un coût supposé bâtirait la Phase suivante sur un chiffre non mesuré.

Ce script inverse donc la question : pour chaque horizon, quel est le coût
aller-retour MAXIMAL qui laisse encore une part donnée de fenêtres tradables ? La
réponse ne dépend d'aucune hypothèse de frais. Le coût Deriv réel, quand il sera
mesuré sur compte réel, se lira directement dans la table.

**2. Trancher M15 vs pagination (DATA-01).** Le plafond de 5000 bougies par
requête donne ~3.5 jours en M1 contre ~52 jours en M15. La réserve du backlog est
que Crash 1000 est un indice à spikes et que l'agrégation peut masquer la
structure. Comparer les deux granularités à wall-clock ÉGAL répond par la mesure :
si M1 et M15 donnent le même budget de coût pour la même durée de détention,
l'agrégation ne détruit pas ce dont dépend la décision d'entrée.

Ce que ce script ne fait pas : mesurer le coût Deriv réel (route API fermée), ni
établir la puissance statistique d'un horizon (c'est DATA-01). Il fixe la cible ;
il ne la valide pas.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Sequence

from aegis_trade.domain.core import AssetClass, Symbol, TimeFrame
from aegis_trade.domain.tradability import max_viable_round_trip_cost

from train_qlib_model import PRICE_KEY, build_feature_sets, load_bars

logging.basicConfig(level=logging.WARNING)

BPS = 10_000.0

# Parts de fenêtres tradables retenues. Aucune n'est « la bonne » : une stratégie
# à petites décisions fréquentes vise le haut de la colonne, une stratégie
# sélective le bas. La table les montre côte à côte au lieu d'en figer une.
RATIOS = (0.50, 0.20, 0.10, 0.05)

# Horizons choisis pour se correspondre en wall-clock d'une granularité à
# l'autre : c'est cette correspondance qui rend la comparaison M1/M15 lisible.
M1_HORIZONS = (1, 15, 30, 60, 120, 240, 480)
M15_HORIZONS = (1, 2, 4, 8, 16, 32, 96)


def _format_wall_clock(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes}min"
    return f"{minutes // 60}h{minutes % 60:02d}"


def _load_prices(parquet_name: str, timeframe: TimeFrame) -> list[tuple[datetime, float]]:
    """Couples (horodatage, clôture) du fichier demandé, ordre chronologique.

    Passe par le même chemin de chargement que l'entraînement (`load_bars` +
    `build_feature_sets`) : mesurer sur un chemin de données différent de celui
    qui servira à entraîner exposerait à conclure sur un jeu qui n'est pas celui
    du modèle. Les horodatages sont conservés parce que la comparaison M1/M15
    n'a de sens que sur une période commune.
    """
    symbol = Symbol("CRASH1000", AssetClass.INDICES)
    bars = load_bars(symbol, timeframe, parquet_name)
    return [(f.timestamp, f.features[PRICE_KEY]) for f in build_feature_sets(bars)]


def _restrict_to_common_span(
    left: Sequence[tuple[datetime, float]],
    right: Sequence[tuple[datetime, float]],
) -> tuple[list[float], list[float]]:
    """Réduit deux séries à leur période de recouvrement.

    Sans cette restriction, le M15 (~52 jours) et le M1 (~3.5 jours) sont
    comparés sur des marchés différents : l'écart mesuré serait un changement de
    régime attribué à tort à l'agrégation. Mesuré, cet artefact atteint -23 % à
    8 h de détention et disparaît entièrement sur période commune.
    """
    start = max(left[0][0], right[0][0])
    end = min(left[-1][0], right[-1][0])
    return (
        [price for stamp, price in left if start <= stamp <= end],
        [price for stamp, price in right if start <= stamp <= end],
    )


def _print_budget_table(
    label: str,
    prices: Sequence[float],
    horizons: Sequence[int],
    minutes_per_bar: int,
) -> None:
    header = "  ".join(f"{'>=' + f'{r:.0%}':>8}" for r in RATIOS)
    print(f"\n  {label} — {len(prices)} barres")
    print(f"  {'horizon':>8}  {'détention':>10}  {'fenêtres':>9}  {header}")
    print("  " + "-" * (33 + 10 * len(RATIOS)))

    for horizon in horizons:
        if horizon >= len(prices):
            continue
        budgets = [
            max_viable_round_trip_cost(prices, horizon, min_ratio=ratio) * BPS
            for ratio in RATIOS
        ]
        cells = "  ".join(f"{b:>8.2f}" for b in budgets)
        wall_clock = _format_wall_clock(horizon * minutes_per_bar)
        windows = len(prices) - horizon
        print(f"  {horizon:>6} b  {wall_clock:>10}  {windows:>9}  {cells}")


def main() -> int:
    print("\n" + "=" * 78)
    print("  BUDGET DE COÛT ALLER-RETOUR PAR HORIZON — CRASH1000, en bps")
    print("=" * 78)
    print("  Lecture : chaque cellule est le coût A/R maximal (bps) sous lequel la part")
    print("  de fenêtres indiquée en tête de colonne couvre encore son propre péage.")
    print("  Plafond oracle : direction supposée connue. Un modèle réel fait moins.")

    m1_series = _load_prices("crash1000.parquet", TimeFrame("M1"))
    _print_budget_table("M1", [p for _, p in m1_series], M1_HORIZONS, minutes_per_bar=1)

    try:
        m15_series = _load_prices("crash1000_m15.parquet", TimeFrame("M15"))
    except SystemExit:
        print("\n  M15 absent — lancer `scripts/fetch_training_data.py` pour la comparaison.")
        return 1

    _print_budget_table("M15", [p for _, p in m15_series], M15_HORIZONS, minutes_per_bar=15)

    m1_prices, m15_prices = _restrict_to_common_span(m1_series, m15_series)

    print("\n" + "=" * 78)
    print("  RESTREINDRE LES ENTRÉES AUX FRONTIÈRES M15 COÛTE-T-IL DE L'ESPACE ? (DATA-01)")
    print("=" * 78)
    print("  Budget à détention ÉGALE, sur période COMMUNE aux deux séries. Un écart")
    print("  faible signifie que passer en M15 ne rétrécit pas la cible économique, et")
    print("  débloque ~52 jours d'historique par requête contre ~3.5 en M1.")
    print(f"  Période commune : {len(m1_prices)} barres M1, {len(m15_prices)} barres M15.\n")
    print(f"  {'détention':>10}  {'M1 bps':>9}  {'M15 bps':>9}  {'écart':>8}")
    print("  " + "-" * 42)

    # 20 % de fenêtres tradables : assez fréquent pour une stratégie à petites
    # décisions, assez sélectif pour ne pas être dominé par le bruit de tick.
    comparison_ratio = 0.20
    # Appariement sur la durée réelle, pas sur le rang dans les deux listes :
    # une correspondance par index ferait face à face des détentions différentes
    # et l'écart mesuré n'aurait plus de sens.
    m15_by_wall_clock = {h * 15: h for h in M15_HORIZONS}
    for m1_h in M1_HORIZONS:
        m15_h = m15_by_wall_clock.get(m1_h)
        if m15_h is None or m1_h >= len(m1_prices) or m15_h >= len(m15_prices):
            continue
        m1_budget = max_viable_round_trip_cost(m1_prices, m1_h, comparison_ratio) * BPS
        m15_budget = max_viable_round_trip_cost(m15_prices, m15_h, comparison_ratio) * BPS
        gap = (m15_budget / m1_budget - 1.0) * 100.0 if m1_budget > 0.0 else float("nan")
        wall_clock = _format_wall_clock(m1_h)
        print(f"  {wall_clock:>10}  {m1_budget:>9.2f}  {m15_budget:>9.2f}  {gap:>7.1f} %")

    print(f"\n  (part de fenêtres exigée : {comparison_ratio:.0%})")
    print("  Portée : ce test compare des mouvements de bout en bout. Il est aveugle au")
    print("  chemin intra-fenêtre PAR CONSTRUCTION, donc il ne dit RIEN sur la question")
    print("  de savoir si des features M15 voient encore les spikes. Cette réserve du")
    print("  backlog reste ouverte et se tranche côté features, pas ici.")
    print("=" * 78 + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
