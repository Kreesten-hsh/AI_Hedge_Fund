"""Coût aller-retour réel Deriv, mesuré par aller-retours immédiats sur démo.

Pourquoi une mesure manuelle transcrite ici plutôt qu'un appel API : toutes les
routes automatisables sont fermées depuis l'environnement de développement
(catalogue d'offres vide pour `clients_country: bj`, REST public en 403, page de
specs rendue côté client, MT5 pointant sur un serveur MetaQuotes qui ne porte pas
les synthétiques Deriv). Détail dans le backlog, entrée COST-01.

Ce que la mesure capture, et que l'arithmétique sur la commission affichée ne
pouvait pas capturer : le nombre de prélèvements par aller-retour. L'hypothèse de
travail était « commission à l'ouverture ET à la fermeture », soit `2 x taux`.
Elle est RÉFUTÉE ici — le coût mesuré vaut la commission affichée UNE fois, plus
un résidu d'environ 0.15 bps. Facteur 2 sur le chiffre qui décide de l'horizon
cible, invisible sans aller-retour réel.

Protocole exécuté : compte démo, ouverture puis fermeture immédiate, cinq fois
par instrument. Le terme de prix s'annule exactement dans `_round_trip_costs`,
donc le mouvement de marché entre l'entrée et la sortie ne contamine pas le
résultat ; seule la latence de saisie subsiste, visible comme dispersion.
"""

from __future__ import annotations

from statistics import median
from typing import NamedTuple, Sequence

BPS_PER_UNIT = 10_000.0

# Arrondi de l'affichage du P&L, en USD. Il fixe la précision atteignable : sur
# un notionnel de 1000 USD, 0.01 USD vaut 0.1 bps. Toute conclusion plus fine que
# ça serait du bruit d'affichage lu comme un signal.
PNL_DISPLAY_STEP_USD = 0.01


class RoundTrip(NamedTuple):
    """Un aller-retour immédiat relevé sur le ticket de trade."""

    entry_spot: float
    exit_spot: float
    realised_pnl_usd: float


class Instrument(NamedTuple):
    name: str
    stake_usd: float
    multiplier: float
    displayed_commission_usd: float
    trades: Sequence[RoundTrip]

    @property
    def notional_usd(self) -> float:
        """Assiette de la commission : c'est la mise AMPLIFIÉE qui est taxée."""
        return self.stake_usd * self.multiplier

    @property
    def displayed_commission_bps(self) -> float:
        return self.displayed_commission_usd / self.notional_usd * BPS_PER_UNIT


# Relevés du 2026-08-04, compte démo Deriv Trader, onglet Multipliers.
# Le sens n'a pas été noté au relevé : il est reconstruit par `infer_direction`,
# pas supposé.
MEASUREMENTS = (
    Instrument(
        name="CRASH1000",
        stake_usd=10.0,
        multiplier=100.0,
        displayed_commission_usd=0.06,
        trades=(
            RoundTrip(5813.068, 5813.101, -0.06),
            RoundTrip(5814.316, 5814.494, -0.30),
            RoundTrip(5814.286, 5814.508, -0.03),
            RoundTrip(5815.562, 5815.588, -0.07),
            RoundTrip(5815.548, 5815.607, -0.07),
        ),
    ),
    Instrument(
        name="BOOM1000",
        stake_usd=10.0,
        multiplier=100.0,
        displayed_commission_usd=0.09,
        trades=(
            RoundTrip(14700.805, 14700.591, -0.08),
            RoundTrip(14700.973, 14700.559, -0.12),
            RoundTrip(14698.538, 14698.525, -0.09),
            RoundTrip(14698.548, 14698.456, -0.10),
            RoundTrip(14698.558, 14698.456, -0.10),
        ),
    ),
)


