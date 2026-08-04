# ADR 0022 — Pagination M1 : 52 jours d'historique, et la table d'horizon tient

- **Statut** : ACCEPTÉ
- **Date** : 2026-08-04
- **Contexte technique** : `src/aegis_trade/providers/deriv/historical_data.py`,
  `tests/providers/deriv/test_historical_pagination.py`,
  `scripts/fetch_training_data.py`
- **Dépend de** : ADR 0020 (budget par horizon), ADR 0021 (coût A/R mesuré)
- **Résout** : DATA-01

## Contexte

L'ADR 0021 a mesuré le coût A/R réel (0.745 bps sur Crash 1000) et en a dérivé
une cible de **5 barres M1**. Il a du même coup renversé la décision M15 de
l'ADR 0020 : une cible de 5 minutes n'est pas représentable dans une barre de 15
minutes. DATA-01 repassait donc en pagination M1 — décision prise, non
implémentée.

Deux choses restaient ouvertes. La pagination existait comme sonde manuelle
(« reculer `end` renvoie bien un bloc antérieur »), pas comme code testé. Et la
table d'horizon de l'ADR 0021 était calculée sur **5000 barres, ~3.5 jours,
un seul régime de marché** — assez pour trancher, pas assez pour être tenue
pour acquise.

## Constat

### 1. La pagination fonctionne et rend 52 jours en ~15 requêtes

`fetch_candles_paginated` recule `end` d'exactement une granularité sous la plus
ancienne barre reçue. Résultat en conditions réelles, par instrument :

| Mesure | Valeur |
|---|---|
| Barres obtenues | 75000 (cible atteinte, historique non épuisé) |
| Étendue | 52 jours 02:00 |
| Requêtes | 15 |
| Horodatages dupliqués | 0 |
| Trous | 1 seul écart de 120 s sur 74999 intervalles |

Contre 5000 barres et ~3.5 jours par requête unique. Les deux instruments
(`CRASH1000`, `BOOM1000`) sont ingérés à cette profondeur.

### 2. Quatre pièges de pagination, épinglés par des tests

Chacun produit un jeu de données faux qui **ne lève aucune erreur** — d'où huit
tests sur connexion doublée plutôt qu'une inspection visuelle du parquet :

| Piège | Effet s'il passe | Garde |
|---|---|---|
| Blocs servis du plus récent au plus ancien | `build_feature_sets` calcule des rendements sur une série non triée | tri par epoch, monotonie vérifiée |
| Barres resservies d'un bloc à l'autre | un doublon donne un rendement nul, indistinguable d'une vraie observation | indexation par epoch |
| `end` reculé de la mauvaise quantité | réutiliser la plus ancienne barre la duplique ; reculer de plus d'une granularité ouvre un trou | `end = oldest - granularity`, valeur exacte assertée |
| `page_size > 5000` | le serveur renvoie 5000 **en silence** ; tous les curseurs se décalent | `ValueError` |

Deux choix supplémentaires sont fixés par test parce qu'ils sont réversibles
sans casse apparente : la troncature à `target_count` garde les barres les plus
**récentes** (celles sur lesquelles un modèle destiné à trader doit être validé),
et une erreur API en cours de pagination **remonte** au lieu de renvoyer un
historique partiel qui passerait pour complet.

La condition d'arrêt mérite d'être notée : la boucle s'arrête quand un bloc
apporte **moins de barres inédites qu'une page pleine**, pas quand il n'en
apporte aucune. Un bloc partiellement chevauchant signale déjà que le serveur a
buté sur le début de son historique.

### 3. La table d'horizon tient sur 15x plus de données

Ratios de fenêtres tradables au coût mesuré, **75000 barres M1**, par marge de
sécurité :

| Horizon | Crash 1.0x / 2.0x / 3.0x | Boom 1.0x / 2.0x / 3.0x |
|---|---|---|
| 1 | 5.8 % / 5.1 % / 4.9 % | 5.4 % / 5.1 % / 4.7 % |
| 2 | 99.0 % / 9.6 % / 9.1 % | 96.3 % / 9.5 % / 8.9 % |
| 3 | 98.6 % / 97.2 % / 12.8 % | 98.3 % / 13.4 % / 12.5 % |
| **5** | **98.0 % / 96.1 % / 94.0 %** | 97.4 % / 94.7 % / 23.4 % |
| **10** | 97.2 % / 94.2 % / 91.5 % | **96.0 % / 91.6 % / 87.2 %** |
| 15 | 96.8 % / 93.3 % / 89.7 % | 94.8 % / 89.2 % / 84.4 % |
| 30 | 96.7 % / 93.9 % / 90.7 % | 95.4 % / 90.2 % / 85.3 % |

Les verdicts de l'ADR 0021 tiennent à ~1 point près, sur un échantillon 15x plus
large couvrant un régime de marché différent :

- **Horizon 1 reste réfuté** (5.8 % contre 6.2 % annoncés). Troisième
  confirmation indépendante, après l'ADR 0019 et l'ADR 0021.
