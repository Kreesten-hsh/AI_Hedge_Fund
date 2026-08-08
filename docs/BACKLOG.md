# Backlog Officiel — Aegis Quant OS

Ce document liste les missions structurées de l'OS de trading. Il sert de plan de travail séquentiel.
L'ordre d'implémentation est strictement linéaire (Pipeline Quantitatif).

## TRAJECTOIRE COURANTE — mise à jour le 2026-08-06

```
GOLD-01 (M1 Tech: REJETÉ) ──► GOLD-MACRO (DFII10 + OpenBB FRED) ──► Audit Council (8 agents) ──► Pivot Fréquence (H4/D1)
```

1. **GOLD-01 (Clôturé & Rejeté - ADR 0025)** : Coût A/R mesuré à 1.859 bps. Gate économique `domain/tradability` validé dès H5 (>75.6% tradable), mais 0/25 indicateurs techniques significatifs de H5 à H120. Réfute définitivement l'hypothèse des indicateurs techniques simples sur M1.
2. **GOLD-MACRO (Clôturé & Rejeté - ADR 0027)** : Ingestion et alignement des Taux Réels 10 ans FRED (`DFII10`) et DXY sur 75k barres M1 Gold. 0/6 features macro significatives de H5 à H240 ($|t| \le 1.93$). Les séries quotidiennes macro ne prédisent pas le bruit M1.
3. **Audit du Council à 8 agents (Clôturé & Rejeté - ADR 0028)** : Audit quantitatif du Council déterministe avec veto strict et comparaison côte-à-côte (Run 1 Purifié: 36.71% d'exposition, net -1.69 bps ; Run 2 Sparse: 51.95% d'exposition, net -1.81 bps). Le mouvement brut moyen capté (+0.16 bps) est 11x inférieur aux allers-retours (1.859 bps). Réfuté sur M1.
4. **Pivot Fréquence & Régime d'Horizon H4/D1 (En cours — Priorité 1)** : Évaluation systématique du changement de régime vers des horizons temporels plus bas (H4 et Quotidien D1). Mesure des mouvements moyens et de la rentabilité nette lorsque les allers-retours sont amortis sur des tendances macro à forte conviction.

