"""Combien de barres une position reste-t-elle ouverte quand la sortie suit le signal ?

Question laissée ouverte par SIG-02 : **« horizon du label » n'est pas « durée de
détention »**.

Le gate de tradabilité (ADR 0021, revalidé ADR 0022) mesure une sortie
TEMPORELLE : `absolute_moves` compare `t+horizon` à `t`, donc suppose la position
fermée exactement à la barre `t+horizon`. Les 94.0 % de fenêtres tradables de
Crash à 5 barres sont le plafond oracle de CETTE stratégie.

`MLStrategy` n'est pas cette stratégie. Elle réémet une exposition cible à chaque
barre et sort quand le rendement attendu retombe dans la zone morte ou change de
sens. Sa détention est une longueur de séquence de signal, que rien ne ramène à
l'horizon du label. Deux régimes divergents, asymétriques :

- **détention < horizon** : un aller-retour complet payé, dimensionné sur un
  mouvement de 5 barres, pour capter un mouvement d'une barre. C'est l'horizon
  1 barre — réfuté trois fois, 5.8 % de fenêtres — réintroduit par la porte de
  sortie. C'est le seul régime dangereux.
- **détention > horizon** : un seul aller-retour au lieu de plusieurs, coût par
  unité d'exposition plus bas. Économiquement favorable, mais le gate cesse de
  décrire ce qui se passe et le seuil d'entrée devient sur-conservateur.

Ce script mesure la distribution des détentions sur un signal ORACLE : à chaque
barre, l'exposition qu'une `MLStrategy` déclarerait si elle prédisait
parfaitement `forward_return_horizon`. Pur data, aucun entraînement — la même
discipline que le gate de tradabilité, appliquée à la sortie plutôt qu'à
l'entrée.

Ce que la mesure N'EST PAS : une borne sur la détention d'un modèle réel. Le
bruit de prédiction fragmente typiquement les séquences, mais peut aussi en
souder deux. C'est la structure de persistance du LABEL, et c'est déjà décisif :
si le label lui-même ne persiste qu'une barre, aucune sortie par persistance ne
peut tenir 5 barres.

Coûts : les chiffres RETENUS de l'ADR 0021 (0.745 / 1.063 bps), pas les mesures
live plus basses de COST-02 (0.652 / 0.951). Retenir les plus bas élargirait les
fenêtres et raccourcirait les détentions dans le sens qui arrange — le défaut
corrigé par l'ADR 0018.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from aegis_trade.domain.core import AssetClass, Symbol, TimeFrame
from aegis_trade.domain.costs import TransactionCostModel
from aegis_trade.domain.tradability import (
    oracle_holding_periods,
    oracle_target_exposure,
    tradable_window_ratio,
)

from train_qlib_model import PRICE_KEY, build_feature_sets, load_bars

logging.basicConfig(level=logging.WARNING)

BPS = 10_000.0

# Marges balayées ensemble plutôt qu'une seule figée : un verdict qui basculerait
# d'une marge à l'autre serait un verdict fragile, et c'est précisément ce qui a
# écarté les horizons 2 et 3 barres.
MARGINS = (1.0, 2.0, 3.0)

# Marge à laquelle la contre-épreuve est jouée : la plus exigeante du balayage.
# C'est celle qui a départagé les horizons (ADR 0021), donc celle sur laquelle un
# artefact serait le plus coûteux.
CONTROL_MARGIN = 3.0

# Graine du contrôle. Fixe et versionnée : un contrôle non reproductible ne
# réfute rien.
CONTROL_SEED = 7


@dataclass(frozen=True, slots=True)
class Instrument:
    """Un instrument, son horizon cible mesuré et son coût aller-retour retenu."""

    name: str
    parquet: str
    horizon: int
    commission_rate: float

    @property
    def cost_model(self) -> TransactionCostModel:
        """`commission_rate` porte tout l'aller-retour ; le slippage est déjà dedans.

        Ajouter un `slippage_bps` non nul le compterait deux fois : les 0.745 et
        1.063 bps de l'ADR 0021 sont mesurés sur des tickets complets, pas sur
        une jambe.
        """
        return TransactionCostModel(
            commission_rate=self.commission_rate, slippage_bps=0.0
        )


INSTRUMENTS = (
    Instrument("CRASH1000", "crash1000.parquet", horizon=5, commission_rate=0.00003725),
    Instrument("BOOM1000", "boom1000.parquet", horizon=10, commission_rate=0.00005315),
)


def _print_decision_rule() -> None:
    """La règle est imprimée AVANT les chiffres, pour qu'elle ne s'y adapte pas."""
    print("\n" + "=" * 78)
    print("  RÈGLE DE DÉCISION — pré-enregistrée, lue avant les mesures")
    print("=" * 78)
    print("  Comparaison : détention MÉDIANE de l'oracle vs horizon du label.")
    print()
    print("    médiane ≈ horizon   -> sortie par persistance CONSERVÉE.")
    print("                           MLStrategy inchangée, gate valide tel quel.")
    print("    médiane >> horizon  -> sortie par persistance CONSERVÉE.")
    print("                           Gate à re-mesurer à la détention réelle")
    print("                           (plus permissif, jamais moins).")
    print("    médiane ≈ 1 barre   -> sortie par persistance RÉFUTÉE.")
    print("                           Soit sortie temporelle forcée à l'horizon,")
    print("                           soit l'horizon tombe pour cette stratégie.")
    print()
    print("  Aucune de ces issues n'est l'issue souhaitée. Elles sont écrites")
    print("  ensemble pour qu'aucune ne soit rédigée après lecture des chiffres.")


def _memoryless_control(
    prices: list[float],
    instrument: Instrument,
    margin: float,
) -> None:
    """Contre-épreuve : une série SANS mémoire donne-t-elle la même détention ?

    Le doute à lever est mécanique. `forward_return_5[i]` et
    `forward_return_5[i+1]` partagent 4 barres sur 5 : un unique mouvement peint
    donc ~5 fenêtres consécutives du même signe. Une détention médiane égale à
    l'horizon pourrait n'être qu'un artefact de ce recouvrement, auquel cas elle
    se reproduirait sur n'importe quelle série et ne dirait rien de Crash ni de
    Boom.

    Le contrôle est une marche aléatoire à incréments i.i.d. — zéro mémoire par
    construction — dont la volatilité est ajustée par bisection jusqu'à ce
    qu'elle expose la MÊME part de fenêtres que la série réelle. Sans ce calage,
    la comparaison serait confondue : une série qui franchit moins souvent le
    seuil produit des séquences plus courtes pour une raison qui n'a rien à voir
    avec la mémoire.
    """
    horizon = instrument.horizon
    cost = instrument.cost_model
    target = tradable_window_ratio(prices, horizon, cost, margin)

    log_returns = np.diff(np.log(np.asarray(prices, dtype=np.float64)))
    sigma = float(log_returns.std())

    def walk(multiplier: float) -> list[float]:
        # Graine fixe : le contrôle doit rendre le même chiffre à chaque
        # exécution, sinon il n'est pas une preuve mais une impression.
        rng = np.random.default_rng(CONTROL_SEED)
        steps = rng.normal(0.0, sigma * multiplier, len(prices))
        return list(prices[0] * np.exp(np.cumsum(steps)))

    low, high = 1.0, 40.0
    for _ in range(40):
        mid = (low + high) / 2.0
        if tradable_window_ratio(walk(mid), horizon, cost, margin) < target:
            low = mid
        else:
            high = mid
    multiplier = (low + high) / 2.0

    real = np.array(
        oracle_holding_periods(prices, horizon, cost, margin), dtype=np.float64
    )
    control = np.array(
        oracle_holding_periods(walk(multiplier), horizon, cost, margin),
        dtype=np.float64,
    )

    print()
    print(
        f"  CONTRE-ÉPREUVE — marche sans mémoire, exposition calée à "
        f"{target * 100:.2f} % (marge {margin:.1f}x, sigma x{multiplier:.1f})"
    )
    print("  " + "-" * 74)
    print(f"  {'série':>22}  {'détentions':>10}  {'méd':>5}  {'méd/H':>6}  {'% < H':>7}")
    for label, sample in ((instrument.name, real), ("marche aléatoire", control)):
        median = float(np.median(sample))
        print(
            f"  {label:>22}  {len(sample):>10}  {median:>5.0f}  "
            f"{median / horizon:>6.2f}  {float(np.mean(sample < horizon)) * 100:>6.2f} %"
        )


def _report(instrument: Instrument) -> None:
    symbol = Symbol(instrument.name, AssetClass.INDICES)
    bars = load_bars(symbol, TimeFrame("M1"), instrument.parquet)
    prices = [f.features[PRICE_KEY] for f in build_feature_sets(bars)]

    cost = instrument.cost_model
    horizon = instrument.horizon

    print("\n" + "=" * 78)
    print(f"  {instrument.name} — horizon du label : {horizon} barres M1")
    print("=" * 78)
    print(
        f"  Coût A/R retenu : {cost.round_trip_cost * BPS:.3f} bps"
        f"  |  {len(prices)} barres"
    )
    print()
    print(
        f"  {'marge':>6}  {'détentions':>10}  {'min':>5}  {'méd':>5}  {'p75':>5}  "
        f"{'p95':>5}  {'max':>6}  {'méd/H':>6}  {'% < H':>7}  {'% temps':>8}  {'% fen.':>7}"
    )
    print("  " + "-" * 84)

    for margin in MARGINS:
        periods = oracle_holding_periods(prices, horizon, cost, safety_margin=margin)
        windows = len(oracle_target_exposure(prices, horizon, cost, margin))
        # Le ratio de fenêtres tradables du gate existant, rappelé sur la même
        # ligne : c'est la grandeur que la détention est censée réaliser.
        window_ratio = tradable_window_ratio(prices, horizon, cost, margin) * 100.0

        if not periods:
            print(
                f"  {margin:>5.1f}x  {0:>10}  "
                + "    —" * 5
                + f"  {'—':>6}  {'—':>7}  {0.0:>7.2f} %  {window_ratio:>6.2f} %"
            )
            continue

        lengths = np.array(periods, dtype=np.float64)
        median = float(np.median(lengths))
        exposed = float(lengths.sum())
        # Part des détentions plus courtes que l'horizon : le régime dangereux,
        # celui où un aller-retour dimensionné sur `horizon` barres est payé pour
        # un mouvement plus court. La médiane seule le masquerait.
        short = float(np.mean(lengths < horizon) * 100.0)
        print(
            f"  {margin:>5.1f}x  {len(periods):>10}  {lengths.min():>5.0f}  "
            f"{median:>5.0f}  {np.percentile(lengths, 75):>5.0f}  "
            f"{np.percentile(lengths, 95):>5.0f}  {lengths.max():>6.0f}  "
            f"{median / horizon:>6.2f}  {short:>6.2f} %  "
            f"{exposed / windows * 100.0:>7.2f} %  {window_ratio:>6.2f} %"
        )

    print()
    print("  Lecture : 'détentions' = nombre d'aller-retours distincts, donc de")
    print("  péages payés. '% < H' est la part de positions fermées AVANT")
    print("  l'horizon sur lequel le seuil d'entrée a été dimensionné — le seul")
    print("  régime dangereux. '% temps' est la part de barres exposées ; elle")
    print("  doit égaler '% fen.', le ratio du gate — l'écart révélerait une")
    print("  divergence entre les deux mesures.")

    _memoryless_control(prices, instrument, CONTROL_MARGIN)


def main() -> int:
    _print_decision_rule()
    for instrument in INSTRUMENTS:
        _report(instrument)
    print("\n" + "=" * 78 + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