- **Horizons 2 et 3 restent fragiles à la marge** : 99.0 % à 1.0x s'effondre à
  9.6 % à 2.0x sur Crash. La distribution quasi-dégénérée de l'ADR 0020 n'était
  pas un artefact de petit échantillon.
- **Crash reste robuste à 5 barres** (94.0 % à 3x), **Boom à 10 barres**
  (87.2 % à 3x).

C'est le résultat le moins spectaculaire et le plus utile : la cible de SIG-02
n'a pas été fixée sur un accident d'échantillonnage.

### 4. Boom 1000 s'effondre à 5 barres, Crash non

À marge 3x, Boom rend 23.4 % à 5 barres contre 94.0 % pour Crash — un facteur 4
sur deux instruments de structure voisine. L'écart de coût (1.063 vs 0.745 bps)
suffit à déplacer Boom du bon côté au mauvais côté de sa propre discontinuité de
distribution.

Conséquence directe : **un horizon unique pour les deux instruments serait un
choix par commodité, pas par mesure.** Crash à 5, Boom à 10.

## Décision

**1. `fetch_candles_paginated` est la route d'ingestion M1.** Le bloc M15 est
retiré de `scripts/fetch_training_data.py`. `crash1000_m15.parquet` reste sur
disque — `diagnose_cost_budget_by_horizon.py` le consomme pour la comparaison
M1/M15 de l'ADR 0020, qui reste valide — mais il n'est plus rafraîchi.

**2. Profondeur d'ingestion : 75000 barres M1 par instrument.** À l'horizon
cible de 5 barres, cela donne ~15000 fenêtres non chevauchantes contre ~1000
auparavant. Le défaut de puissance statistique qui rendait SIG-01 non concluant
(~6 fenêtres indépendantes à 240 barres) est levé.

**3. La table d'horizon de l'ADR 0021 est confirmée, pas remplacée.** Les
valeurs ci-dessus, mesurées sur 75000 barres, remplacent celles de l'ADR 0021
comme référence. Les décisions qu'elles portent sont inchangées.

**4. Cibles SIG-02 : 5 barres sur Crash 1000, 10 barres sur Boom 1000.**
Deux horizons, pas un. L'ADR 0021 le notait déjà ; la mesure sur 75000 barres le
confirme et en donne la cause (§4).

**5. `fetch_candles` reste en place, non déprécié.** Un appel simple à 5000
bougies est le bon outil pour un diagnostic rapide, et la pagination
l'utiliserait de toute façon. Le supprimer casserait des scripts pour rien.

## Conséquences

**Acquis**

- DATA-01 est résolu par du code testé, pas par une sonde manuelle.
- La cible d'horizon de SIG-02 survit à un échantillon 15x plus large et à un
  régime différent.
- Quatre modes de corruption silencieuse de la série sont couverts par des tests
  qui échouent si quelqu'un « simplifie » la boucle de pagination.

**Coûts assumés**

- **Ces ratios restent des PLAFONDS ORACLE.** Ils supposent la direction connue
  d'avance. 94 % de fenêtres tradables signifie que le marché bouge assez pour
  payer le péage, **jamais qu'un signal exploitable existe**. C'est la question
  de SIG-02 et elle reste entièrement ouverte.
- Le coût sous-jacent vient toujours d'une mesure sur compte **démo**, 5 trades,
  une session, multiplicateur x100 (réserve de l'ADR 0021, inchangée).
- 52 jours restent 52 jours : aucun changement de régime saisonnier n'est
  couvert. La profondeur résout la puissance statistique, pas la représentativité
  temporelle.
- Le trou unique de 120 s n'est pas comblé. Une barre manquante sur 75000
  déplace un rendement à 5 barres sur une fenêtre ; l'effet est négligeable mais
  n'est pas nul, et aucune interpolation n'est faite — inventer une barre serait
  pire que d'en manquer une.

## Alternatives écartées

- **Garder le M15 et viser 1 barre M15.** Reviendrait à tripler la détention (15
  min au lieu de 5) par contrainte de format de données plutôt que par mesure —
  l'inverse exact de la démarche de l'ADR 0020.
- **Ingérer jusqu'à épuisement de l'historique Deriv.** Profondeur inconnue, coût
  en requêtes non borné, et 52 jours suffisent déjà largement à la puissance
  statistique requise pour un horizon de 5 barres. La cible est dérivée du
  besoin, pas de ce que l'API veut bien rendre.
- **Arrêter la pagination seulement quand un bloc n'apporte AUCUNE barre
  inédite.** Laisse passer une requête inutile de plus, et surtout confond
  « historique épuisé » avec « chevauchement partiel ». Le test
  `test_overlapping_blocks_are_deduplicated` a effectivement attrapé cette
  version-là.
- **Retenir un horizon unique pour Crash et Boom.** Confortable, non mesuré :
  Boom rend 23.4 % à 5 barres avec marge 3x. Le choisir quand même serait un
  choix par commodité présenté comme un résultat.