Ce qui reste **gelé** jusqu'à cette évaluation : déduplication `Verdict → ordre`, déduplication `DatasetBuilder`, pureté du domaine
(`domain/council.py:5`). (Note: La coexistence des deux Councils a été réglée par la migration d'AiDecisionEngine vers MultiAgentCouncil et docs/LEGACY_COUNCIL_MIGRATION.md). Gelé ≠ abandonné : **Lot 3 complet reste prérequis obligatoire avant AI-07b
(argent réel).**

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
- **Statut** : **RÉSOLU** — porté sur la nouvelle API Deriv, exécuté en live sur compte démo, résultats transcrits dans l'ADR 0021
- **Livré** : `scripts/measure_deriv_live_round_trip.py` — authentifie, ouvre une position Multipliers, la ferme après N secondes, écrit `data/measurements/deriv_round_trips.csv`, résume en bps. 80 tests dans `tests/scripts/test_deriv_live_round_trip.py`, **les deux couches doublées** (préambule REST par `httpx.MockTransport`, WebSocket par une connexion doublée), zéro réseau, **99 % de couverture** (la ligne restante est `if __name__ == "__main__"`). `mypy --strict` et `ruff` propres.
- **Portage sur la nouvelle API Deriv** : l'ancienne authentification WebSocket v3 (`{"authorize": token}` in-band sur `wss://ws.derivws.com/websockets/v3`) **n'existe plus** — aucun `authorize_request.schema.json` dans le spec officiel, et l'ancien point d'entrée rejette un Personal Access Token avec `InvalidToken`. Séquence actuelle, vérifiée contre `rest-api-openapi.json` publié par Deriv :
  ```
  GET  /trading/v1/options/accounts            (Bearer PAT + en-tête Deriv-App-ID)
  POST /trading/v1/options/accounts/{id}/otp   -> data.url
  websockets.connect(data.url)                 l'OTP est déjà dans la query
  ```
  Le jeton ne transite **plus jamais** par le WebSocket. Trois ruptures silencieuses qu'un portage naïf aurait manquées : `buy.parameters.symbol` devient **`underlying_symbol`** (se sérialise sans erreur, se fait refuser côté serveur) ; `authorize` disparaît entièrement ; **`is_virtual` est remplacé par `account_type: "demo" | "real"`**, ce qui déplace le garde-fou démo de l'authentification vers la sélection de compte. L'enveloppe de messages v3 (`msg_type`, `echo_req`, `req_id`), elle, est conservée — seule la couche d'authentification change.
- **Le garde-fou démo est désormais double, et le second fait foi** : `account_type == "demo"` est déclaratif et lu avant l'OTP ; le chemin de l'URL renvoyée (`/ws/demo` contre `/ws/real`) est ce que Deriv ouvre réellement. Les deux sont vérifiés, le refus tombe **pendant le préambule REST**, donc aucun WebSocket n'est même ouvert. Sans `--account-id`, un seul compte démo actif est accepté : plusieurs candidats sans consigne serait un choix arbitraire sur un compte qui passe des ordres.
- **Secret supplémentaire à protéger** : l'URL renvoyée par l'OTP porte un identifiant de connexion dans sa query. `redact_otp()` la caviarde systématiquement avant journalisation, et un test vérifie qu'aucun log de session ne contient ni l'OTP ni le PAT.
- **Ce que la mesure manuelle ne pouvait pas produire** : le spot au moment de la DÉCISION n'était pas noté, donc les 0.745 / 1.063 bps de l'ADR 0021 sont un **péage sur spots exécutés**, slippage exclu. Le script relève le spot juste avant l'ordre et le contrat renvoie le spot obtenu : l'écart est isolé et signé selon le sens (défavorable = positif). Un chiffre live supérieur à l'ADR 0021 ne le contredit donc pas — il rend visible le second terme.
- **Frontière architecturale assumée** : le script route des ordres **sans passer par le `RiskEngine`**. Il vit dans `scripts/`, hors de `src/aegis_trade/`, précisément pour qu'aucun import depuis le paquet ne puisse l'atteindre — c'est un instrument de mesure, jamais un composant d'exécution. Les garde-fous qui remplacent le risk check absent sont durs et non configurables en CLI : compte `account_type == "demo"` **et** URL sur `/ws/demo` obligatoires (refus pendant le préambule REST, avant toute ouverture de WebSocket), `MAX_STAKE_USD = 50`, `MAX_TRADES_PER_RUN = 20`, `MAX_HOLD_SECONDS = 60`, et fermeture tentée systématiquement si une exception survient entre l'achat et la vente. Chacun a son test.
- **Effet de bord utile** : `tests/conftest.py` met désormais la racine du dépôt dans `sys.path`. Sans ça, `scripts/` n'était importable par aucun test — 25 scripts, dont plusieurs qui touchent des données de production, étaient intestables par construction.
- **Limite du CSV comme preuve** : `/data/` est gitignoré, donc `deriv_round_trips.csv` reste local. Il sert d'accumulation brute entre sessions, pas de preuve versionnée. Comme pour l'ADR 0021, les valeurs retenues devront être **transcrites dans l'ADR** pour exister hors de la machine — sinon la mesure est rejouable mais son résultat, lui, disparaît.
- **CORRECTION d'une conclusion précédemment portée ici** : ce backlog affirmait que `DERIV_API_TOKEN` (68 caractères, préfixe `pat`) « ressemblait à un jeton d'une autre plateforme » parce qu'un token Deriv « fait ~15 caractères et commence par `a1-` ». **C'est faux.** Les Personal Access Tokens émis par `home.deriv.com/dashboard/profile/api-tokens` sont désormais la méthode d'authentification recommandée et n'ont plus ce format. Le jeton présent est valide : sondé sur la nouvelle API, il obtient `Deriv-App-ID header is required for PAT tokens` et non une erreur de jeton invalide. Le format d'un secret n'est pas une preuve de sa provenance — ne plus rejeter un jeton sur son préfixe.
- **BLOCAGE LEVÉ** : `DERIV_APP_ID` est renseigné dans `.env`. Le préambule REST a été sondé **en lecture seule** (aucun ordre) et répond : un unique compte, `DOT93925868`, `account_type: "demo"`, `status: "active"`, USD. Un seul compte démo actif signifie que `--account-id` est inutile. Les app id hérités testés à vide restent invalides (`1089`, `36544`, `16929` → `Invalid application`) — seul un id enregistré sur `home.deriv.com/dashboard` fonctionne. Le CLI sort toujours 2 si la clé disparaît.
- **Inadéquation trouvée par la sonde, pas par les tests** : la vraie API renvoie le solde en **chaîne** (`'9999.25'`), pas en nombre. `_optional_float` n'acceptait que `int`/`float` et aurait donc journalisé `None` sur une réponse pourtant complète. Corrigé (avec garde explicite sur `bool`, sous-type d'`int` en Python, qui serait devenu `1.0`), deux tests ajoutés. Les doubles ne valident que le contrat qu'on leur a écrit — un aller-retour lecture seule contre le vrai service reste nécessaire avant tout run qui engage de l'argent.
- **RÉSULTAT LIVE (2026-08-04, compte démo `DOT93925868`, 10 A/R au total)** : Crash 0.652 bps d'exécution / +0.002 bps de slippage / **0.652 tout compris** ; Boom 0.961 / −0.011 / **0.951**. Les deux sont **sous** les chiffres manuels de l'ADR 0021 (−12 %, −11 %) avec une dispersion bien plus serrée — la latence de saisie manuelle gonflait le relevé. **Le slippage est négligeable** : ≤ 0.011 bps, ~1 % du péage. Le second terme que COST-02 devait révéler existe mais ne pèse rien à 5 s de détention. **Les 0.745 / 1.063 restent retenus** (les plus conservateurs) : basculer sur le chiffre plus bas serait choisir la mesure qui arrange. Transcrit dans l'ADR 0021, section Décision 1.
- **Le verdict « routes fermées » des ADR 0020/0021 est PÉRIMÉ** : authentifié sur la nouvelle API, `active_symbols` (78 symboles), `contracts_for` sur les deux instruments et `ticks_history` (`granularity: 60`, 500 bougies M1) répondent tous. Le schéma a changé en même temps que l'authentification — `product_type` et `currency` sont désormais **refusés** (`InputValidationFailed: Properties not allowed`), et une sonde qui garde les champs v3 reçoit une erreur qui se lit à tort comme une route fermée. C'est exactement l'erreur commise. Corrigé dans l'ADR 0021, constat 1. **Conséquence ouverte, non traitée ici** : `ticks_history` est une source M1 alternative à MT5 — à évaluer séparément, pas dans COST-02.
- **Reste ouvert, hors COST-02** : `providers/deriv/` et `infrastructure/paper/deriv_gateway.py` sont toujours sur l'ancienne API WebSocket v3 (`authorize` in-band, `symbol` au lieu de `underlying_symbol`). Ils ne sont pas sur le chemin de la mesure, donc délibérément non touchés — mais ils sont **cassés côté serveur** et le seront silencieusement jusqu'à leur portage.

