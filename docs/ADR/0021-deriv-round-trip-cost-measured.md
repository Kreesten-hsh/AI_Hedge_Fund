# ADR 0021 — Le coût aller-retour Deriv est mesuré : 0.745 bps sur Crash 1000

- **Statut** : ACCEPTÉ
- **Date** : 2026-08-04
- **Contexte technique** : `scripts/measure_deriv_round_trip_cost.py`
- **Dépend de** : ADR 0018 (seuils dérivés du coût), ADR 0020 (budget par horizon)
- **Résout** : COST-01
- **Corrige** : la formule `2 x taux` proposée en session, jamais publiée dans un ADR

## Contexte

L'ADR 0020 a publié une table de budget de coût par horizon en laissant
délibérément un trou : le coût de transaction Deriv réel n'était pas mesurable
par API depuis l'environnement de développement, et aucune estimation n'a été
câblée. La table indiquait quelle ligne lire une fois le chiffre connu.

Ce chiffre existe maintenant. Il change la cible d'horizon d'un facteur ~40 par
rapport aux 30 bps du `SimulatedBroker` qui structuraient toute la planification.

## Constat

### 1. Toutes les routes automatisables sont fermées

En plus du catalogue d'offres vide déjà documenté à l'ADR 0020
(`clients_country: bj`), trois routes ont été testées et fermées :

| Route | Résultat |
|---|---|
| `api.deriv.com/api-explorer/data/active_symbols.json` | HTTP 403 |
| `deriv.com/trading-specifications` | rendue côté client — **0 occurrence de « crash »** dans le HTML servi |
| MT5 (`scripts/ingest_mt5.py`) | `MT5_SERVER = MetaQuotes-Demo`, serveur générique qui ne porte pas les synthétiques Deriv ; et le paquet `MetaTrader5` est Windows-only alors que l'hôte est Linux |

Deriv ne publie pas de taux de commission par instrument et renvoie
explicitement au ticket de trade. La mesure manuelle n'était donc pas un
raccourci : c'était la seule route.

### 2. Deux produits, deux structures de coût non interchangeables

Distinction absente du backlog initial, qui présumait « spread intégré et
commission de multiplier » sans l'avoir décidé :

| Produit | Structure |
|---|---|
| Deriv Trader — multipliers | commission = notionnel x taux, notionnel = mise x multiplicateur |
| Deriv MT5 — CFD | spread en points + commission par lot |

**Le produit retenu est les multipliers.** Mesurer l'autre aurait donné un
chiffre exact et inutilisable.

### 3. Il n'y a pas de spread à chercher

Aucun spread n'est affiché dans le ticket. Ce n'est pas un défaut d'interface :
les synthétiques Deriv sont cotés sur un **flux à prix unique**, ce que confirme
indépendamment `ticks_history`, qui ne renvoie qu'un prix par horodatage et
jamais bid/ask. Entrée et sortie se font au même spot.

### 4. La commission est prélevée UNE fois par aller-retour, pas deux

C'est le fait que seule une mesure réelle pouvait établir. L'hypothèse de travail
proposée en session était « commission à l'ouverture ET à la fermeture », soit
`coût A/R = 2 x taux`. Elle avait été explicitement signalée comme non vérifiée.

**Elle est réfutée.** Cinq aller-retours immédiats par instrument, compte démo,
mise 10 USD, multiplicateur x100 :

| Instrument | Sens | Commission affichée | Coût A/R mesuré (médiane) | Rapport |
|---|---|---|---|---|
| Crash 1000 | LONG | 0.600 bps (0.06 USD) | **0.745 bps** | 1.24x |
| Boom 1000 | SHORT | 0.900 bps (0.09 USD) | **1.063 bps** | 1.18x |

Un rapport de 1.2x, pas 2.0x. L'erreur aurait été d'un facteur 2 sur le chiffre
qui décide de l'horizon cible.

Le résidu (+0.145 et +0.163 bps) est du même ordre que le pas d'affichage du P&L
(0.01 USD = 0.100 bps sur ce notionnel). Il est conservé dans le chiffre retenu
mais **aucun mécanisme ne lui est attribué** — le prétendre serait lire du bruit
d'affichage comme un signal.

