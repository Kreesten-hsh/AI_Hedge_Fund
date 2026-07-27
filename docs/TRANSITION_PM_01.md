# CONTEXTE ET TRANSFERT DE PROJET — AEGIS QUANT OS (MISSION PM-01)

> **À L'ATTENTION DU NOUVEL AGENT** : Ce document contient l'état exact du projet, les règles architecturales absolues, et les instructions de ta mission (PM-01). Lis ce document dans son intégralité avant toute action. N'invente rien.

---

## 1. VISION DU PROJET ET PHILOSOPHIE

**Aegis Quant OS** est un méta-orchestrateur quantitatif institutionnel (Headless).
Nous développons comme une équipe quantitative institutionnelle. Les règles absolues (`.agents/AGENTS.md`) sont :
1. **La roadmap est la seule source de vérité.** Aucun code spéculatif.
2. **Architecture Hexagonale Stricte** : Le domaine (`src/aegis_trade/domain`) est pur, typé strictement, sans dépendances externes (ni pandas, ni Base de Données). L'infrastructure implémente les ports.
3. **Discipline Scientifique et TDD** : Aucun développement n'est validé si la couverture de code n'est pas > 90%, si MyPy échoue, ou s'il n'y a pas de tests unitaires rigoureux.
4. **Pas d'hallucinations** : Si une feature manque, on la code ou on gère son absence. On ne mocke pas en production.

---

## 2. ÉTAT ACTUEL DE L'ARCHITECTURE (TRÈS IMPORTANT)

Actuellement, le projet contient **deux architectures qui vivent en parallèle et ne doivent PAS être mélangées** avant d'y être explicitement invité :

1. **La Piste Événementielle (Legacy/Future)** :
   - Fichiers : `engine/strategy.py`, `engine/core.py`, `engine/portfolio.py`, `engine/global_risk.py`, `agents/*`, et les scripts `run_ai_backtest.py`, `run_paper_trading.py`, etc.
   - **Règle : NE TOUCHE SOUS AUCUN PRÉTEXTE À CES FICHIERS LORS DE TA MISSION.**

2. **La Piste Modulaire (Nouveau Pipeline Quantitatif Actuel)** :
   - Fichiers : `domain/signal.py`, `domain/strategy.py`, `domain/execution.py`, `engine/backtester.py`, `engine/performance.py`, `infrastructure/brokers/simulated_broker.py`, `infrastructure/strategies/*`.
   - **C'est ici que tu travailles.**

---

## 3. MISSIONS DÉJÀ ACCOMPLIES (BASE SOLIDE)

- **DATA-01R, FE-01, FE-02** : Pipeline de données (OpenBB), Feature Engine (basé sur Pandas/Numpy purs, pas de TA-Lib), Feature Store (Parquet local), et Alpha Research Framework (Alphalens). 
- **BT-01 (Backtest Core)** : Moteur de simulation séquentiel. Un `Backtester` itère sur un `FeatureStoreFeed`, passe les données à une stratégie, envoie les `OrderIntent` à un `SimulatedBroker`, et génère un `TearsheetReport` institutionnel 100% vectorisé (`performance.py`).
- **ST-01 (Strategy Framework)** : Hiérarchie de stratégies. Implémentation de `EmaCrossoverStrategy`, `RsiMeanReversionStrategy` et d'une `CompositeStrategy` à vote pondéré. Tout est testé à 99% de couverture. Le script `scripts/run_historical_backtest.py` utilise cette architecture.

L'état des tests actuels est de **42 tests passés, 0 échec**. La couverture du cœur et des stratégies est > 90%.

---

## 4. MISSION DU JOUR : PM-01 (PORTFOLIO MANAGEMENT)

**CONTEXTE :**
Les stratégies (`ST-01`) génèrent aujourd'hui des `Signal` (direction, strength). Le `Backtester` (`BT-01`) prend ces signaux et les convertit naïvement en `OrderIntent` avec une taille fixe ou basique. Il nous manque la couche intermédiaire cruciale : **Le Portfolio Manager**.

**OBJECTIF :**
Implémenter la gestion de portefeuille modulaire (`PM-01`) dans le nouveau pipeline quantitatif (Piste Modulaire), sans toucher au vieux `engine/portfolio.py` de la piste événementielle.

**INSTRUCTIONS D'IMPLÉMENTATION :**

1. **Création du Domaine (Portfolio)** :
   - Créer `src/aegis_trade/domain/portfolio.py` (si nécessaire, ou l'intégrer proprement) définissant les contrats pour le calcul de la taille des positions (Position Sizing).
   - Définir une interface `IPortfolioManager` ou `ISizingModel` qui prend en entrée : le `Signal`, le capital disponible, la volatilité (issue du `FeatureSet`), et retourne un montant ou une quantité exacte à trader.

2. **Implémentation Infrastructure (Modèles de Sizing)** :
   - Créer `src/aegis_trade/infrastructure/portfolio/sizing.py`.
   - Implémenter au moins deux modèles :
     - `FixedFractionalSizing` : Risque un pourcentage fixe du capital (ex: 2%).
     - `VolatilityTargetingSizing` : Ajuste la taille de la position inversement à la volatilité de l'actif (utilise la feature `volatility_20` du `FeatureSet`).

3. **Intégration au Moteur (Backtester)** :
   - Modifier `src/aegis_trade/engine/backtester.py` pour qu'il accepte une instance de `ISizingModel` (ou `IPortfolioManager`) lors de son initialisation.
   - Dans la boucle de simulation, le `Backtester` doit passer le `Signal` et le `FeatureSet` au modèle de sizing pour générer un `OrderIntent` précis au lieu d'une logique naïve codée en dur.

4. **Tests (TDD Strict)** :
   - Écrire des tests unitaires complets pour les modèles de sizing (`tests/infrastructure/portfolio/test_sizing.py`).
   - Mettre à jour `tests/test_backtester.py` pour inclure le mock du Portfolio Manager.
   - Objectif : Couverture > 90% sur le nouveau module de sizing, maintien à 100% de passage sur la suite globale.

5. **Mise à jour de la Démo et du Backlog** :
   - Mettre à jour `scripts/run_historical_backtest.py` pour injecter un modèle de sizing (ex: `VolatilityTargetingSizing`) dans le `Backtester`.
   - Mettre à jour `docs/BACKLOG.md` : passer `PM-01` de `PLANNED` à `COMPLETED`.

**RÈGLE D'ACCEPTATION FINALE :**
- 100% des tests réussissent.
- Aucun fichier de la piste événementielle n'est modifié (Vérification par `git status`).
- Le script de démo génère un Tearsheet sans erreur.

---
**FIN DU DOCUMENT DE TRANSFERT.** 
Nouvel agent, confirme ta compréhension de ces règles avant d'écrire la moindre ligne de code.