### SIG-02 : Redéfinition de l'horizon cible
- **Objectif** : Mesurer la faisabilité économique AVANT d'entraîner, puis re-tester l'hypothèse « signal exploitable » à un horizon où l'espace économique existe.
- **Priorité** : Critique — bloque la Phase 4
- **Statut** : REJETÉ — Rejeté par la mesure (ADR 0024). L'étape « Recherche de features » avait été sautée ; 0/25 features présentent un signal mesurable hors échantillon.
- **Prérequis** : DATA-01 **résolu** (75000 barres M1, 52 jours). COST-01 **résolu** (ADR 0021).
- **Cible** : **5 barres M1 sur Crash 1000**, **10 barres M1 sur Boom 1000** (ADR 0021, revalidé ADR 0022 sur 75000 barres). Deux horizons, pas un : à marge 3x, Boom rend **23.4 %** de fenêtres à 5 barres contre **94.0 %** pour Crash — l'écart de coût (1.063 vs 0.745 bps) suffit à faire basculer Boom du mauvais côté de sa propre discontinuité de distribution. Un horizon unique serait un choix par commodité, pas par mesure. 5 minutes de détention sur Crash — cohérent avec l'objectif de décisions fréquentes, contre les 4 heures de la fenêtre 60-240 retirée à l'ADR 0020.
- **Horizons écartés et pourquoi** : 1 barre reste **réfuté** (5.8 % de fenêtres sur 75000 barres — troisième confirmation indépendante après l'ADR 0019 et l'ADR 0021). 2 et 3 barres sont **fragiles à la marge** : le ratio s'effondre de 99.0 % à 9.6 % entre marge 1.0x et 2.0x à 2 barres. Un horizon dont la viabilité dépend d'un paramètre non dérivé n'est pas viable — le retenir serait du gate-adjusting (ADR 0018).
- **Outil** : `aegis_trade.domain.tradability` (`tradable_window_ratio`, `is_horizon_tradable`, `max_viable_round_trip_cost`) + `scripts/diagnose_cost_budget_by_horizon.py` et `scripts/diagnose_horizon_vs_cost.py`. Le gate passe AVANT tout entraînement : le budget est un plafond atteignable par un oracle, donc un budget sous le coût réel réfute l'horizon sans dépenser de temps de calcul.
- **Déblocage technique fait** : l'horizon du label n'est plus câblé. `DatasetBuilder(horizon=N)` étiquette à `forward_return_N` (nom dérivé de l'horizon pour que deux campagnes d'horizons différents ne se confondent pas dans le registre), et `scripts/train_qlib_model.py --horizon N` l'expose. Horizon < 1 refusé (0 = fuite, négatif = passé). La fuite de cible reste couverte : `model_factory._feature_matrix` exclut `dataset.target_col` par son nom exact, pas seulement la constante.
- **TRANCHÉ (ADR 0023) — « horizon du label » ≠ « durée de détention »** : la question était réelle. Le gate mesure une sortie **temporelle** (`absolute_moves` compare `t+horizon` à `t`), `MLStrategy` fait une sortie **par persistance** — les 94.0 % étaient le plafond oracle d'une autre stratégie que celle à entraîner. Tranché **par la mesure, pas par goût** : la distribution des détentions d'un oracle est calculable sans entraîner quoi que ce soit. Règle de décision pré-enregistrée et imprimée avant les chiffres. Résultat sur 75000 barres, coûts retenus de l'ADR 0021 : détention **médiane = 5 barres sur Crash** (méd/H 1.00) et **10 sur Boom** (1.00), stable aux trois marges 1x/2x/3x. Verdict : **sortie par persistance CONSERVÉE, `MLStrategy` inchangée, gate valide tel quel**. La conception sans état est préservée — pas de second registre de vérité face au broker.
  - **Contre-épreuve obligatoire** : le recouvrement des fenêtres (`forward_return_5[i]` et `[i+1]` partagent 4 barres sur 5) pouvait produire cette médiane par pur artefact. Marche aléatoire sans mémoire, σ calé **par bisection sur la même exposition** que la série réelle (premier essai confondu : 74.08 % contre 93.97 %) : méd/H tombe à **0.60** (Crash) et **0.30** (Boom), avec 58 % et 74 % de détentions courtes. Artefact réfuté — la persistance appartient aux séries.
  - **Coût assumé, à relever dans le P&L** : **12.4 %** (Crash) et **26.6 %** (Boom) des détentions se ferment **avant** l'horizon sur lequel le seuil d'entrée a été dimensionné. Régime minoritaire, pas nul. Non re-débattu : il apparaîtra en net au backtest.
  - **Outil** : `scripts/diagnose_signal_persistence.py` (graine du contrôle versionnée) + `oracle_target_exposure` / `oracle_holding_periods` dans `domain/tradability.py`. `oracle_target_exposure` reproduit la règle de décision **exacte** de `MLStrategy.generate_signals` — les deux évoluent ensemble. Tout nouvel instrument ou horizon repasse par ce script avant entraînement : la propriété est mesurée, jamais garantie.
