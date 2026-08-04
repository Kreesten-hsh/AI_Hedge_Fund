# ADR 0020 — La cible d'horizon se dérive d'un budget de coût, pas d'un coût supposé

- **Statut** : ACCEPTÉ
- **Date** : 2026-08-04
- **Contexte technique** : `src/aegis_trade/domain/tradability.py`,
  `scripts/diagnose_cost_budget_by_horizon.py`
- **Dépend de** : ADR 0018 (seuils dérivés du coût), ADR 0019 (horizon 1 barre réfuté)
- **Corrige** : ADR 0019, section « discontinuité / quantification du tick »

## Contexte

L'ADR 0019 a réfuté l'horizon 1 barre et proposé une fenêtre cible de **60-240
barres M1** pour SIG-02. Cette fenêtre est calculée à partir des **30 bps** du
`SimulatedBroker` — un chiffre dont l'ADR 0018 dit lui-même qu'il n'est **pas une
mesure Deriv**.

Deux conséquences rendaient la suite fragile. D'abord, organiser DATA-01 et SIG-02
autour de 60-240 barres revient à bâtir la phase suivante sur un nombre non
mesuré, alors que l'ADR 0019 vient précisément de refuser ce raccourci pour la
question M15 vs pagination. Ensuite, 240 barres M1 valent **4 heures par
position**, ce qui contredit l'objectif de départ — beaucoup de petites décisions
fréquentes plutôt que des positions tenues des heures. La cible et l'intention
divergeaient sans que personne l'ait décidé.

## Constat

### 1. Le spread réel Deriv n'est pas lisible depuis l'environnement de développement

Sondage direct de l'API WebSocket (`wss://ws.derivws.com/websockets/v3`) :

| Requête | Résultat |
|---|---|
| `active_symbols` (brief, full, toutes variantes) | **0 symbole** |
| `contracts_for: CRASH1000` | `OfferingsInvalidSymbol` |
| `proposal` MULTUP multiplier | `OfferingsValidationError`, `field: platform` |
| `ticks` / `ticks` subscribe | `InvalidSymbol` |
| `ticks_history` (candles et ticks) | **fonctionne** |

Testé sur trois `app_id` (1089, 16929, 36544) et deux hôtes (`ws.derivws.com`,
`ws.binaryws.com`) : identique. `website_status` renvoie `clients_country: bj`.

Le catalogue d'offres est vide pour cette juridiction, ce qui ferme en cascade
toutes les routes de spécification de contrat. `ticks_history` survit mais ne
renvoie **qu'un prix unique par horodatage** — jamais `bid`/`ask`. Le spread n'est
donc pas mesurable ici, et la commission de multiplier non plus.

**Ce chiffre reste manquant.** Il n'est pas remplacé par une estimation.

### 2. La décision d'horizon n'a pas besoin de ce chiffre

Plutôt que de supposer un coût, on inverse la question : *pour chaque horizon,
quel est le coût aller-retour maximal qui laisse encore une part donnée de
fenêtres tradables ?* La réponse ne dépend d'aucune hypothèse de frais.

`max_viable_round_trip_cost(prices, horizon, min_ratio)` — inverse exact de
`tradable_window_ratio` — sur Crash 1000, 5000 barres, budget en bps :

| Détention | ≥50 % fenêtres | ≥20 % | ≥10 % | ≥5 % |
|---|---|---|---|---|
| 1 min | 0.60 | 0.66 | 0.69 | 2.49 |
| 15 min | 8.88 | 9.49 | 15.46 | 22.00 |
| 30 min | 11.11 | 18.14 | 20.97 | 29.25 |
| 1 h | 16.55 | 29.55 | 35.88 | 40.06 |
| 2 h | 26.28 | 45.41 | 58.38 | 68.99 |
| 4 h | 41.77 | 69.91 | 86.89 | 104.45 |

**L'intuition qui a déclenché cette mesure est confirmée.** Si le coût A/R réel
est de l'ordre de 9 bps, l'espace économique s'ouvre dès **15 minutes** de
détention, pas 60-240 barres. La fenêtre de l'ADR 0019 était un artefact des
30 bps supposés.

### 3. Passer en M15 ne rétrécit pas la cible économique

Comparaison à détention égale, **sur la période commune aux deux séries** :

| Détention | M1 | M15 | Écart |
|---|---|---|---|
| 15 min | 9.49 | 9.46 | −0.3 % |
| 30 min | 18.14 | 18.15 | +0.1 % |
| 1 h | 29.55 | 28.73 | −2.8 % |
| 2 h | 45.41 | 45.78 | +0.8 % |
| 4 h | 69.91 | 69.85 | −0.1 % |
| 8 h | 111.60 | 111.19 | −0.4 % |

La restriction à la période commune n'est pas cosmétique : comparées sur leurs
étendues natives (M1 ~3.5 jours, M15 ~52 jours), les mêmes séries affichent un
écart de **−23 % à 8 h**. C'est un changement de régime de marché, pas un effet
d'agrégation. Sans cette restriction, le script aurait publié un artefact.

La pagination fonctionne également (vérifié : `end` reculé dans le temps renvoie
bien un bloc antérieur), donc les deux routes de DATA-01 sont ouvertes.

### 4. Correction d'une erreur factuelle de l'ADR 0019

L'ADR 0019 attribue la discontinuité du balayage de coût (4.87 % à 1 bps →
97.60 % à 0.5 bps) à une quantification du prix, en affirmant « un tick vaut
~0.6 bps ». **C'est faux.** L'incrément de prix mesuré est de 0.001 sur un prix
de ~5728, soit **0.0017 bps par tick** — un facteur ~350 d'écart. Un mouvement
médian de 0.61 bps représente donc ~350 ticks, pas un tick.

