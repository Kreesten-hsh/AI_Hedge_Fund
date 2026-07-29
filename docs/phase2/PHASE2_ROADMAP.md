# Phase 2 : Roadmap Détaillée et Stratégie de Validation

Le développement de la Phase 2 est séquencé en 7 missions strictement interdépendantes, aboutissant sur un pipeline de validation de niveau institutionnel.

## [x] AI-01 : Memory Engine
**Objectif :** Poser les fondations de l'Experience Memory (FAISS, Embeddings).

## AI-02 : Reflection Engine
**Objectif :** Créer la boucle post-trade (Feature Engineering, Storage).

## AI-03 : Reasoning Engine
**Objectif :** Transformer les expériences de marché brutes de FAISS en règles métier exploitables, statistiques, versionnées et vérifiables.

## AI-04 : Reinforcement Learning
**Objectif :** Intégrer FinRL pour l'optimisation des poids de décision, en s'appuyant sur la base de connaissances.

## AI-05 : Multi Agent Council
**Objectif :** Implémenter le comité de prise de décision (Trend, Momentum, Volatility, etc.) en utilisant le Reinforcement Learning et les règles validées par le Reasoning Engine.

---
## Pipeline de Validation (AI-06 à AI-07)

Afin d'atteindre le statut d'OS Quantitatif professionnel, la validation suit une montée en charge drastique :

### 1. Historical Validation (AI-05a)
- **Objectif :** Backtest pur sur des données EOD et tick-by-tick passées.
- **Méthode :** Validation mathématique des modèles (Overfitting checks).

### 2. Replay Validation (AI-05b)
- **Objectif :** Tick-Replay (Simulation du temps réel).
- **Méthode :** Rejeu d'une semaine historique à vitesse 100x pour tester la latence et la stabilité du code.

### 3. Paper Trading (AI-06a)
- **Objectif :** Exécution Live sans argent réel.
- **Méthode :** Compte Demo. Validation de la connectivité Broker et accumulation d'expériences.

### 4. Shadow Trading (AI-06b)
- **Objectif :** Vérification de Slippage.
- **Méthode :** Le système tourne avec les données du compte Live, génère les signaux, les logge, mais *n'envoie pas* l'ordre au Broker. Comparaison des prix théoriques vs réels.

### 5. Micro Capital (AI-07a)
- **Objectif :** First Blood.
- **Méthode :** Compte Live réel, mais capital limité à une fraction (ex: 50$). Lot minimum. But : Vérifier la gestion psychologique/technique des pertes réelles.

### 6. Production (AI-07b)
- **Objectif :** Scale-up.
- **Méthode :** Allocation du capital total. Respect absolu de l'`AEGIS_DECISION_PIPELINE.md`.