### 5. Le sens des positions est reconstruit, pas supposé

Le sens n'a pas été noté au relevé, et l'inverser déplace chaque coût de deux
fois le mouvement de prix. Il est déterminé par une contrainte physique : le flux
étant à prix unique, aucun spread favorable n'est possible, donc le coût A/R ne
peut pas descendre sous la commission affichée. Un seul sens satisfait cette
borne pour chaque instrument (`infer_direction`, qui lève si zéro ou deux sens
la satisfont plutôt que d'en choisir un).

### 6. La médiane, pas la moyenne

Crash T2 ressort à 3.306 bps contre 0.657-0.801 pour les quatre autres. Sur un
seul relevé, ce trade aurait fixé le coût 4x trop haut. Le protocole à cinq
passages et la médiane existent pour ça.

### 7. Conséquence sur l'horizon : l'espace économique s'ouvre à 5 minutes

Ratio de fenêtres tradables au coût mesuré, Crash 1000, 5000 barres M1, par
marge de sécurité :

| Horizon | marge 1.0x | 2.0x | 3.0x |
|---|---|---|---|
| 1 min | 6.2 % | 5.4 % | 5.0 % |
| 2 min | 98.7 % | 10.0 % | 9.5 % |
| 3 min | 98.2 % | 96.8 % | 13.4 % |
| **5 min** | **98.1 %** | **95.9 %** | **93.3 %** |
| 10 min | 97.0 % | 93.3 % | 89.5 % |
| 15 min | 95.2 % | 90.7 % | 86.1 % |

**L'horizon 1 barre reste réfuté** — 6.2 % de fenêtres même au coût réel. L'ADR
0019 tient, désormais sur une mesure et non sur les 30 bps supposés.

Mais les horizons 2 et 3 barres sont **fragiles à la marge** : le ratio s'effondre
de 98.7 % à 10.0 % entre 1.0x et 2.0x à 2 barres, et entre 2.0x et 3.0x à 3
barres. C'est la distribution quasi-dégénérée identifiée à l'ADR 0020 — les
mouvements courts sont presque tous de la même taille, donc un seuil légèrement
plus haut les élimine d'un bloc. Un horizon dont la viabilité dépend du choix de
marge n'est pas viable.

**Le premier horizon robuste est 5 barres M1** (93.3 % même à 3x). Boom 1000 est
plus serré et n'atteint la même robustesse qu'à **10 barres** (25.0 % à 5 barres
avec marge 3x).

> **REVALIDÉ par l'ADR 0022.** Cette table est mesurée sur 5000 barres M1
> (~3.5 jours, un seul régime). Recalculée sur **75000 barres (52 jours)** après
> l'ingestion paginée, elle tient à ~1 point près : horizon 1 à 5.8 % (contre
> 6.2 %), horizons 2-3 toujours fragiles à la marge, Crash robuste à 5 barres
> (94.0 % à marge 3x), Boom à 10 barres (87.2 %). Les verdicts sont inchangés ;
> ce sont les valeurs de l'ADR 0022 qui font désormais référence.

## Décision

**1. Coût A/R retenu : 0.745 bps sur Crash 1000, 1.063 bps sur Boom 1000.**
COST-01 est résolu. Le trou documenté de l'ADR 0020 est comblé par une mesure.

**2. Cible d'horizon SIG-02 : 5 barres M1 sur Crash 1000**, premier horizon
robuste au choix de marge. Cible cohérente avec l'objectif de décisions
fréquentes — 5 minutes de détention, contre les 4 heures de la fenêtre 60-240
retirée à l'ADR 0020.

**3. Les défauts du `SimulatedBroker` ne changent pas.** C'est un broker
générique, pas un adaptateur Deriv : y câbler 0.745 bps modifierait silencieusement
le coût de toutes les campagnes existantes et de 522 tests. Le chiffre mesuré
passe par CLI :

```
--commission-rate 0.00003725 --slippage-bps 0.0    # Crash 1000, A/R 0.745 bps
--commission-rate 0.00005315 --slippage-bps 0.0    # Boom 1000,  A/R 1.063 bps
```

