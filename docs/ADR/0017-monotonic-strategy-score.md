# ADR 0017 — Le Strategy Score est monotone en PnL net réel

- **Statut** : ACCEPTÉ
- **Date** : 2026-08-03
- **Contexte technique** : `src/aegis_trade/engine/scoring_engine.py`
- **Campagne déclenchante** : `.validation_registry/val_20260803_063600_MLStrategy_score_30.json`

## Contexte

Le `ScoringEngine` agrège les campagnes du framework de validation en un score
de 0 à 100. Le `ValidationRunner` approuve à partir de 75, et
`scripts/train_qlib_model.py` n'exporte un modèle que s'il est approuvé. Le score
est donc le portillon unique entre une hypothèse et un artefact réutilisable en
aval.

Le barème initial était **additif** : chaque campagne PASS créditait +10 points,
un Sharpe > 1 jusqu'à +15, un alpha positif +15, et une probabilité de ruine
< 5 % créditait +20 points. Un plafond à 49 s'appliquait si HOLD_OUT ou
WALK_FORWARD échouait.

Deux campagnes réelles ont montré que ce barème n'ordonne pas les stratégies
selon leur résultat économique :

| Campagne | Rendement net | Ancien score |
|---|---|---|
| `val_20260803_052640` | **-1.02 %** | **0** |
| `val_20260803_063600` | **-37.11 %** | **30** |

La stratégie qui a perdu 36 points de pourcentage de plus a obtenu un score
supérieur. Cause directe : le bonus Monte-Carlo de +20 points ne regardait que
`ruin_probability`, définie comme la probabilité de descendre sous -50 % du
capital. Une stratégie perdant systématiquement 37 % affiche
`ruin_probability = 0.0` — elle ne se ruine pas, elle saigne. Ce PASS créditait
20 points pleins, et le PASS de campagne lui-même 10 de plus.

Le rejet final (score 30 < 75) était donc correct par accident, pas par
construction. Il ne tenait qu'au plafond arbitraire à 49, lui-même contournable :
retirer HOLD_OUT et WALK_FORWARD de `active_campaigns` supprimait le plafond
tout en conservant les bonus. Un barème dans lequel désactiver un test augmente
le score n'est pas falsifiable.

## Décision

Le score est **multiplicatif**, jamais additif :

```
score = terme_économique(net_return) x facteur_DD x facteur_robustesse x facteur_anti_ruine
```

1. **Terme économique** — seule source de points. `50 x (1 + tanh(net_return / 0.10))`,
   dans (0, 100), strictement croissant, valant 50 à l'équilibre. `tanh` borne le
   score sans créer de palier : deux stratégies perdantes restent ordonnées entre
   elles, ce qui garde le barème exploitable comme diagnostic et pas seulement
   comme portillon.

2. **Facteur de drawdown** — `max(0, 1 - pire_DD / 0.30)`. Pénalité **continue et
   proportionnelle au drawdown réel**, remplaçant tout traitement binaire. La
   limite de 30 % est celle déjà appliquée par `HoldOutValidator` : un seul seuil
   de risque dans le système. Au-delà, le score s'annule quel que soit le
   rendement.

3. **Facteur de robustesse** — part pondérée des campagnes exigées effectivement
   passées. HOLD_OUT et WALK_FORWARD pèsent 2, MONTE_CARLO et BENCHMARK pèsent 1.
   **Une campagne absente compte comme un échec** : sans cela, désactiver une
   campagne gênante augmenterait le score, et la faille de falsifiabilité serait
   simplement déplacée.

4. **Facteur anti-ruine** — `max(0, 1 - ruin_probability)`. L'anti-ruine devient
   une **pénalité, jamais un bonus**. Éviter la ruine n'est pas une performance,
   c'est un prérequis ; un multiplicateur ne peut que retirer des points.

Le plafond arbitraire à 49 est **supprimé**. Il devient inutile : avec les poids
ci-dessus, l'échec d'une seule campagne critique ramène le facteur de robustesse
à 4/6, ce qui rend 75 structurellement inatteignable (67 au maximum théorique).
Le portillon découle de la structure, plus d'une constante posée à côté.

En complément, les validateurs exposent désormais la **perte réelle** et non
seulement la ruine :

- `HoldOutValidator`, `WalkForwardValidator`, `BenchmarkValidator` : `net_return`.
- `WalkForwardValidator` : rendement **composé** à travers les folds (un fold à
  -50 % ne se compense pas avec un fold à +50 %), et pire drawdown inter-folds.
- `MonteCarloValidator` : `median_net_return`, `loss_probability`,
  `expected_shortfall` (moyenne du quintile bas). Son PASS exige désormais un
  rendement médian positif, pas seulement l'absence de ruine.

Un `net_return` absent donne un score de **0**, pas un score neutre : une
stratégie non mesurée ne doit pas franchir un gate en aval.

## Conséquences

**Acquis**

- Propriété garantie : à facteurs de risque constants, plus de PnL net ne peut
  jamais donner moins de score. Testée sur 6 intervalles de rendement, dont le
  couple historique -37 % / -1 %.
- Le cas `val_20260803_063600` note désormais **0** au lieu de 30 (drawdown de
  37 % au-delà de la limite de 30 %).
- Falsifiabilité : retirer une campagne ne peut plus augmenter le score.
- Le barème reste capable d'approuver — vérifié par test, un barème qui ne peut
  jamais approuver serait un mur, pas un barème.

**Coûts assumés**

- Les scores historiques du registre ne sont pas comparables aux nouveaux. Les
  artefacts existants restent en place comme trace, non comme référence.
- Le produit de quatre facteurs est plus sévère qu'une somme de bonus : des
  stratégies auparavant notées 30-49 tombent près de 0. C'est l'effet voulu.
- Les constantes (saturation à 10 %, limite de DD à 30 %, poids) restent des
  choix de conception, pas des résultats dérivés. Elles sont regroupées en
  constantes nommées du module et devront être resserrées quand des données
  démo réelles seront accumulées.

## Alternatives écartées

- **Corriger seulement le bonus Monte-Carlo.** Aurait traité le symptôme observé
  en laissant la structure additive intacte : tout futur bonus non corrélé au PnL
  aurait recréé la même inversion.
- **Garder l'additif avec un gate dur `net_return <= 0 -> 0`.** Rend toutes les
  stratégies perdantes indistinguables (une perte de 1 % et une de 37 % notent 0),
  ce qui détruit la valeur diagnostique du score pendant la phase de recherche.
- **Sortir la décision d'approbation du score.** Séparer proprement mérite et
  autorisation reste défendable, mais déplace la logique de gate dans le
  `ValidationRunner` sans corriger la non-monotonie du score lui-même. À
  reconsidérer si des consommateurs multiples du score apparaissent.
