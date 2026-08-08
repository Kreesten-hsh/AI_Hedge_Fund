# ADR 0023 — La sortie par persistance du signal est conservée : la détention médiane vaut l'horizon

- **Statut** : ACCEPTÉ
- **Date** : 2026-08-04
- **Contexte technique** : `src/aegis_trade/domain/tradability.py`,
  `src/aegis_trade/application/strategy/ml_strategy.py`,
  `scripts/diagnose_signal_persistence.py`,
  `tests/domain/test_tradability.py`
- **Dépend de** : ADR 0018 (seuils dérivés du coût), ADR 0021 (coût A/R mesuré),
  ADR 0022 (horizons revalidés sur 75000 barres)
- **Résout** : la question ouverte de SIG-02 — « horizon du label » ≠ « durée de
  détention »

## Contexte

SIG-02 a retenu deux horizons de label : **5 barres M1 sur Crash 1000**,
**10 sur Boom 1000**. Ces cibles viennent de `tradable_window_ratio`, qui mesure
94.0 % et 87.2 % de fenêtres tradables à marge 3x.

Ce gate mesure une sortie **temporelle**. `absolute_moves` compare `t+horizon`
à `t` : il suppose la position ouverte en `t` et fermée exactement en
`t+horizon`. Les 94.0 % sont le plafond oracle de *cette* stratégie.

`MLStrategy` n'est pas cette stratégie. Elle réémet une exposition cible à chaque
barre et sort quand le rendement attendu retombe dans la zone morte ou change de
sens — une sortie **par persistance**. Sa détention est une longueur de séquence
de signal, que rien ne ramène à l'horizon du label. Le gate décrivait donc le
plafond d'une stratégie différente de celle qu'on s'apprêtait à entraîner.

Deux régimes de divergence, asymétriques :

- **détention < horizon** : un aller-retour complet payé, dimensionné sur un
  mouvement de 5 barres, pour capter un mouvement d'une barre. C'est l'horizon
  1 barre — réfuté trois fois (ADR 0019, 0021, 0022) — réintroduit par la porte
  de sortie. **Seul régime dangereux.**
- **détention > horizon** : un seul aller-retour au lieu de plusieurs, coût par
  unité d'exposition plus bas. Économiquement favorable, mais le gate cesse de
  décrire ce qui se passe et le seuil d'entrée devient sur-conservateur.

La question ne se tranche pas par goût architectural. Elle est **mesurable sans
entraîner quoi que ce soit** : on calcule l'exposition qu'une `MLStrategy`
déclarerait si elle prédisait parfaitement `forward_return_horizon`, puis la
distribution des longueurs de séquence. Même discipline que le gate de
tradabilité, appliquée à la sortie plutôt qu'à l'entrée.

## Règle de décision — pré-enregistrée

Écrite et imprimée par le script **avant** toute mesure
(`_print_decision_rule`), pour qu'aucune des trois issues ne soit rédigée après
lecture des chiffres. Comparaison : détention **médiane** de l'oracle vs horizon
du label.

| Mesure | Verdict |
|---|---|
| médiane ≈ horizon | sortie par persistance **CONSERVÉE**. `MLStrategy` inchangée, gate valide tel quel. |
| médiane >> horizon | sortie par persistance **CONSERVÉE**. Gate à re-mesurer à la détention réelle (plus permissif, jamais moins). |
| médiane ≈ 1 barre | sortie par persistance **RÉFUTÉE**. Soit sortie temporelle forcée à l'horizon, soit l'horizon tombe pour cette stratégie. |

Aucune de ces issues n'était l'issue souhaitée. C'est le point de l'écrire avant.

## Constat

Mesures sur 75000 barres M1 par instrument, coûts **retenus** de l'ADR 0021
(0.745 / 1.063 bps) — pas les mesures live plus basses de COST-02 (0.652 /
0.951). Basculer sur les plus basses élargirait les fenêtres et raccourcirait
les détentions dans le sens qui arrange : le défaut corrigé par l'ADR 0018.