`commission_rate` porte tout le coût aller-retour, `one_way = round_trip / 2`. Le
slippage est nul parce qu'il est déjà inclus dans la mesure — l'ajouter le
compterait deux fois.

**4. Le relevé est versionné dans `scripts/measure_deriv_round_trip_cost.py`**,
pas recopié dans une constante. Les cinq trades bruts, la reconstruction du sens
et la conversion sont réexécutables et auditables ; une constante nue aurait la
même autorité apparente sans la trace.

**5. DATA-01 repasse en pagination M1 — cette décision RENVERSE l'ADR 0020.**
L'ADR 0020 retenait le M15 sur la base d'un budget de coût équivalent au M1 à
±3 % **à partir de 15 minutes de détention**. La cible mesurée ici est de 5
minutes, qui n'est pas représentable en M15 : la barre minimale y vaut 15
minutes. Conserver le M15 reviendrait à tripler la détention par contrainte de
format de données plutôt que par mesure — l'inverse exact de la démarche de
l'ADR 0020. La pagination M1 donne la même profondeur d'historique (~52 jours en
~15 requêtes) sans ce compromis.

La mesure de départage de l'ADR 0020 reste valide et n'est pas rétractée : elle
rend le M15 réutilisable si une cible ≥15 minutes réapparaît. Seule sa
conclusion opérationnelle change, parce que la prémisse qu'elle servait — un
horizon cible long, dérivé de 30 bps supposés — a été réfutée par la mesure.

## Conséquences

**Acquis**

- Le coût réel est ~40x plus bas que les 30 bps qui structuraient la
  planification. La cible passe de 4 heures à 5 minutes de détention.
- Une hypothèse fausse (`2 x taux`) a été signalée comme non vérifiée AVANT
  d'être utilisée, puis réfutée par la mesure au lieu d'être propagée.
- La fragilité à la marge des horizons 2-3 barres est visible avant
  l'entraînement, pas après une campagne non concluante.

**Coûts assumés**

- **Ces ratios sont des PLAFONDS ORACLE.** Ils supposent la direction connue
  d'avance. 98 % de fenêtres tradables signifie que le marché bouge assez pour
  payer le péage — **jamais qu'un signal exploitable existe**. C'est précisément
  la question de SIG-02, et elle reste entièrement ouverte.
- Mesure sur compte **démo**. L'exécution réelle peut différer (rejets, latence,
  glissement en conditions chargées). À revérifier avant tout passage en réel.
- Cinq trades par instrument sur une seule session. La dispersion observée
  (0.657-3.306 sur Crash) est absorbée par la médiane, pas expliquée.
- Le résidu de ~0.15 bps au-dessus de la commission n'est pas expliqué, seulement
  conservé. Il est du même ordre que le pas d'affichage du P&L.
- Le multiplicateur x100 est le seul testé. La commission étant proportionnelle
  au notionnel, le coût en bps devrait en être indépendant — non vérifié.

## Alternatives écartées

- **Calculer le coût depuis la commission affichée seule.** C'est ce que faisait
  la formule `2 x taux` : arithmétiquement propre et fausse d'un facteur 2. Le
  nombre de prélèvements par aller-retour n'est pas déductible du montant affiché.
- **Chercher le spread plus longtemps dans l'interface.** Il n'y en a pas :
  le flux est à prix unique, ce que `ticks_history` confirmait déjà.
- **Retenir la moyenne des cinq mesures.** L'outlier à 3.306 bps la tirerait à
  1.24 bps sur Crash, soit 66 % au-dessus de la médiane, sur la foi d'un seul
  relevé probablement affecté par la latence de saisie.
- **Viser 2 barres M1**, l'horizon le plus court qui passe à marge 1.0x. Sa
  viabilité dépend entièrement du choix de marge (98.7 % à 1.0x, 10.0 % à 2.0x),
  qui n'est pas dérivé. Choisir la marge après avoir vu le résultat serait du
  gate-adjusting, exactement le défaut corrigé par l'ADR 0018.
- **Câbler 0.745 bps comme défaut du `SimulatedBroker`.** Rendrait Deriv-spécifique
  une infrastructure générique et changerait sous silence le coût de toutes les
  campagnes déjà enregistrées.
