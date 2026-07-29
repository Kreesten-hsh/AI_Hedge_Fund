# Paper Trading Architecture (PT-01)

## Vue d'Ensemble
Le moteur de Paper Trading d'Aegis Quant OS est une simulation de bout en bout qui émule parfaitement un environnement de Live Trading sans engager de capital réel. L'objectif architectural central est de s'assurer que **le passage du Paper Trading au Live Trading ne nécessite qu'un seul changement : le remplacement du `PaperBroker` par le `LiveBroker`**.

## Principes de la Clean Architecture appliqués
Le moteur respecte la ségrégation en 3 couches :

1. **Domain (`domain/paper/`)** :
   - Contient la vérité absolue de la simulation (Ordres, Positions, Fills, Snapshot de Portefeuille).
   - Les objets sont de pures structures de données (dataclasses) et des énumérations. 
   - Aucune dépendance externe.
   - Les machines d'états (ex: transition `CREATED` -> `SUBMITTED` -> `FILLED`) sont validées ici.

2. **Application (`application/paper_trading/`)** :
   - Contient l'**Orchestrateur** (`PaperTradingOrchestrator`).
   - Gère le flux logique : Signal -> Validation Risque (`GlobalRiskManager`) -> Transmission au Broker.
   - Exécute la boucle de monitoring asynchrone générant les `PaperPortfolioSnapshot`.
   - Définit les interfaces (contrats) : `IPaperBroker`, `ISlippageModel`, `IMarketFeed`, etc.

3. **Infrastructure (`infrastructure/paper/`)** :
   - Implémente les interfaces définies par l'Application.
   - Contient le `PaperBroker` qui exécute l'ordre en appliquant virtuellement la latence, le slippage et les commissions via les moteurs spécialisés (ex: `ConstantSlippageModel`, `RandomLatencyModel`).
   - Contient `MarketReplayFeed` pour ingérer le flux de prix.

## Machine d'États des Ordres
L'enum `OrderState` définit le cycle de vie d'un ordre :
- **CREATED** : Créé en interne, en attente de soumission.
- **SUBMITTED** : Envoyé au broker (Paper ou Live).
- **ACCEPTED** : Marge vérifiée et acceptée par le broker.
- **PARTIALLY_FILLED** : Exécuté en partie (non simulé actuellement).
- **FILLED** : Exécuté totalement.
- **CANCELLED** : Annulé par l'utilisateur.
- **REJECTED** : Rejeté par le broker (fonds insuffisants, prix invalide).
- **EXPIRED** : Ordre Limite/Stop non touché à la fin de la session.

## Flux Événementiel
L'architecture est 100% *event-driven*. Le Broker interagit avec le système via des callbacks poussant des événements sur l'Event Bus (défini dans `engine/events.py`) :
- `OrderLifecycleEvent`
- `PositionEvent`
- `AccountEvent`

Ce flux permet de découpler totalement la logique de reporting (Dashboard, Base de données) du cycle de passage d'ordres.