La vraie cause est que la distribution à 1 barre est **quasi-dégénérée** :
médiane 0.606 bps et p95 0.761 bps. Presque toutes les barres bougent de la même
petite quantité, d'où le saut brutal du balayage de part et d'autre de 0.6.

**Le verdict de l'ADR 0019 est intact** — l'horizon 1 barre reste réfuté, et le
budget de 0.60-0.69 bps mesuré ici le confirme indépendamment. Seule
l'explication mécanique était erronée. Elle est corrigée parce qu'un raisonnement
faux laissé dans un ADR accepté sera réutilisé comme prémisse.

## Décision

**1. `max_viable_round_trip_cost` entre au domaine.** Testée par inversion contre
`tradable_window_ratio` (le budget rendu tient la part promise) et par
contre-épreuve de serrage (un coût juste au-dessus la casse) — sans quoi
retourner zéro passerait le premier test.

**2. La fenêtre « 60-240 barres » de l'ADR 0019 est retirée comme cible.** Elle
est remplacée par la table ci-dessus. SIG-02 vise l'horizon le plus court dont le
budget dépasse le coût réel une fois mesuré, ce qui préserve l'objectif de
décisions fréquentes au lieu de le sacrifier à un chiffre supposé.

**3. DATA-01 passe en M15.** À budget économique équivalent (±3 %), le M15 donne
~52 jours par requête contre ~3.5 en M1. La pagination reste disponible si un
horizon court exige une granularité fine.

> **RENVERSÉ par l'ADR 0021 — la mesure de départage tient, sa conclusion
> opérationnelle non.** Le coût A/R réel mesuré vaut 0.745 bps, d'où une cible
> de **5 barres M1 (5 minutes)**, non représentable en M15 dont la barre
> minimale vaut 15 minutes. Garder le M15 triplerait la détention par contrainte
> de format de données au lieu d'une mesure. DATA-01 repasse en **pagination
> M1**. L'équivalence de budget à ±3 % au-delà de 15 min reste vraie et rend le
> M15 réutilisable si une cible ≥15 min réapparaît — c'est bien la clause
> « si un horizon court exige une granularité fine » ci-dessus qui se déclenche.

**4. Mesurer le coût Deriv réel devient un prérequis explicite de SIG-02**, à
faire hors API publique (compte réel : spread affiché plus commission de
multiplier). Tant qu'il manque, aucune valeur de coût n'est câblée : la table de
budget est publiée, la ligne à retenir sera choisie quand le chiffre existera.

> **RÉSOLU par l'ADR 0021.** Coût A/R mesuré : **0.745 bps** sur Crash 1000,
> **1.063 bps** sur Boom 1000, par aller-retours immédiats sur compte démo. Deux
> précisions sur la formulation ci-dessus : il n'y a **pas de spread** (flux à
> prix unique, ce que `ticks_history` indiquait déjà), et la commission est
> prélevée **une fois** par aller-retour, pas deux.

## Conséquences

**Acquis**

- La cible d'horizon ne dépend plus d'un coût supposé. Le coût réel, quand il
  arrivera, se lira dans la table sans re-mesure.
- L'objectif « petites décisions fréquentes » est réconcilié avec la mesure :
  15-30 min redevient plausible, contre 4 h précédemment.
- DATA-01 est tranché par la mesure, pas par préférence, et sa réserve
  d'agrégation est levée **pour la métrique de décision d'entrée**.
- Une erreur de raisonnement dans un ADR accepté est corrigée avant réutilisation.

**Coûts assumés**

- **Le coût Deriv réel reste non mesuré.** C'est la limite principale de cet ADR.
  La table est un budget, pas un verdict : aucun horizon n'est déclaré viable ici.
- **Le test M15 est aveugle au chemin intra-fenêtre par construction** — il
  compare des mouvements de bout en bout. Il ne dit rien sur la question de savoir
  si des features calculées en M15 voient encore les spikes de Crash 1000. Cette
  réserve du backlog reste **ouverte** et se tranche côté features.
- La table est mesurée sur 5000 barres d'une seule période (~3.5 jours en M1). Les
  budgets sont indicatifs d'un régime, et la puissance statistique d'un horizon
  reste le travail de DATA-01.
- `min_ratio` reste un choix non dérivé, comme dans `is_horizon_tradable`. La
  table montre quatre valeurs côte à côte au lieu d'en figer une.

## Alternatives écartées

- **Estimer le spread Deriv depuis la documentation publique ou une valeur
  courante d'indice synthétique.** Produirait un chiffre d'apparence mesurée mais
  non vérifié, exactement le défaut que cet ADR corrige. Un trou documenté vaut
  mieux qu'une estimation présentée comme une mesure.
- **Avancer sur DATA-01/SIG-02 avec 30 bps « en hypothèse conservatrice à affiner
  ensuite ».** Toute la phase serait organisée autour d'un horizon connu comme
  probablement surestimé, et l'affinage arriverait après que les choix
  structurants soient faits.
- **Garder `tradable_window_ratio` seul et balayer les coûts à la main.** C'est ce
  que faisait le script de l'ADR 0019 ; ça donne une grille discrète et laisse la
  lecture du seuil critique à l'œil, au lieu de le calculer.
- **Trancher M15 vs pagination sur les étendues natives des deux séries.** Aurait
  conclu à une perte de 23 % due à l'agrégation, alors que c'est un effet de
  période. Mesure invalide, conclusion fausse.