- **REJETÉ (ADR 0024)** : Entraînements LightGBM Crash 1000 h5 et Boom 1000 h10 à score 0/100. La décomposition P&L brut/coût montre un brut négatif sur Crash (−2315.29 $) et non distinguable de zéro sur Boom (+1461.24 $, t = +0.54). L'Alpha Research (Spearman IC) montre que 0/25 features survivent aux 4 cas. L'étape « Recherche de features » du pipeline avait été sautée. Campagne close.


### FE-01 : Recherche de features obligatoire (Phase 4) — BLOQUANT
- **Objectif** : Mesurer l'Information Coefficient (IC Spearman) et la significativité ($|t| > 2.0$) de chaque feature candidat sur Train et Test avant tout entraînement de modèle.
- **Priorité** : Bloquante — condition préalable absolue à toute future campagne de signal
- **Statut** : À FAIRE (Outil `scripts/run_feature_research.py` disponible et testé)
- **Raison** : L'omission de cette étape sur SIG-01 et SIG-02 a conduit à entraîner des modèles sur des features au pouvoir prédictif mesuré nul (ADR 0024).
- **Corroboration externe** : L'étude statistique indépendante de Berko (2026, 15M ticks sur MT5 Demo, HMM + test Poisson post-spike) confirme l'absence d'edge exploitable court terme après coûts sur Boom/Crash 1000. Voir [EXTERNAL_FINDINGS_SPIKE_HYPOTHESIS.md](file:///mnt/WindowsData/AI_Hedge_Fund/docs/research/EXTERNAL_FINDINGS_SPIKE_HYPOTHESIS.md).