### 1. Crash 1000 — horizon 5 barres, coût 0.745 bps

| marge | détentions | min | méd | p75 | p95 | max | méd/H | % < H | % temps | % fen. |
|---|---|---|---|---|---|---|---|---|---|---|
| 1.0x | 5696 | 1 | 6 | 14 | 45 | 161 | 1.20 | 10.66 % | 98.02 % | 98.02 % |
| 2.0x | 5708 | 1 | 6 | 14 | 43 | 161 | 1.10 | 11.53 % | 96.09 % | 96.09 % |
| 3.0x | 5703 | 1 | 5 | 14 | 42 | 161 | 1.00 | 12.38 % | 93.97 % | 93.97 % |

### 2. Boom 1000 — horizon 10 barres, coût 1.063 bps

| marge | détentions | min | méd | p75 | p95 | max | méd/H | % < H | % temps | % fen. |
|---|---|---|---|---|---|---|---|---|---|---|
| 1.0x | 4202 | 1 | 10 | 19 | 52 | 205 | 1.00 | 21.37 % | 95.98 % | 95.98 % |
| 2.0x | 4181 | 1 | 10 | 19 | 49 | 201 | 1.00 | 23.49 % | 91.63 % | 91.63 % |
| 3.0x | 4183 | 1 | 10 | 18 | 47 | 178 | 1.00 | 26.56 % | 87.18 % | 87.18 % |

La médiane vaut l'horizon, à la barre près, sur les deux instruments et aux trois
marges. Le verdict ne bascule pas d'une marge à l'autre — c'est exactement le
test de fragilité qui a écarté les horizons 2 et 3 barres (ADR 0022).

### 3. `% temps` égale `% fen.` à la décimale — les deux mesures ne peuvent pas diverger

Une barre est détenue exactement quand sa fenêtre couvre le péage. La somme des
détentions doit donc redonner le numérateur du ratio du gate. L'identité tient
sur les six lignes et est **verrouillée par un test**
(`test_holding_bars_reconcile_with_the_tradable_window_ratio`). Sans elle, la
nouvelle mesure et le gate existant pourraient dériver en silence et ce
diagnostic ne prouverait plus rien sur le gate.

### 4. La persistance appartient aux séries, pas à la construction du label

Doute mécanique à lever : `forward_return_5[i]` et `forward_return_5[i+1]`
partagent 4 barres sur 5. Un unique mouvement peint donc ~5 fenêtres
consécutives du même signe, et une médiane égale à l'horizon pourrait n'être
qu'un artefact de recouvrement — auquel cas elle se reproduirait sur n'importe
quelle série et ne dirait rien de Crash ni de Boom.

Contrôle : marche aléatoire à incréments i.i.d., **zéro mémoire par
construction**, graine fixe 7. Premier essai naïf (σ calé sur la série réelle) :
confondu — le contrôle n'exposait que 74.08 % des barres contre 93.97 % pour
Crash, et une série qui franchit moins souvent le seuil produit des séquences
plus courtes pour une raison sans rapport avec la mémoire. σ est donc ajusté par
bisection jusqu'à ce que le contrôle expose **exactement la même part de
fenêtres** que la série réelle.

| marge 3.0x | exposition calée | série | détentions | méd | méd/H | % < H |
|---|---|---|---|---|---|---|
| Crash 1000 | 93.97 % (σ ×4.4) | réelle | 5703 | 5 | **1.00** | 12.38 % |
| | | marche aléatoire | 15203 | 3 | **0.60** | 58.00 % |
| Boom 1000 | 87.18 % (σ ×2.1) | réelle | 4183 | 10 | **1.00** | 26.56 % |
| | | marche aléatoire | 10540 | 3 | **0.30** | 74.35 % |

À exposition **égale**, la marche sans mémoire tombe à 0.60 et 0.30 fois
l'horizon, avec 58 % et 74 % de détentions courtes contre 12 % et 27 %. Elle paie
aussi ~2.6 fois plus de péages pour couvrir le même temps d'exposition. Artefact
réfuté : la persistance est une propriété de Crash et Boom.

