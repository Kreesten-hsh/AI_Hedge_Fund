# Spécification d'Architecture Système V2.0 — Pipeline Cognitif Sémantique

- **Statut** : SPÉCIFICATION TECHNIQUE V2.0 (Lot 1)
- **Date** : 2026-08-08
- **Contexte technique** : Architecture globale à 4 modules, découplage Clean Architecture, sécurité du chemin critique.
- **Dépend de** : ADR 0002 (Clean Architecture), ADR 0012 (AI Council Pattern), ADR 0032 (Pivot Pipeline Cognitif v2.0), `docs/LLM_INFRASTRUCTURE_V2.md`

---

## 1. Schéma d'Architecture Général V2.0

```text
 ┌──────────────────────────────────────────────────────────────────────────────────────────┐
 │                                MODULE 2 : AGENT COGNITIF                                │
 │                                                                                          │
 │   ┌───────────────────────┐        ┌────────────────────────┐      ┌─────────────────┐   │
 │   │ Context Aggregator    │ -----> │ LLM Reasoning Engine   │ ---> │ Trade Intent    │   │
 │   │ (Market + Regimes)    │        │ (Ollama / vLLM local)  │      │ (JSON Proposal) │   │
 │   └───────────▲───────────┘        └───────────▲────────────┘      └────────┬────────┘   │
 └───────────────┼────────────────────────────────┼────────────────────────────┼────────────┘
                 │                                │                            │
                 │                    Top-k RAG Experience                     │
                 │                    (Cosine Similarity)                      │
                 │                                │                            │
 ┌───────────────┼────────────────────────────────┴────────────────────────────┼────────────┐
 │               │             MODULE 3 : BOUCLE RAG & MÉMOIRE                │            │
 │               │                                                             │            │
 │   ┌───────────┴───────────┐        ┌────────────────────────┐               │            │
 │   │ Trade Outcome Logger  │ -----> │ FaissVectorStore       │               │            │
 │   │ (P&L Net, Context)    │        │ (Index vectoriel)      │               │            │
 │   └───────────────────────┘        └────────────────────────┘               │            │
 └─────────────────────────────────────────────────────────────────────────────┼────────────┘
                                                                               │
                                                                               ▼
 ┌──────────────────────────────────────────────────────────────────────────────────────────┐
 │                           MODULE 1 : ORCHESTRATEUR DÉTERMINISTE                          │
 │                                                                                          │
 │   ┌──────────────────────────────────────────────────────────────────────────────────┐   │
 │   │  ÉVALUATION ET VETO DU RISK GATE & MULTI-AGENT COUNCIL                           │   │
 │   │  - Contrôle des limites de capital (RiskGate)                                    │   │
 │   │  - Veto déterministe impératif MultiAgentCouncil (Liquidity/Execution >= 0.8)   │   │
 │   │  * APPLIQUÉ STRICTEMENT APRÈS LA PROPOSITION LLM — REJET FINAL ET ABSOLU *        │   │
 │   └────────────────────────────────────────┬─────────────────────────────────────────┘   │
 │                                            │                                             │
 │                                            ▼                                             │
 │   ┌──────────────────────────────────────────────────────────────────────────────────┐   │
 │   │  ÉXÉCUTION BROKER (SimulatedBroker / DerivGateway / VNPY)                        │   │
 │   └──────────────────────────────────────────────────────────────────────────────────┘   │
 └────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                              │
                                              ▼
 ┌──────────────────────────────────────────────────────────────────────────────────────────┐
 │                            MODULE 4 : INTERFACE D'OBSERVATION                            │
 │                                                                                          │
 │   - Métriques d'inférence (LLMMetrics JSON)                                              │
 │   - Télémétrie en temps réel (Dashboard local / WebSocket)                               │
 └──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Description Détaillée des 4 Modules

S'appuyant sur la carte de réutilisation scellée dans l'[ADR 0032 §3](file:///mnt/WindowsData/Aegis%20Quant%20OS/docs/ADR/0032-pivot-cognitive-pipeline-and-reuse-audit.md), chaque module réutilise le code existant sans duplication.

### Module 1 : Orchestrateur Déterministe (Contrôle et Exécution)

Ce module détient l'autorité ultime d'exécution. Il héberge les garde-fous déterministes et la gestion du risque.

- **Composants Réutilisés** :
  - `Orchestrator` : `src/aegis_trade/engine/orchestrator.py:1-120` (Boucle d'événements et dispatch).
  - `MultiAgentCouncil` & `AgentVote` : `src/aegis_trade/domain/council.py:1-85` (Agrégation déterministe et gestion des votes).
  - `RiskGate` : `src/aegis_trade/engine/risk_gate.py:1-95` (Limites de drawdown et d'exposition capital).
  - `SimulatedBroker` / `DerivGateway` : `src/aegis_trade/infrastructure/brokers/simulated_broker.py:1-90` (Passerelle broker).
- **Composants à Écrire** :
  - `CognitiveProposalConsumer` : Adaptateur recevant les propositions sémantiques JSON du Module 2 pour conversion en demandes d'ordre normées.
- **Dépendances** : Consomme les intentions émise par le Module 2 ; transmet le statut d'exécution et le P&L au Module 3.

> [!IMPORTANT]
> **Coexistence et Ordre des Vétos (Principe de Sécurité Règle 2)** :
> Le `MultiAgentCouncil` (Module 1, déterministe) et l'Agent Cognitif (Module 2, sémantique) sont deux composants strictement distincts.
> 1. L'Agent Cognitif (Module 2) émet une **proposition d'intention de trade**.
> 2. Le `MultiAgentCouncil` et le `RiskGate` (Module 1) évaluent ensuite cette proposition.
> 3. Si `LiquidityAgent` ou `ExecutionAgent` émet un vote `WAIT` avec une confiance $\ge 0.8$, ou si la limite de risque est franchie, la proposition du LLM est **immédiatement rejetée**. Ce rejet déterministe est **final, irrévocable, et non négociable**.

---

### Module 2 : Agent Cognitif (Raisonnement Sémantique)

Ce module formule les intentions stratégiques en analysant le contexte de marché et les leçons tirées du passé.

- **Composants Réutilisés** :
  - `OllamaAdapter` : `src/aegis_trade/infrastructure/llm/adapters/ollama_adapter.py:1-110` (Adaptateur d'inférence LLM locale).
  - `LLMProviderFactory` : `src/aegis_trade/infrastructure/llm/factory.py:1-50` (Factory de fournisseurs).
  - `DecisionCache` : `src/aegis_trade/infrastructure/cache/decision_cache.py:1-80` (Cache de déduplication).
  - Templates de prompt : `src/aegis_trade/prompts/` (Gestion des structures de prompts).
- **Composants à Écrire** :
  - `CognitiveReasoningEngine` : Assemblage du contexte sémantique, invocation du LLM avec prompt RAG, et extraction du JSON d'intention (`TradeIntent`).
  - Template de prompt `cognitive_agent_v1.md` : Définition des règles de décision sémantique.
- **Dépendances** : Interroge le Module 3 (Boucle RAG) pour récupérer les souvenirs k-NN ; émet vers le Module 1.

---

### Module 3 : Boucle RAG & Mémoire d'Expérience

Ce module stocke et recherche les expériences passées pour alimenter le raisonnement de l'Agent Cognitif.

- **Composants Réutilisés** :
  - `FaissVectorStore` : `src/aegis_trade/infrastructure/memory/faiss_store.py:1-120` (Stockage vectoriel et recherche par similarité cosinus).
  - `BasicEmbedding` : `src/aegis_trade/infrastructure/memory/basic_embedding.py:1-60` (Génération des embeddings sémantiques).
  - `MemoryEntry` : `src/aegis_trade/domain/memory.py:1-50` (Structure immuable du journal d'expérience).
- **Composants à Écrire** :
  - `ExperienceMemoryManager` : Gestionnaire haut niveau d'enregistrement et de requêtage RAG.
- **Dépendances** : Reçoit les confirmations d'exécutions et P&L du Module 1 ; fournit le top-k au Module 2.

---

### Module 4 : Interface d'Observation (Télémétrie et Monitoring)

Ce module assure la visibilité temps réel sur le comportement du pipeline cognitif.

- **Composants Réutilisés** :
  - `LLMMetrics` : `src/aegis_trade/infrastructure/llm/metrics.py:1-75` (Journalisation structurée JSON des métriques LLM).
  - Dashboard Frontend : `frontend/` (Interface utilisateur d'observation local).
- **Composants à Écrire** :
  - `TelemetryBroadcaster` : Publication en temps réel des métriques de décision et d'état de la mémoire RAG.
- **Dépendances** : Écoute passivement les événements des Modules 1, 2 et 3.