### KRO-01 : Kronos-mini (Phase 4) — SUSPENDU
- **Objectif** : Substituer un modèle de séquence à LightGBM.
- **Statut** : SUSPENDU — Un meilleur modèle sur des features sans pouvoir prédictif mesuré est déjà réfuté par l'ADR 0019 et l'ADR 0024.
- **Raison** : sur `forward_return_1`, un meilleur modèle prédirait plus précisément une grandeur trop petite pour être tradée. Gain de précision réel, gain économique nul (ADR 0019). Sur SIG-02, 0/25 features ont du signal (ADR 0024).


### GOLD-01 : Troisième actif réel — valider l'infrastructure avant d'y greffer du ML

- **Objectif** : mesurer Gold de bout en bout sur l'outillage existant (ingestion Deriv → coût A/R réel
  → gate de tradabilité → backtest baseline), **avant** d'auditer le Council ou de reconstruire un
  pipeline ML. Si l'infrastructure a un défaut structurel, il vaut mieux le découvrir sur un troisième
  actif que sur un nettoyage de Lot 6 ou un pipeline reconstruit.
- **Priorité** : Haute — succède à l'annualisation (Lot 3), précède l'audit Council/ML
- **Statut** : REJETÉ (ADR 0025 — coût A/R 1.859 bps, gate domain/tradability passé dès H5 (>75.6% tradable), mais 0/25 features d'oscillateur significatives de H5 à H120)
- **Pourquoi maintenant** : Crash 1000 et Boom 1000 sont mesurés de bout en bout (DATA-01, COST-01,
  COST-02, ADR 0021→0024). Gold ne l'a jamais été. Les deux instruments mesurés sont des **synthétiques
  Deriv** — deux membres de la même famille. Un troisième actif de famille différente est ce qui
  distingue « l'infrastructure marche » de « l'infrastructure marche sur des synthétiques ».
- **Aucune refonte** : `fetch_candles_paginated` (DATA-01), `measure_deriv_live_round_trip.py` (COST-02),
  `domain/tradability` et `run_feature_research.py` existent, sont testés, et prennent l'instrument en
  paramètre. GOLD-01 est une campagne de mesure, pas une construction.

**Deux prérequis, tous deux mesurés — Gold n'est PAS outillé aujourd'hui :**

1. **Les données actuelles ne conviennent pas.** `data/market_data/xauusd.parquet` contient **122 barres
   D1** (2026-02-05 → 2026-07-31), sourcées **OpenBB** (`scripts/fetch_training_data.py:81-102`), pas
   Deriv. Contre 75000 barres M1 Deriv pour Crash/Boom. Backtester Gold sur ce fichier ne testerait ni
   la source de production, ni la granularité cible, ni la puissance statistique exigée par DATA-01 —
   ce serait mesurer un autre système. **Action : ingérer Gold en M1 via `fetch_candles_paginated`**,
   au symbole Deriv correspondant (à résoudre dans les 78 symboles rendus par `active_symbols`, route
   ouverte depuis COST-02).
2. **Le coût de Gold est inconnu et n'est pas transposable.** L'ADR 0021 établit que les synthétiques
   Deriv sont cotés sur **un flux à prix unique, sans spread** — c'est ce qui rend le coût Crash/Boom
   égal à la seule commission (0.745 / 1.063 bps). **Gold n'est pas un synthétique.** Rien ne garantit
   ni l'absence de spread, ni le même barème. Réutiliser 0.745 bps sur Gold produirait un chiffre exact
   et faux, et tout verdict de tradabilité en aval en hériterait. **Action : rejouer
   `scripts/measure_deriv_live_round_trip.py` sur Gold** (compte démo `DOT93925868`, garde-fous inchangés),
   puis transcrire le résultat en ADR — le CSV est gitignoré, une mesure non transcrite n'existe pas
   hors de la machine (leçon COST-02).

**Ordre imposé, hérité du pipeline :** ingestion M1 → coût A/R mesuré → **gate de tradabilité**
(`domain/tradability`, avant tout entraînement) → recherche de features (FE-01) → seulement ensuite un
modèle. Le gate passe avant l'entraînement précisément parce qu'un budget de coût sous le coût réel
réfute l'horizon sans dépenser de calcul (SIG-02). Sauter le gate est ce qui a produit les rejets
ADR 0019 et 0024.

**Critère de sortie** : un verdict de tradabilité sur Gold appuyé sur un coût A/R **mesuré sur Gold**
et un historique M1 Deriv de profondeur comparable à Crash/Boom. **Un rejet propre est un succès** —
si Gold est non tradable aux coûts réels, on l'écarte avec preuve reproductible et l'infrastructure est
validée par la mesure elle-même.

**Ce que GOLD-01 ne promet pas** : ni que Gold soit tradable, ni qu'un edge existe. Il promet que
l'infrastructure aura été exercée sur un actif hors de la famille des synthétiques avant qu'on lui
ajoute une couche ML.


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

### DEBT-03 : `HoldOutValidator` et `WalkForwardValidator` à faire correspondre à leur nom ou à renommer
- **Constat** : `scripts/train_qlib_model.py:210` passe le même dataset de test `ListDataFeed(test_sets)` à tous les validateurs. `HoldOutValidator` n'isole aucun sous-segment complémentaire (`ratio: 0.2` est une métadonnée décorative) et `WalkForwardValidator` découpe le segment en 5 folds sans jamais réentraîner la stratégie (contrôle de stabilité inter-période).
- **Impact** : Les chiffres sont valides et hors échantillon, mais les noms des validateurs mentent sur ce qu'ils font.
- **Action** : Réaligner l'implémentation des validateurs avec leur dénomination ou renommer les classes pour éviter toute ambiguïté sur les métriques de validation.