def round_trip_costs_bps(instrument: Instrument, direction: float) -> list[float]:
    """Coût aller-retour de chaque trade, en bps du notionnel.

    Le P&L réalisé mélange deux effets : le mouvement du marché pendant la
    détention, et le péage. On retranche le premier pour isoler le second —
    c'est ce qui rend la mesure insensible au fait que le prix a bougé entre la
    saisie de l'entrée et celle de la sortie.

    :param direction: +1 pour une position acheteuse, -1 pour vendeuse.
    """
    costs: list[float] = []
    for trade in instrument.trades:
        gross_usd = (
            instrument.notional_usd
            * direction
            * (trade.exit_spot / trade.entry_spot - 1.0)
        )
        costs.append(
            (gross_usd - trade.realised_pnl_usd) / instrument.notional_usd * BPS_PER_UNIT
        )
    return costs


def infer_direction(instrument: Instrument) -> float:
    """Reconstruit le sens des positions à partir d'une contrainte physique.

    Le sens n'a pas été noté au relevé, et le supposer fausserait tout : inverser
    le signe déplace chaque coût de deux fois le mouvement de prix.

    La contrainte qui tranche : les synthétiques Deriv sont cotés sur un flux à
    PRIX UNIQUE (vérifié — `ticks_history` ne renvoie jamais bid/ask). Aucun
    spread favorable n'est donc possible, et le coût aller-retour ne peut pas
    descendre sous la commission affichée. Un seul sens satisfait cette borne.

    :raises ValueError: si les deux sens la violent, ou si aucun ne la viole —
        dans les deux cas le relevé est incohérent et publier un chiffre serait
        pire que de s'arrêter.
    """
    floor_bps = instrument.displayed_commission_bps - (
        PNL_DISPLAY_STEP_USD / instrument.notional_usd * BPS_PER_UNIT
    )
    admissible = [
        direction
        for direction in (1.0, -1.0)
        if all(cost >= floor_bps for cost in round_trip_costs_bps(instrument, direction))
    ]
    if len(admissible) != 1:
        raise ValueError(
            f"{instrument.name} : {len(admissible)} sens compatibles avec le "
            f"plancher de {floor_bps:.3f} bps. Relevé incohérent, sens à noter "
            "explicitement au prochain passage."
        )
    return admissible[0]


def main() -> int:
    print("\n" + "=" * 72)
    print("  COÛT ALLER-RETOUR RÉEL — DERIV MULTIPLIERS (compte démo)")
    print("=" * 72)

    for instrument in MEASUREMENTS:
        direction = infer_direction(instrument)
        costs = round_trip_costs_bps(instrument, direction)
        retained = median(costs)
        commission = instrument.displayed_commission_bps

        print(f"\n  {instrument.name} — notionnel {instrument.notional_usd:.0f} USD "
              f"({instrument.stake_usd:.0f} x{instrument.multiplier:.0f})")
        print(f"    sens reconstruit          : {'LONG' if direction > 0 else 'SHORT'}")
        print(f"    commission affichée       : {instrument.displayed_commission_usd:.2f} USD "
              f"= {commission:.3f} bps")
        print(f"    coûts A/R mesurés (bps)   : "
              f"{'  '.join(f'{c:.3f}' for c in sorted(costs))}")
        print(f"    RETENU (médiane)          : {retained:.3f} bps")
        # Le résidu au-dessus de la commission est ce qui reste une fois le
        # mouvement de prix retiré. Il est du même ordre que le pas d'affichage
        # du P&L, donc on ne prétend pas l'attribuer à un mécanisme.
        print(f"    résidu sur la commission  : {retained - commission:+.3f} bps "
              f"(pas d'affichage : {PNL_DISPLAY_STEP_USD / instrument.notional_usd * BPS_PER_UNIT:.3f} bps)")
        print(f"    prélèvements par A/R      : {retained / commission:.2f}x la commission "
              "-> UNE fois, pas deux")

    print("\n" + "=" * 72)
    print("  Lire ces chiffres dans la table de budget de l'ADR 0020 pour fixer")
    print("  l'horizon cible. Rappel : le ratio de fenêtres tradables est un")
    print("  PLAFOND ORACLE — il dit que le marché bouge assez pour payer le")
    print("  péage, jamais qu'un signal exploitable existe.")
    print("=" * 72 + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
