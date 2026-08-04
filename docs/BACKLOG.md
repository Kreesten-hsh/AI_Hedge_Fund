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
- **Statut** : TRANCHÉ — route M15 retenue (ADR 0020). Ingestion à faire.
- **Raison** : à un horizon de 240 barres, 1500 barres de test ne donnent que ~6 fenêtres indépendantes. Re-tester SIG-02 sur ce jeu reproduirait le même défaut de puissance statistique : un résultat, quel qu'il soit, ne serait pas concluant.
- **Contrainte technique** : `DerivHistoricalData.fetch_candles` plafonne à **5000 bougies par requête** (`historical_data.py:38`, `end: "latest"`). Relancer `scripts/fetch_training_data.py` avec un `count` plus grand ne suffit donc pas — l'API refuse. Deux routes, toutes deux vérifiées ouvertes :
  1. **Pagination** — reculer `end` dans le temps puis concaténer et dédupliquer. **Testé, fonctionne.** Lève le plafond sans changer de granularité.
  2. **Granularité plus grossière** — sous le même plafond, le M15 couvre ~52 jours contre ~3.5 jours en M1. **Testé, fonctionne** (`data/market_data/crash1000_m15.parquet`).
- **Mesure de départage** (ADR 0020) : à détention égale et **sur période commune**, le budget de coût M15 égale le M1 à ±3 % de 15 min à 8 h. Passer en M15 ne rétrécit donc pas la cible économique. Attention : comparées sur leurs étendues natives, les mêmes séries montrent −23 % à 8 h — un effet de régime, pas d'agrégation.
- **Réserve encore OUVERTE** : la mesure de départage compare des mouvements de bout en bout et est **aveugle au chemin intra-fenêtre par construction**. Elle ne dit rien sur la capacité de features calculées en M15 à voir les spikes de Crash 1000. Cette question se tranche côté features, dans SIG-02.

### COST-01 : Mesurer le coût de transaction Deriv réel
- **Objectif** : Obtenir le coût aller-retour réel sur Crash 1000 et Boom 1000 — spread intégré **et** commission de multiplier, pas l'un sans l'autre.
- **Priorité** : Critique — prérequis de SIG-02
- **Statut** : BLOQUÉ hors API publique
- **Constat** (ADR 0020) : le catalogue d'offres Deriv revient vide depuis l'environnement de développement (`clients_country: bj`). `active_symbols` renvoie 0 symbole sur 3 `app_id` et 2 hôtes, ce qui ferme en cascade `contracts_for`, `proposal` et l'abonnement `ticks`. Seul `ticks_history` répond, et il ne renvoie qu'un prix unique — jamais bid/ask.
- **Route restante** : lecture sur compte réel (panneau de trade Deriv ou MT5). Aucune estimation ne sera câblée en attendant — un chiffre supposé est exactement le défaut corrigé par l'ADR 0018.
- **Usage** : le chiffre obtenu se lit directement dans la table de budget de l'ADR 0020 (`scripts/diagnose_cost_budget_by_horizon.py`) pour fixer l'horizon cible. Aucune re-mesure nécessaire.

### SIG-02 : Redéfinition de l'horizon cible
- **Objectif** : Mesurer la faisabilité économique AVANT d'entraîner, puis re-tester l'hypothèse « signal exploitable » à un horizon où l'espace économique existe.
- **Priorité** : Critique — bloque la Phase 4
- **Statut** : PLANNED
- **Prérequis** : DATA-01 **et** COST-01. Ne pas lancer SIG-02 sur les 5000 barres actuelles.
- **Cible** : la fenêtre « 60-240 barres M1 » de l'ADR 0019 est **retirée** — elle découlait des 30 bps supposés du `SimulatedBroker`, pas d'une mesure. Viser l'horizon le plus COURT dont le budget dépasse le coût réel, ce qui préserve l'objectif de décisions fréquentes. Ordre de grandeur mesuré : ~9.5 bps de budget à 15 min de détention, ~29.5 bps à 1 h (20 % de fenêtres).
- **Outil** : `aegis_trade.domain.tradability` (`tradable_window_ratio`, `is_horizon_tradable`, `max_viable_round_trip_cost`) + `scripts/diagnose_cost_budget_by_horizon.py` et `scripts/diagnose_horizon_vs_cost.py`. Le gate passe AVANT tout entraînement : le budget est un plafond atteignable par un oracle, donc un budget sous le coût réfute l'horizon sans dépenser de temps de calcul.

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
