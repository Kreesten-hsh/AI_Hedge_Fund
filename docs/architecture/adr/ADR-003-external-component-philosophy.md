# ADR-003: External Component Philosophy & Anti-Corruption Layer

## 1. Contexte
En intégrant des briques open source massives comme OpenBB (ingestion), Qlib (backtest) et vn.py (exécution), il existe un risque mortel : le "Dependency Hell" ou couplage fort. Si Aegis utilise directement les objets `vnpy.trader.object.OrderData` dans sa logique de décision, le jour où vn.py change son API, tout le moteur de décision d'Aegis s'effondre.

## 2. Décision
**Application stricte du Pattern Adaptateur (Architecture Hexagonale) et Anti-Corruption Layer (ACL).**
- Le cœur d'Aegis manipule exclusivement ses propres objets (Data Transfer Objects - DTOs) définis en interne (ex: `AegisOrder`, `MarketBar`, `ResearchReport`).
- Tout composant externe est isolé derrière une interface (Port) et une implémentation (Adaptateur).
- Interdiction absolue d'importer une classe d'un composant externe (ex: `import openbb`) dans les couches `DecisionEngine`, `CouncilOrchestrator` ou `PortfolioEngine`.

## 3. Justification
Cela garantit que l'Orchestrateur (Aegis) reste indépendant de ses membres. Qlib, vn.py et OpenBB sont traités comme de simples "plugins" interchangeables. L'ACL traduit les données du monde extérieur vers le dialecte pur d'Aegis, protégeant notre logique métier.

## 4. Conséquences
- **Positif :** Agilité maximale, tests unitaires (TDD) facilités par des Mocks parfaits (Mission G validée avec succès).
- **Négatif :** Boilerplate supplémentaire requis pour écrire les classes de traduction (Adaptateurs).
