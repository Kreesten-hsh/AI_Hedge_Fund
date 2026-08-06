# Product Roadmap — Aegis Quant OS

La feuille de route définit les jalons de développement d'Aegis Quant OS. 
Suite à l'audit de maturité produit, la roadmap a été restructurée pour se concentrer sur la création d'un système de trading quantitatif personnel exploitable (Hedge Fund personnel), en écartant toute logique SaaS ou commerciale.

## Sprint 1 : Validation Framework (Mission VA-01) [TERMINÉ]
### Objectif
Construire un laboratoire de validation quantitatif (Walk-Forward, Hold-Out, Monte Carlo, Benchmark) pour tester automatiquement la robustesse d'une stratégie avant toute intégration ML.
### Contraintes
- Ne pas modifier les moteurs existants (Backtester, Portfolio, Risk). Le Framework de Validation est un orchestrateur.
### Critères de réussite
- Production d'un rapport de validation JSON générant un "Strategy Score".

## Sprint 2 : Intégration Qlib (Mission QL-01) [TERMINÉ]
### Objectif
Brancher Microsoft Qlib comme moteur d'accélération pour la recherche de signaux et les backtests vectorisés.
### Contraintes
- Qlib ne doit **jamais** calculer les indicateurs techniques (EMA, RSI, etc.). Ces derniers appartiennent au `FeatureEngine` d'Aegis.
- Qlib consomme uniquement les données du `FeatureStore` pré-calculé.
### Critères de réussite
- Les modèles ML de Qlib peuvent être entraînés sur les features générées par Aegis.

## Sprint 3 : Moteur d'Exécution (Mission EX-01 - Paper Trading) [TERMINÉ]
### Objectif
Remplacer le broker simulé par une connexion à un environnement de Paper Trading réel via vn.py ou MetaTrader 5 (MT5).
### Contraintes
- L'adaptateur de broker doit s'intégrer de manière transparente derrière le `PortfolioEngine` et le `RiskEngine`.
### Critères de réussite
- Les ordres générés en local sont exécutés et réconciliés sur un compte de démonstration MT5/vn.py.

## Sprint courant : Validation Macro & Audit Council [EN COURS — 2026-08-06]

### Objectif
Évaluer la puissance prédictive de la **famille de features macroéconomiques fondamentales** sur l'Or (Taux réels 10 ans FRED `DFII10`, DXY, VIX) suite au rejet des indicateurs techniques usuels (ADR 0025), puis soumettre le Council multi-agents à un audit scientifique rigoureux.

### Trajectoire
```
GOLD-01 (M1 Tech: REJETÉ) ──► GOLD-MACRO (DFII10 + OpenBB FRED) ──► Audit Council (8 agents) ──► Pivot Fréquence (H4/D1)
```

### Jalons & Priorités
1. **GOLD-MACRO** : Ingestion & alignement temporel des séries macro FRED (Taux réels `DFII10`) via `OpenBBDataProvider` (ADR 0026), puis validation de l'alpha prédictif via `domain/tradability` et `run_feature_research.py`.
2. **AUDIT COUNCIL** : Audit complet du Council à 8 agents (`domain/council.py`) selon la même grille de mesure rigoureuse (ADR, P&L net vs coût réel mesuré de 1.859 bps).
3. **ÉVALUATION DE FRÉQUENCE** : Si l'absence d'alpha M1 persiste, transition vers des stratégies à horizon plus bas (H4 / D1) privilégiant la conviction sur des mouvements d'amplitude supérieure aux frais de transaction.

### Contraintes
- Aucun modèle ML n'est branché avant que GOLD-01 ait rendu son verdict. Le pipeline
  (Dataset → Backtester → Baseline → Recherche de features → Validations → Modèle) n'admet pas de saut :
  les rejets ADR 0019 et ADR 0024 viennent tous deux d'une étape sautée.
- Le coût de transaction de Gold doit être **mesuré sur Gold**. Les 0.745 / 1.063 bps de l'ADR 0021
  valent pour des synthétiques Deriv sans spread ; Gold n'en est pas un.
- Lot 3 complet (y compris ses éléments gelés dans le Council) reste prérequis obligatoire avant AI-07b
  (engagement d'argent réel).

### Critères de réussite
- Annualisation : `engine/performance.py` seule autorité, test de non-régression numérique par appelant.
- GOLD-01 : verdict de tradabilité appuyé sur un historique M1 Deriv et un coût A/R mesurés sur Gold.
  **Un rejet propre et reproductible compte comme réussite.**

## Sprint 4 : Le Centre de Contrôle (Mission LIVE-01 - Dashboard) [EN COURS]
### Objectif
Construire l'interface visuelle locale (Dashboard) pour superviser le système sans utiliser le terminal.
### Contraintes
- Architecture Local-First (Aucun portail web public).
- Doit afficher : Equity Curve, Drawdown, Positions, Statistiques de performance (Sharpe, Sortino), et les décisions des agents IA.
### Critères de réussite
- Un utilisateur peut monitorer les trades en temps réel et déclencher le Kill Switch manuellement depuis le Dashboard.

## Sprint 5 : Live Trading & Optimisation
### Objectif
Engagement de capital réel sous le contrôle strict du Risk Engine.
### Contraintes
- Déploiement sur un serveur Linux (VPS) fonctionnant 24/7.
### Critères de réussite
- Exécution autonome sur le marché réel sans intervention manuelle (hors supervision).
