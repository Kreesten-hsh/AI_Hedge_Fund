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
- **Statut** : PLANNED
- **Raison** : à un horizon de 240 barres, 1500 barres de test ne donnent que ~6 fenêtres indépendantes. Re-tester SIG-02 sur ce jeu reproduirait le même défaut de puissance statistique : un résultat, quel qu'il soit, ne serait pas concluant.
- **Contrainte technique** : `DerivHistoricalData.fetch_candles` plafonne à **5000 bougies par requête** (`historical_data.py:38`, `end: "latest"`). Relancer `scripts/fetch_training_data.py` avec un `count` plus grand ne suffit donc pas — l'API refuse. Deux routes, à évaluer :
  1. **Pagination** — boucler les requêtes en reculant `end` dans le temps, puis concaténer et dédupliquer. Lève le plafond sans changer de granularité.
  2. **Granularité plus grossière** — sous le même plafond de 5000 bougies, du M15 couvre ~52 jours contre ~3.5 jours en M1. L'horizon tradable de ~60-240 barres M1 (1 à 4 heures) devient 4-16 barres M15, ce qui donnerait ~90 fenêtres indépendantes au lieu de 6.
- **Réserve** : la route 2 n'est pas gratuite — Crash 1000 est un indice à spikes, et agréger en M15 peut masquer la structure même qu'on cherche à prédire. Aucune des deux routes n'est présumée bonne : mesurer avec le gate de faisabilité AVANT d'ingérer massivement.

### SIG-02 : Redéfinition de l'horizon cible
- **Objectif** : Mesurer la faisabilité économique AVANT d'entraîner, puis re-tester l'hypothèse « signal exploitable » à un horizon où l'espace économique existe (~60-240 barres d'après ADR 0019).
- **Priorité** : Critique — bloque la Phase 4
- **Statut** : PLANNED
- **Prérequis** : DATA-01. Ne pas lancer SIG-02 sur les 5000 barres actuelles.
- **Outil** : `aegis_trade.domain.tradability` (`tradable_window_ratio`, `is_horizon_tradable`) + `scripts/diagnose_horizon_vs_cost.py`. Le gate passe AVANT tout entraînement : `tradable_window_ratio` est un plafond atteignable par un oracle, donc un plafond nul réfute l'horizon sans dépenser de temps de calcul.

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
