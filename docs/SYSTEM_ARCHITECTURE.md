# Architecture Système — Aegis Quant OS

Aegis Quant OS repose sur une **Architecture Hexagonale (Ports et Adapters)** couplée au **Domain Driven Design (DDD)**. 
L'objectif est d'isoler strictement la logique de trading (Domain & Engine) des détails d'implémentation (Data Providers, Brokers, LLMs, UIs).

## Vue d'Ensemble de l'Architecture (Big Picture)

Le schéma ci-dessous illustre le flux de données de bout en bout, depuis l'ingestion des données jusqu'à l'exécution des ordres, en passant par l'analyse IA. 
Le **Dashboard local** est branché transversalement sur toutes les couches pour offrir une supervision complète.

```mermaid
graph TD
    %% Providers Extérieurs (Data & ML)
    OpenBB[OpenBB / Polygon] -->|Market Data| DataPipeline[Data Pipeline]
    
    %% Core Engines
    DataPipeline --> FeatureEngine[Feature Engine / Qlib]
    FeatureEngine -->|Signaux & Features| AICouncil[AI Council]
    
    %% AI Council Sub-Agents
    subgraph AICouncil [AI Council (Agents Multiples)]
        MacroAnalyst[Macro Analyst]
        RiskAnalyst[Risk Analyst]
        TechnicalAnalyst[Technical Analyst]
        Synthesizer[Synthesizer]
        
        MacroAnalyst --> Synthesizer
        RiskAnalyst --> Synthesizer
        TechnicalAnalyst --> Synthesizer
    end
    
    %% LLM Providers
    LLMs[(LLM Providers)] -.->|Ollama / vLLM / Claude| AICouncil
    
    %% Trading Logic
    AICouncil -->|Décision| Portfolio[Portfolio Engine]
    Portfolio -->|Ordre Proposé| Risk[Risk Engine]
    
    %% Execution
    Risk -->|Ordre Validé| Execution[Execution Engine]
    Execution --> Gateway[Broker Gateway]
    
    %% External Brokers
    Gateway -->|vn.py / IB| Brokers[(Brokers Réels)]
    
    %% Dashboard (Transverse)
    Dashboard((Dashboard Local))
    Dashboard -.->|Supervise| DataPipeline
    Dashboard -.->|Supervise| FeatureEngine
    Dashboard -.->|Supervise| AICouncil
    Dashboard -.->|Supervise| Portfolio
    Dashboard -.->|Supervise| Risk
    Dashboard -.->|Supervise| Execution
    
    classDef domain fill:#0f172a,stroke:#3b82f6,stroke-width:2px,color:#fff;
    classDef external fill:#475569,stroke:#94a3b8,stroke-width:1px,color:#fff;
    classDef transverse fill:#166534,stroke:#22c55e,stroke-width:2px,color:#fff;
    
    class AICouncil,Portfolio,Risk,Execution,FeatureEngine,DataPipeline domain;
    class OpenBB,Brokers,LLMs external;
    class Dashboard transverse;
```

## Les 6 Composants Majeurs

### 1. Data Pipeline
Responsable de l'ingestion, du nettoyage et de l'harmonisation temporelle des données. Il agit comme un cache local (base de données time-series ou Parquet) pour minimiser la latence réseau et les coûts d'API. Il abstrait les sources externes (OpenBB, Polygon, Yahoo).

### 2. Feature Engine
Transforme les données brutes en *features* (indicateurs techniques, sentiments, modèles statistiques). Il intègre des moteurs avancés comme **Qlib** pour générer des alphas prédictifs qui nourriront l'IA.

### 3. AI Council
L'orchestrateur de l'intelligence artificielle. Il sollicite plusieurs agents spécialisés (Macro, Risque, Fondamental, Technique) qui analysent le contexte du marché indépendamment. Un `Synthesizer` rassemble ensuite leurs rapports pour générer une **Décision du Conseil** (ex: LONG, SHORT, WAIT, CLOSE).

### 4. Portfolio Engine
Gère l'état global du portefeuille (capital, positions ouvertes, marges). Il traduit la décision de l'AI Council en un **dimensionnement de position** concret (Sizing) selon la volatilité actuelle et l'allocation cible.

### 5. Risk Engine
Le gendarme du système. Il vérifie toute transaction proposée par le Portfolio Engine par rapport à des règles strictes (Max Drawdown, Corrélation sectorielle, Exposition maximale). Il possède le **Kill Switch** global.

### 6. Execution Engine & Gateway
Gère la transmission des ordres au broker (via vn.py, Interactive Brokers, etc.). Il s'occupe de la logique de passage d'ordre (Limit, Market, VWAP), du slippage, et de la réconciliation des statuts d'ordres.

## Le Dashboard : Centre de Contrôle
Il s'agit de l'interface utilisateur unique du système (sans vocation SaaS). Le Dashboard ne contient **aucune logique métier**. Il se contente de lire l'état des différents moteurs via une API (FastAPI) pour l'afficher à l'opérateur (React/Streamlit), et permet d'intervenir manuellement (Kill Switch, fermeture forcée de positions).
