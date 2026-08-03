# ADR 0019 — L'hypothèse « signal exploitable à 1 barre sur Crash 1000 » est abandonnée

- **Statut** : ACCEPTÉ
- **Date** : 2026-08-03
- **Contexte technique** : `scripts/train_qlib_model.py`,
  `scripts/diagnose_prediction_scale.py`, `scripts/diagnose_horizon_vs_cost.py`
- **Campagne déclenchante** : `.validation_registry/val_20260803_205954_MLStrategy_score_0.json`
- **Dépend de** : ADR 0017 (barème monotone), ADR 0018 (seuils dérivés du coût)

## Contexte

Les ADR 0017 et 0018 ont corrigé les deux défauts qui rendaient toute conclusion
scientifique impossible : un barème non monotone (une perte de -37 % notait mieux
qu'une perte de -1 %) et un seuil d'entrée ~15x sous le coût du trade qu'il
déclenchait.

Ces deux corrections faites, la question posée était : **avec un seuil réaliste
devant le coût, un edge net de frais apparaît-il ?** C'est la question qui
détermine si la Phase 4 (Kronos-mini) a un sens.

## Constat

Relance de `scripts/train_qlib_model.py` sur les mêmes données (Crash 1000 M1,
5000 barres, split chronologique 70/30, LightGBM 300 arbres) :

```
Coût aller-retour : 30.00 bps  |  Seuil d'entrée : 0.003000
[FAIL] hold_out      net_return 0.0    [FAIL] walk_forward  net_return 0.0
[FAIL] monte_carlo   0 trades          [FAIL] benchmark     alpha -0.0073
Score : 0.0/100 — Approuvé : False
```

**Zéro trade.** Aucune prédiction n'a franchi la zone morte de 30 bps.

Un zéro-trade est ambigu en soi : modèle trop plat, ou marché trop calme ? Deux
diagnostics tranchent.

### 1. Amplitude prédite vs coût (1500 barres hors-échantillon)

| Grandeur | Valeur |
|---|---|
| Seuil de rentabilité | **30.00 bps** |
| Prédiction \|médiane\| | 1.98 bps |
| Prédiction \|max\| | 8.92 bps |
| **Mouvement RÉEL \|médiane\|** | **0.61 bps** |
| **Mouvement RÉEL \|max\|** | **23.47 bps** |
| Barres où le marché bouge de ≥ 30 bps | **0 / 1499 (0.00 %)** |

Le modèle prédit 3.4x trop petit pour le seuil — mais **le marché lui-même ne
franchit jamais 30 bps en une barre M1**. Le plafond n'est pas dans le modèle.
Aucun prédicteur, aussi bon soit-il, ne peut extraire d'un mouvement de 0.61 bps
de quoi payer 30 bps de péage. Un oracle parfait perdrait de l'argent.

### 2. Le verdict ne dépend pas du chiffre de coût retenu

30 bps est le coût du `SimulatedBroker`, pas une mesure Deriv (ADR 0018). Un
balayage sur le coût lève l'objection :

| Coût aller-retour | % barres au-dessus |
|---|---|
| 30 bps | 0.00 % |
| 10 bps | 2.33 % |
| 4 bps | 4.14 % |
| 2 bps | 4.67 % |
| 1 bps | 4.87 % |
| **0.5 bps** | **97.60 %** |

La discontinuité entre 1 bps (4.87 %) et 0.5 bps (97.60 %) révèle un fait de
microstructure : **le prix de Crash 1000 est quantifié, un tick vaut ~0.6 bps**.
En une barre M1, on capte un tick ou rien. Tout coût aller-retour supérieur à
~0.6 bps élimine donc l'horizon 1 barre, quel que soit le broker. Le résultat est
robuste, pas conditionnel à une hypothèse de frais.

### 3. Le mouvement ne dépasse le coût qu'à un horizon bien plus long

| Horizon | \|médiane\| | % fenêtres > 30 bps |
|---|---|---|
| 1 barre | 0.61 bps | 0.00 % |
| 5 barres | 3.03 bps | 0.00 % |
| 15 barres | 8.98 bps | 0.00 % |
| 30 barres | 11.19 bps | 1.22 % |
| 60 barres | 15.96 bps | 19.17 % |
| 120 barres | 26.90 bps | 39.42 % |
| 240 barres | 42.81 bps | 63.65 % |

L'espace économique n'existe qu'à partir de ~60 barres de détention.

## Décision

**L'hypothèse « signal exploitable sur cette configuration de features à un
horizon de 1 barre » est formellement abandonnée.** Elle est réfutée par les
données, pas par un manque d'effort d'ingénierie.

Le label `forward_return_1` du `DatasetBuilder` demande au modèle de prédire une
grandeur (0.61 bps médians) inférieure d'un facteur ~50 au coût de l'action
qu'elle déclenche. Aucune amélioration de modèle ne corrige un rapport
signal/péage défavorable par construction.

**Conséquence directe sur la Phase 4 : Kronos-mini est suspendu sur cette
cible.** Substituer un modèle plus puissant à LightGBM sur le même label à 1
barre reviendrait à mieux prédire une grandeur trop petite pour être tradée. Le
gain de précision serait réel et économiquement nul. La Phase 4 ne reprend
qu'après redéfinition de l'horizon cible.

**Ce qui n'est PAS décidé ici** : que Crash 1000 soit intradable, ou que le jeu
de features soit sans valeur. Seul l'horizon 1 barre est réfuté. Les mêmes
features à un horizon de 60-240 barres restent une hypothèse ouverte, non testée.

## Conséquences

**Acquis**

- La question posée a une réponse chiffrée et reproductible : non, aucun edge net
  de frais, et la cause est identifiée (horizon, pas modèle).
- Le cadre corrigé (ADR 0017/0018) a produit son premier rejet propre : score 0,
  aucun export dans `data/models/`, artefact conservé au registre.
- Deux scripts de diagnostic réutilisables, indépendants de tout modèle :
  `diagnose_prediction_scale.py` (prédiction vs coût) et
  `diagnose_horizon_vs_cost.py` (mouvement par horizon + balayage de coût).
  Tout futur couple marché/horizon doit passer ce test AVANT qu'un modèle soit
  entraîné — c'est un contrôle de faisabilité économique, pas un post-mortem.

**Coûts assumés**

- Le Lot 4 ne livre aucun modèle exportable. C'est le résultat correct : un
  artefact non validé en aval serait pire qu'aucun artefact.
- Les 5000 barres de Crash 1000 ne suffisent pas pour un horizon de 240 barres
  (1500 barres de test = ~6 fenêtres indépendantes). Tester l'horizon long exige
  une ré-ingestion de données, pas seulement un changement de paramètre.

## Alternatives écartées

- **Baisser le seuil pour retrouver des trades.** C'est exactement le défaut
  corrigé par l'ADR 0018, et ce serait du gate-adjusting après lecture du
  résultat. Les 325 trades de la campagne précédente n'étaient pas un signal,
  c'étaient 37 % de frais.
- **Lancer Kronos-mini sur `forward_return_1` malgré tout.** Validerait un modèle
  contre une cible économiquement intradable. Un meilleur modèle sur un mauvais
  label reste un mauvais système, et le succès apparent masquerait le défaut.
- **Changer de marché en gardant l'horizon 1 barre.** La quantification du tick
  n'est pas propre à Crash 1000 ; il faudrait de toute façon mesurer d'abord le
  ratio tick/coût. C'est précisément ce que fait `diagnose_horizon_vs_cost.py`,
  qui devient le préalable au choix de marché.
