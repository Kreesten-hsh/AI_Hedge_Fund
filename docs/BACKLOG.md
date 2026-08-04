# Backlog Officiel — Aegis Quant OS

Ce document liste les missions structurées de l'OS de trading. Il sert de plan de travail séquentiel.
L'ordre d'implémentation est strictement linéaire (Pipeline Quantitatif).

## Phase 1 : Cœur du Moteur de Simulation

### BT-01 : Modular Backtesting Engine (Backtest Core)
- **Objectif** : Implémenter le moteur de simulation (Boucle séquentielle, Simulated Broker, Performance Metrics).
- **Statut** : COMPLETED

### ST-01 : Strategy Framework
- **Objectif** : Créer l'architecture de stratégies hiérarchiques (Core, Composites).
- **Priorité** : Haute
- **Statut** : COMPLETED

### PM-01 : Portfolio Management
- **Objectif** : Implémenter le Portfolio Manager (Sizing, Rééquilibrage).
- **Priorité** : Haute
- **Statut** : COMPLETED (Note : Le Portfolio Manager réutilise le `GlobalRiskManager` événementiel via adaptateur au lieu d'en recréer un).

### RM-01 : Risk Management
- **Objectif** : RM-01 : fonctionnalité couverte par la réunification PM-01 (GlobalRiskAdapter). Pas de mission dédiée nécessaire.
- **Priorité** : Haute
- **Statut** : COMPLETED

## Phase 2 : Validation Scientifique & Machine Learning

### VA-01 : Institutional Validation Framework
- **Objectif** : Construire un laboratoire de validation (Walk-Forward, Hold-Out, Monte Carlo, Benchmark) pour tester la robustesse économique des stratégies avant le ML.
- **Priorité** : Critique
- **Statut** : COMPLETED

### QL-01 : Qlib Adapter
- **Objectif** : Intégrer Microsoft Qlib pour un backtesting factoriel à ultra-haute vitesse.
- **Priorité** : Moyenne
- **Statut** : COMPLETED

### ML-01 : Machine Learning / AI Decision Engine
- **Objectif** : Ajouter les modèles ML (LightGBM, Pytorch) et réintégrer l'AI Council (LLM) dans le pipeline de stratégie.
- **Statut** : COMPLETED

### VA-02 : Barème monotone et seuils dérivés du coût
- **Objectif** : Rendre le `ScoringEngine` strictement monotone en PnL net réel, et dériver tout seuil d'entrée du coût de transaction réel au lieu de le choisir.
- **Priorité** : Critique
- **Statut** : COMPLETED (ADR 0017, ADR 0018)
- **Note** : Prérequis de toute conclusion scientifique en aval. L'ancien barème notait 30/100 une stratégie à -37 % et 0/100 une stratégie à -1 % ; l'ancien seuil valait ~15x moins que le péage qu'il déclenchait.

### SIG-01 : Horizon 1 barre sur Crash 1000 — REJETÉ
- **Objectif** : Établir si un edge net de frais existe sur `forward_return_1`.
- **Priorité** : Critique
- **Statut** : REJETÉ, hypothèse abandonnée (ADR 0019)
- **Preuve** : `.validation_registry/val_20260803_205954_MLStrategy_score_0.json` — 0 trade, score 0/100. Le marché lui-même ne franchit jamais 30 bps en une barre (0/1499 fenêtres) ; mouvement médian 0.61 bps, soit un tick. Un oracle parfait y perdrait de l'argent. Cause = horizon, pas modèle.

### DATA-01 : Historique Crash 1000 suffisant pour valider un horizon long
- **Objectif** : Ingérer un historique nettement plus long que les 5000 barres M1 actuelles, spécifiquement pour Crash 1000.
- **Priorité** : Critique — bloque SIG-02
- **Statut** : COMPLETED (ADR 0022) — route **pagination M1** retenue (ADR 0021, renverse l'ADR 0020), implémentée et ingérée.
- **Livré** : `DerivHistoricalData.fetch_candles_paginated` recule `end` d'exactement une granularité sous la plus ancienne barre reçue, déduplique par epoch, s'arrête quand une page n'apporte plus de barre inédite, et tronque par la TÊTE (les barres les plus récentes sont conservées). 14 tests dans `tests/providers/deriv/test_historical_pagination.py` épinglent le contrat, connexion doublée, zéro réseau. `page_size > 5000` est refusé : le serveur renvoie 5000 en silence, ce qui décalerait tous les curseurs.
- **Jeux ingérés** : `crash1000.parquet` et `boom1000.parquet`, **75000 barres M1 chacun, 52 jours**, 0 doublon, un seul trou de 120 s sur 75000 barres, ~15 requêtes par instrument. Contre 5000 barres / 3.5 jours auparavant.
- **Puissance statistique obtenue** : à l'horizon cible de 5 barres, ~15000 fenêtres non chevauchantes contre ~1000 avant. Le défaut qui rendait SIG-01 non concluant (~6 fenêtres à 240 barres) est levé.
- **Table de l'ADR 0021 revérifiée sur les 75000 barres** — les verdicts tiennent à ~1 point près, sur 15x plus de données et un régime de marché différent :

  | Horizon | Crash 1.0x / 2.0x / 3.0x | Boom 1.0x / 2.0x / 3.0x |
  |---|---|---|
  | 1 | 5.8 % / 5.1 % / 4.9 % | 5.4 % / 5.1 % / 4.7 % |
  | 2 | 99.0 % / 9.6 % / 9.1 % | 96.3 % / 9.5 % / 8.9 % |
  | 3 | 98.6 % / 97.2 % / 12.8 % | 98.3 % / 13.4 % / 12.5 % |
  | **5** | **98.0 % / 96.1 % / 94.0 %** | 97.4 % / 94.7 % / 23.4 % |
  | **10** | 97.2 % / 94.2 % / 91.5 % | **96.0 % / 91.6 % / 87.2 %** |
  | 15 | 96.8 % / 93.3 % / 89.7 % | 94.8 % / 89.2 % / 84.4 % |

  Horizon 1 reste réfuté. 2 et 3 barres restent fragiles à la marge. Crash reste robuste à 5 barres, Boom à 10.
- **Raison** : à un horizon de 240 barres, 1500 barres de test ne donnent que ~6 fenêtres indépendantes. Re-tester SIG-02 sur ce jeu reproduirait le même défaut de puissance statistique : un résultat, quel qu'il soit, ne serait pas concluant.
- **Contrainte technique levée** : `DerivHistoricalData.fetch_candles` plafonne à **5000 bougies par requête** — plafond serveur, pas défaut d'appel. Deux routes vérifiées ouvertes :
  1. **Pagination** — reculer `end` dans le temps puis concaténer et dédupliquer. **← route retenue, implémentée, ingérée.**
  2. **Granularité plus grossière** — sous le même plafond, le M15 couvre ~52 jours contre ~3.5 jours en M1 (`data/market_data/crash1000_m15.parquet`). Écartée : voir ci-dessous.
- **Pourquoi le M15 est écarté après avoir été retenu** : l'ADR 0020 avait choisi le M15 sur la base d'un budget de coût équivalent à ±3 % **à partir de 15 min de détention**. La cible mesurée est désormais **5 barres M1, soit 5 minutes** (ADR 0021), qui n'est pas représentable en M15 — la barre minimale y vaut 15 min. Le M15 imposerait donc de tripler la détention par contrainte de format de données, pas par mesure. La pagination donne la même profondeur d'historique sans ce compromis (~52 jours de M1 = ~15 requêtes).
- **Mesure de départage conservée** (ADR 0020) : à détention égale et **sur période commune**, le budget de coût M15 égale le M1 à ±3 % de 15 min à 8 h. Ce résultat reste valide et rend le M15 réutilisable si une cible ≥15 min réapparaît. Attention : comparées sur leurs étendues natives, les mêmes séries montrent −23 % à 8 h — un effet de régime, pas d'agrégation.
- **Réserve devenue sans objet pour la cible actuelle** : la question « des features M15 voient-elles encore les spikes ? » ne se pose plus en pagination M1. Elle redevient ouverte si le M15 revient.

### COST-01 : Mesurer le coût de transaction Deriv réel
- **Objectif** : Obtenir le coût aller-retour réel sur Crash 1000 et Boom 1000.
- **Priorité** : Critique — prérequis de SIG-02
- **Statut** : COMPLETED (ADR 0021)
- **Résultat** : **0.745 bps A/R sur Crash 1000**, **1.063 bps sur Boom 1000**. Soit ~40x moins que les 30 bps du `SimulatedBroker` qui structuraient la planification.
- **Produit retenu** : Deriv Trader **multipliers** (commission = notionnel × taux). Le CFD MT5 (spread en points + commission par lot) est un produit distinct aux coûts non interchangeables — mesurer le mauvais aurait donné un chiffre exact et inutilisable.
- **Fait que seule la mesure pouvait établir** : la commission est prélevée **une seule fois** par aller-retour (rapport mesuré 1.18-1.24x la commission affichée), pas deux. La formule `2 × taux` proposée en session est **réfutée** — elle aurait faussé d'un facteur 2 le chiffre qui décide de l'horizon.
- **Pas de spread** : les synthétiques Deriv sont cotés sur un flux à prix unique, confirmé indépendamment par `ticks_history` qui ne renvoie jamais bid/ask. Rien à chercher dans l'interface.
- **Relevé versionné** : `scripts/measure_deriv_round_trip_cost.py` porte les 5 aller-retours bruts par instrument, la reconstruction du sens par contrainte physique et la conversion. Réexécutable.
- **Usage en CLI** — les défauts du `SimulatedBroker` restent inchangés (broker générique, pas adaptateur Deriv ; 522 tests en dépendent) :
  ```
  --commission-rate 0.00003725 --slippage-bps 0.0    # Crash 1000, A/R 0.745 bps
  --commission-rate 0.00005315 --slippage-bps 0.0    # Boom 1000,  A/R 1.063 bps
  ```
  Slippage nul : il est déjà inclus dans la mesure, l'ajouter le compterait deux fois.
- **Routes automatisables, toutes vérifiées fermées** : API WebSocket (`active_symbols` = 0 symbole, `clients_country: bj`) ; REST public en HTTP 403 ; `deriv.com/trading-specifications` rendue côté client (0 occurrence de « crash » dans le HTML servi) ; MT5 bloqué deux fois — `MT5_SERVER = MetaQuotes-Demo` ne porte pas les synthétiques Deriv, et le paquet `MetaTrader5` est Windows-only alors que l'hôte est Linux. Cette dernière route redevient viable sur un compte Deriv-MT5 depuis Windows.
- **Réserve** : mesure sur compte **démo**, 5 trades, une session, multiplicateur x100 seulement. À revérifier avant tout passage en réel.

### COST-02 : Automatiser la mesure du coût, et séparer le slippage du péage
- **Objectif** : rendre la mesure de COST-01 rejouable, et décomposer le coût agrégé en **péage d'exécution + slippage**, ce que le relevé manuel ne pouvait pas faire.
- **Priorité** : Haute — lève la réserve de COST-01
- **Statut** : IMPLÉMENTÉ, **non exécuté en live** (token bloquant, voir ci-dessous)
- **Livré** : `scripts/measure_deriv_live_round_trip.py` — authentifie, ouvre une position Multipliers, la ferme après N secondes, écrit `data/measurements/deriv_round_trips.csv`, résume en bps. 45 tests dans `tests/scripts/test_deriv_live_round_trip.py`, connexion doublée, zéro réseau, **99 % de couverture** (la ligne restante est `if __name__ == "__main__"`). `mypy --strict` et `ruff` propres.
- **Ce que la mesure manuelle ne pouvait pas produire** : le spot au moment de la DÉCISION n'était pas noté, donc les 0.745 / 1.063 bps de l'ADR 0021 sont un **péage sur spots exécutés**, slippage exclu. Le script relève le spot juste avant l'ordre et le contrat renvoie le spot obtenu : l'écart est isolé et signé selon le sens (défavorable = positif). Un chiffre live supérieur à l'ADR 0021 ne le contredit donc pas — il rend visible le second terme.
- **Frontière architecturale assumée** : le script route des ordres **sans passer par le `RiskEngine`**. Il vit dans `scripts/`, hors de `src/aegis_trade/`, précisément pour qu'aucun import depuis le paquet ne puisse l'atteindre — c'est un instrument de mesure, jamais un composant d'exécution. Les garde-fous qui remplacent le risk check absent sont durs et non configurables en CLI : compte `is_virtual` obligatoire (refus à l'authentification, avant tout ordre), `MAX_STAKE_USD = 50`, `MAX_TRADES_PER_RUN = 20`, `MAX_HOLD_SECONDS = 60`, et fermeture tentée systématiquement si une exception survient entre l'achat et la vente. Chacun a son test.
- **Effet de bord utile** : `tests/conftest.py` met désormais la racine du dépôt dans `sys.path`. Sans ça, `scripts/` n'était importable par aucun test — 25 scripts, dont plusieurs qui touchent des données de production, étaient intestables par construction.
- **Limite du CSV comme preuve** : `/data/` est gitignoré, donc `deriv_round_trips.csv` reste local. Il sert d'accumulation brute entre sessions, pas de preuve versionnée. Comme pour l'ADR 0021, les valeurs retenues devront être **transcrites dans l'ADR** pour exister hors de la machine — sinon la mesure est rejouable mais son résultat, lui, disparaît.
- **BLOCAGE** : `DERIV_API_TOKEN` dans `.env` fait 68 caractères et commence par `pat`. Un token Deriv fait ~15 caractères et commence par `a1-`. La valeur présente ressemble à un jeton d'une autre plateforme. Aucun run live n'a été tenté — et aucun chiffre live n'est reporté ici. À régénérer sur le compte **démo** (Paramètres > Jetons API, portées `read` + `trade`).
- **Reste à faire une fois le token valide** : exécuter 5 A/R sur CRASH1000 puis sur BOOM1000 (`--stake 10 --multiplier 100 --hold 5`), comparer la médiane d'exécution aux 0.745 / 1.063 bps, et reporter le **coût tout compris** dans l'ADR 0021 si le slippage est non négligeable. Profiter du token pour re-tester `active_symbols` / `contracts_for` **authentifié** : le verdict « routes fermées » de l'ADR 0020/0021 repose sur des sondes non authentifiées et peut être périmé.

### SIG-02 : Redéfinition de l'horizon cible
- **Objectif** : Mesurer la faisabilité économique AVANT d'entraîner, puis re-tester l'hypothèse « signal exploitable » à un horizon où l'espace économique existe.
- **Priorité** : Critique — bloque la Phase 4
- **Statut** : PLANNED
- **Prérequis** : DATA-01 **résolu** (75000 barres M1, 52 jours). COST-01 **résolu** (ADR 0021).
- **Cible** : **5 barres M1 sur Crash 1000**, **10 barres M1 sur Boom 1000** (ADR 0021, revalidé ADR 0022 sur 75000 barres). Deux horizons, pas un : à marge 3x, Boom rend **23.4 %** de fenêtres à 5 barres contre **94.0 %** pour Crash — l'écart de coût (1.063 vs 0.745 bps) suffit à faire basculer Boom du mauvais côté de sa propre discontinuité de distribution. Un horizon unique serait un choix par commodité, pas par mesure. 5 minutes de détention sur Crash — cohérent avec l'objectif de décisions fréquentes, contre les 4 heures de la fenêtre 60-240 retirée à l'ADR 0020.
- **Horizons écartés et pourquoi** : 1 barre reste **réfuté** (5.8 % de fenêtres sur 75000 barres — troisième confirmation indépendante après l'ADR 0019 et l'ADR 0021). 2 et 3 barres sont **fragiles à la marge** : le ratio s'effondre de 99.0 % à 9.6 % entre marge 1.0x et 2.0x à 2 barres. Un horizon dont la viabilité dépend d'un paramètre non dérivé n'est pas viable — le retenir serait du gate-adjusting (ADR 0018).
- **Outil** : `aegis_trade.domain.tradability` (`tradable_window_ratio`, `is_horizon_tradable`, `max_viable_round_trip_cost`) + `scripts/diagnose_cost_budget_by_horizon.py` et `scripts/diagnose_horizon_vs_cost.py`. Le gate passe AVANT tout entraînement : le budget est un plafond atteignable par un oracle, donc un budget sous le coût réel réfute l'horizon sans dépenser de temps de calcul.
- **Déblocage technique fait** : l'horizon du label n'est plus câblé. `DatasetBuilder(horizon=N)` étiquette à `forward_return_N` (nom dérivé de l'horizon pour que deux campagnes d'horizons différents ne se confondent pas dans le registre), et `scripts/train_qlib_model.py --horizon N` l'expose. Horizon < 1 refusé (0 = fuite, négatif = passé). La fuite de cible reste couverte : `model_factory._feature_matrix` exclut `dataset.target_col` par son nom exact, pas seulement la constante.
- **Reste à trancher côté stratégie** : **« horizon du label » ≠ « durée de détention »**. `MLStrategy` déclare une exposition cible à chaque barre ; avec `horizon=15`, le modèle prédit un rendement à 15 barres mais la détention effective est dictée par la persistance du signal. Le seuil d'entrée reste cohérent (rendement attendu vs coût A/R), mais la sortie n'est pas alignée sur l'horizon. À décider dans SIG-02, pas par défaut.

### KRO-01 : Kronos-mini (Phase 4) — SUSPENDU
- **Objectif** : Substituer un modèle de séquence à LightGBM.
- **Statut** : SUSPENDU jusqu'à SIG-02
- **Raison** : sur `forward_return_1`, un meilleur modèle prédirait plus précisément une grandeur trop petite pour être tradée. Gain de précision réel, gain économique nul (ADR 0019).

## Phase 3 : Production & Temps Réel

### EX-01 : Execution Engine (Event-Driven)
- **Objectif** : Moteur événementiel (EventBus) complet pour router les ordres (via broker, e.g. vn.py/ccxt) en conditions réelles ou Paper Trading.
- **Priorité** : Haute
- **Statut** : COMPLETED

### LIVE-01 / LIVE-02 : Production / Dashboards
- **Objectif** : Lancement en direct, Dashboards de supervision (FastAPI/React), et automatisation complète.
- **Priorité** : Haute
- **Statut** : PLANNED

## Dette technique identifiée

### DEBT-01 : `pytest --cov` inutilisable sur tout module important pandas
- **Symptôme** : `ImportError: cannot load module more than once per process` à la collection. Reproductible en trois lignes, sans code du projet :
  ```
  printf 'import pandas\ndef test_x(): pass\n' > t.py
  pytest t.py --cov=aegis_trade.domain.tradability   # ECHEC
  pytest t.py                                        # OK
  ```
- **Cause** : numpy ≥ 2.4 refuse de charger ses extensions C pendant qu'un traceur est actif. `pytest-cov` démarre coverage dans `pytest_load_initial_conftests`, donc **avant** tout `conftest.py` — un pré-import dans `tests/conftest.py` arrive trop tard. Versions : numpy 2.4.6, coverage 7.15.2, pytest-cov 7.1.0.
- **Contournement vérifié** : plugin chargé par `-p`, importé avant le traceur.
  ```
  printf 'import pandas  # noqa: F401\n' > /tmp/preload_pandas.py
  PYTHONPATH=/tmp pytest <tests> -p preload_pandas --cov=<module>
  ```
- **Impact** : le gate coverage de CLAUDE.md n'est pas atteignable par la commande évidente sur la moitié du repo. Le contournement fonctionne mais n'est pas versionné, donc invisible pour quiconque relance les gates.
- **À trancher** : versionner le plugin de pré-import dans le repo et l'ajouter à `addopts`, ou épingler une version de numpy/coverage compatible. Ni l'un ni l'autre n'est fait ici — hors périmètre DATA-01.

### DEBT-02 : `DerivHistoricalData.fetch_candles` n'a aucun test
- **Constat** : découvert en mesurant la couverture pour DATA-01. Les 18 lignes non couvertes du module (78 % global) sont **exclusivement** `fetch_candles` (90-119) et son wrapper `fetch_candles_sync` (128). Le code paginé ajouté par DATA-01 est à 100 %.
- **Antériorité** : `grep -rl fetch_candles tests/` ne renvoie que le fichier de pagination. La méthode n'a jamais été testée — ce n'est pas une régression de DATA-01.
- **Pourquoi ça compte** : `fetch_candles` reste la route d'un diagnostic rapide à 5000 bougies (ADR 0022, décision 5), et `_candles_to_records` est désormais partagé avec le chemin paginé. Une régression sur le parsing casserait les deux.
- **Coût estimé** : faible — la connexion doublée et les fixtures existent déjà dans `tests/providers/deriv/test_historical_pagination.py`.

