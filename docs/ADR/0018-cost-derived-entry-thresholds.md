# ADR 0018 — Le seuil d'entrée se dérive du coût de transaction, il ne se choisit pas

- **Statut** : ACCEPTÉ
- **Date** : 2026-08-03
- **Contexte technique** : `src/aegis_trade/domain/costs.py`,
  `src/aegis_trade/application/strategy/ml_strategy.py`,
  `src/aegis_trade/infrastructure/brokers/simulated_broker.py`

## Contexte

`MLStrategy` convertit un rendement attendu prédit par le modèle en exposition
cible. La conversion repose sur une zone morte : au-dessus de `buy_threshold` on
achète, en dessous de `sell_threshold` on vend, entre les deux on reste plat.

Ces seuils valaient `±0.0002` (2 bps) par défaut. Le broker de validation
appliquait `commission_rate=0.001` et `slippage_bps=5.0`, soit **15 bps par
jambe et 30 bps sur un aller-retour**. Le seuil d'entrée était donc **~15x sous
le coût du trade qu'il déclenchait**.

Conséquence mesurée sur Crash 1000, segment de test hors-échantillon
(`val_20260803_063600`) : 325 trades, rendement **-37.11 %**. Décomposition
approximative sur 100 000 de capital initial : ~24.7k de commissions et ~12.3k
de slippage. Le même jeu de signaux, simulé **sans frais**, rapporte +86.82 —
soit un Sharpe de -0.0014, un edge nul et non négatif.

Le modèle ne se trompait donc pas particulièrement : la perte était un coût de
friction, pas une erreur de prédiction. Toute recherche de signal menée avec un
seuil sous le coût est vaine par construction, quelle que soit la qualité du
modèle en amont. Aucune quantité de features supplémentaires ne peut corriger
cela.

Un second défaut aggravait le premier : le seuil (dans la stratégie) et le coût
(dans le broker) étaient deux constantes indépendantes, recopiées à la main de
part et d'autre. Rien n'empêchait leur divergence silencieuse, et une divergence
rend le backtest non concluant plutôt que faux — la pire des deux situations,
parce qu'elle ne se voit pas.

## Décision

**1. Le coût de transaction devient un concept de domaine explicite.**

`TransactionCostModel` (`domain/costs.py`), dataclass gelée sans dépendance
broker, expose `one_way_cost`, `round_trip_cost` et
`breakeven_return(safety_margin)`.

Le coût pertinent pour une décision d'entrée est celui de l'**aller-retour** :
ouvrir une position engage mécaniquement de la fermer. Ne budgéter que la jambe
d'entrée sous-estime le péage d'un facteur 2 et fait paraître rentables des
signaux qui ne le sont pas.

**2. Le seuil de rentabilité est le plancher de tout seuil légitime.**

`MLStrategy.from_cost_model(predictor, cost_model, safety_margin)` dérive
`buy_threshold = +breakeven`, `sell_threshold = -breakeven`, et
`strength_scale = 2 x breakeven` (la conviction sature quand le mouvement
anticipé vaut deux allers-retours — le dimensionnement est rattaché à la même
échelle économique que la décision d'entrer).

`safety_margin < 1.0` lève une `ValueError` : viser un trade dont le gain espéré
ne couvre pas son propre péage n'est pas un compromis paramétrable, c'est une
espérance négative garantie.

**3. Les seuils deviennent obligatoires dans le constructeur.**

`buy_threshold` et `sell_threshold` n'ont plus de valeur par défaut. Un défaut
arbitraire est précisément ce qui a permis de lancer 325 trades perdants sans
qu'aucun appelant ait choisi ce compromis. Les seuils explicites restent
disponibles pour les tests sans friction ; `from_cost_model` est le chemin
d'exécution.

**4. Source de vérité unique entre stratégie et exécution.**

`SimulatedBroker.cost_model` expose le coût réellement prélevé sous forme de
concept de domaine. `scripts/train_qlib_model.py` construit une fabrique de
broker, en lit le `cost_model`, et en dérive les seuils — la stratégie budgète
exactement le péage que la simulation appliquera.

La signature `broker_factory` des validateurs passe de `Type[IBroker]` à
`Callable[[], IBroker]`. Tous les sites d'appel l'invoquaient déjà comme une
fabrique sans argument ; le type était simplement trop étroit et interdisait de
passer un broker préconfiguré en coûts.

## Conséquences

**Acquis**

- Un seuil sous le coût n'est plus atteignable par défaut ou par omission.
- Seuil et coût ne peuvent plus diverger : un seul chiffre, lu depuis le broker.
- `--commission-rate`, `--slippage-bps` et `--safety-margin` deviennent les
  paramètres de recherche du script d'entraînement, à la place de
  `--buy-threshold` / `--sell-threshold`. La recherche porte sur des grandeurs
  économiques, pas sur des nombres libres.
- Test économique de bout en bout : un mouvement au seuil de rentabilité produit
  un PnL net non négatif après commissions réelles du broker ; l'ancien seuil de
  2 bps produit un PnL net négatif.

**Coûts assumés**

- **Un seuil réaliste réduit fortement le nombre de trades, jusqu'à zéro.** Sur
  du M1 synthétique, un modèle prédisant rarement plus de 30 bps de mouvement
  générera peu ou pas de signaux. Un échantillon sous 30 trades fait échouer
  Monte-Carlo comme non concluant. **C'est le comportement voulu** : zéro trade
  au-dessus du coût est un résultat, et il signifie que l'hypothèse « signal
  exploitable sur cette configuration de features » est fausse à cet horizon.
  Rabaisser le seuil pour retrouver des trades serait du gate-adjusting.
- Les coûts réels de Deriv sur indices synthétiques ne sont pas ceux de
  `SimulatedBroker` (pas de commission explicite ; le coût est dans le spread).
  Les 30 bps utilisés ici sont ceux du broker simulé, pas une mesure Deriv. Le
  câblage sur les spreads réels est un travail distinct (backlog).
- `safety_margin` reste un choix non dérivé. Par défaut 1.0 (rentabilité stricte),
  ce qui laisse une espérance nulle avant erreur de prédiction. Le calibrer
  correctement exige une distribution d'erreur du modèle mesurée, qui n'existe
  pas encore.

## Alternatives écartées

- **Garder les seuils libres et corriger seulement la valeur par défaut.** Laisse
  le prochain appelant reproduire le même défaut, et laisse seuil et coût
  divergents.
- **Rendre le seuil paramètre d'optimisation du modèle.** Optimiser un seuil sur
  le segment de test après avoir lu le résultat est du p-hacking. Le seuil est
  une contrainte économique déduite, pas un degré de liberté.
- **Placer le coût dans le broker uniquement.** La stratégie doit connaître le
  coût pour décider ; le laisser dans l'infrastructure obligerait la stratégie à
  dépendre d'un adaptateur, en violation de la frontière domaine/infrastructure.
