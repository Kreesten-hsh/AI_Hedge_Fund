# Aegis Quant OS — Architecture

Aegis Quant OS est conçu comme un **Méta-Orchestrateur Institutionnel**. Son architecture suit strictement les principes du **Domain Driven Design (DDD)** et de l'**Architecture Hexagonale (Ports & Adapters)**.

Le système ne réinvente pas les outils bas niveau de la finance quantitative. Il s'appuie sur les meilleurs frameworks open-source via des adaptateurs stricts, pour concentrer sa valeur sur la **Gouvernance de la Recherche (Research Council)** et l'**Exécution (Portfolio Engine)**.

## Séparation des Couches

L'architecture est scindée en trois niveaux d'isolation absolus :

### 1. Aegis Core (Domaine Propriétaire)
Le cœur du système. Il ne possède aucune dépendance vers l'infrastructure ou les bibliothèques externes de traitement (comme `pandas` ou `qlib` dans le domaine pur).
Il contient :
- **Event Bus** : Le système nerveux central. Tous les échanges sont des événements asynchrones et immuables.
- **Research Council (Multi-Agents)** : Gouvernance IA avec séparation stricte des rôles (Regime Analyst, Risk Analyst, Research Analyst).
- **Alpha Validation Protocol** : Règles inflexibles de validation statistique (IC, ICIR, Train/Holdout).
- **Portfolio Engine & Risk Governance** : Décision d'allocation, gestion des expositions et respect des contraintes de risque.

### 2. Couche d'Adaptation (Ports & Adapters)
Les interfaces (Ports) sont définies dans le Domaine. Les Adaptateurs implémentent ces interfaces pour traduire les données et les événements entre le format standardisé d'Aegis et les formats spécifiques des frameworks externes.
- `openbb_adapter` : Connecteur vers OpenBB pour l'ingestion de contexte macro-économique et fondamental.
- `qlib_adapter` : Wrappe les pipelines de feature engineering de Microsoft Qlib.
- `vnpy_adapter` : Implémente l'`ExecutionGateway` pour traduire un `Aegis OrderEvent` en un ordre Live sur vn.py.
- `fingpt_adapter` : Fournisseur de features NLP pour l'analyse de sentiment.

### 3. Moteurs Sous-jacents (Frameworks Externes)
L'infrastructure brute, exécutée de manière isolée ou via appel API.
- **Qlib** : Manipulation lourde de datasets et entraînement ML.
- **vn.py** : Routage d'ordres Live, maintien des connexions WebSocket/FIX avec les brokers.
- **OpenBB SDK** : Agrégateur de données multi-sources.
- **FinGPT** : Inférence LLM financière.

## Principes de Conception (Règles d'or)
- **Domain Driven Design (DDD)** : Les entités (`MarketBar`, `Signal`, `TradeProposal`) sont pures et portent le sens métier.
- **Inversion de Dépendance** : Les adaptateurs dépendent du domaine, jamais l'inverse.
- **Immutabilité & Événements** : Chaque changement d'état génère un événement horodaté en UTC.
- **Zéro État Global Mutable** : Tout est injecté via le constructeur.