## Décision

### 1. La sortie par persistance est CONSERVÉE. `MLStrategy` est inchangée.

Application directe de la règle pré-enregistrée, branche « médiane ≈ horizon ».
Aucun code de stratégie n'est modifié : pas de sortie temporelle forcée, pas de
compteur de barres, pas de suivi de position dans la stratégie. La conception
sans état est préservée — la faire suivre sa propre position aurait introduit un
second registre de vérité, donc une désynchronisation possible avec le broker.

### 2. Le gate de tradabilité reste valide tel quel pour SIG-02.

Les 94.0 % / 87.2 % décrivent bien, en médiane, ce que la stratégie va réellement
faire. L'écart entre stratégie mesurée et stratégie entraînée, qui rendait le
gate suspect, est mesuré et nul en médiane. Les horizons 5 / 10 barres tiennent.

### 3. Les 12.4 % / 26.6 % de détentions sous l'horizon sont un coût ASSUMÉ, pas un détail.

Le régime dangereux est minoritaire, pas nul. Sur Boom, plus d'une détention sur
quatre se ferme avant l'horizon sur lequel le seuil d'entrée a été dimensionné.
La conséquence est bornée et connue : ces positions paient un aller-retour
complet pour un mouvement plus court que prévu. C'est le prix de la sortie sans
état, retenu en connaissance de cause. Il ne sera pas re-débattu : il sera
**relevé dans le P&L du backtest**, où il apparaît en net sans avoir besoin
d'être modélisé.

La médiane seule aurait masqué ce régime — la colonne `% < H` a été ajoutée
précisément pour ça, et elle ne peut que durcir le verdict, jamais l'assouplir.

### 4. La propriété est mesurée, jamais garantie. Elle se re-mesure.

Aucune inégalité générale n'est démontrée ici : ce résultat vaut pour Crash 1000
et Boom 1000, à ces horizons, sur ces 75000 barres. Tout nouvel instrument ou
nouvel horizon repasse par `scripts/diagnose_signal_persistence.py` avant
entraînement. Le script est rejouable, la graine du contrôle est versionnée.

### 5. Ce que la mesure N'EST PAS.

Ce n'est pas une borne sur la détention d'un **modèle réel**. C'est la structure
de persistance du **label** sous prédiction parfaite. Le bruit de prédiction
fragmente typiquement les séquences, mais peut aussi en souder deux — aucune
inégalité n'est démontrée dans un sens ou dans l'autre, et aucune n'est
revendiquée. Ce qui est décisif est plus faible et suffit : si le label lui-même
ne persistait qu'une barre, aucune sortie par persistance ne pourrait tenir 5
barres. Il persiste.

## Conséquences

- SIG-02 est débloqué : l'entraînement peut commencer à horizon 5 (Crash) / 10
  (Boom), sortie par persistance.
- `oracle_target_exposure` et `oracle_holding_periods` entrent dans le domaine
  pur (`domain/tradability.py`), sans dépendance broker ni I/O.
  `oracle_target_exposure` **reproduit la règle de décision exacte** de
  `MLStrategy.generate_signals` : c'est ce qui fait de cette mesure une réponse à
  SIG-02 plutôt qu'une statistique de persistance générique. Les deux resteront
  à faire évoluer ensemble.
- `absolute_moves` est refactorisé sur une primitive signée privée
  (`_forward_returns`) partagée avec l'oracle. Un seul site de validation :
  dupliquer les gardes les ferait diverger en silence.
- La docstring de `MLStrategy` affirmait que l'horizon de détention était
  cohérent avec l'horizon de prédiction « parce que le modèle ne prédit qu'une
  barre ». Vrai à horizon 1 uniquement, **faux depuis que l'horizon est
  paramétrable** (ADR 0022). Corrigé : la docstring pointe désormais cet ADR et
  dit que l'indépendance est structurelle et la coïncidence, mesurée.
