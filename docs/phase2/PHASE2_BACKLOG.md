# Phase 2 : Backlog Technique

## Priorité 0 (Bloquant)
- ~~**[AI-01-A]** Choix et implémentation de la librairie d'Embedding (ex: SentenceTransformers / OpenAI Embeddings).~~ *(Fait - BasicDeterministicEmbedding)*
- ~~**[AI-01-B]** Intégration de FAISS dans la couche Infrastructure et création des Adapters.~~ *(Fait - FaissVectorStore)*
- **[AI-02-A]** Câblage du module "Feature Extraction" à l'EventBus (écoute des MarketBars et OrderEvents).
- **[AI-02-B]** Implémentation du routeur Post-Trade (Redirection Gain vers SuccessMemory, Perte vers FailureMemory).

## Priorité 1 (Critique)
- ~~**[AI-03-A]** Conception de l'abstraction `IClusterEngine` (DBSCAN/HDBSCAN) et clustering des expériences de FAISS.~~ *(Fait)*
- ~~**[AI-03-B]** Implémentation du LLM Adapter Local (`OllamaReasoner`) et du `KnowledgeValidator` avec la création des objets `Knowledge` et `KnowledgeScore`.~~ *(Fait)*
- ~~**[AI-04-A]** Conception mathématique de la *Reward Function* intégrant les 8 paramètres définis.~~ *(Fait - RewardCalculator)*
- ~~**[AI-04-B]** Adapter FinRL/SB3 à l'environnement Event-Driven d'Aegis (Custom Gym Environment).~~ *(Fait - CustomAegisEnv, Asynchronous PolicyTrainer)*
- ~~**[AI-04-C]** Implémentation du Policy Promotion Gate (Validation stricte avant promotion d'un nouveau modèle).~~ *(Fait - PolicyEvaluator)*
- ~~**[AI-05-A]** Définition des prompts et rôles du Comité Multi-Agents.~~ *(Fait - Agents déterministes implémentés)*
- ~~**[AI-05-B]** Implémentation du Droit de Veto du Risk Engine au niveau du Domain basé sur la Knowledge Base.~~ *(Fait - GlobalRiskManager intègre le Veto)*

## Priorité 2 (Optimisation & Exploitation)
- **[AI-05-A]** Automatisation de l'export des logs vers le *Research Logbook*.
- **[AI-05-B]** Optimisation de la recherche de similarité (Top 200) pour garantir une latence HFT-compatible.
- ~~**[AI-06-A]** Historical & Replay Validation (TickReplayEngine, BenchmarkGate).~~ *(Fait)*
- ~~**[AI-06-B]** Live Paper Trading & Shadow Trading (DerivGateway, ShadowTradingEngine).~~ *(Fait)*
- ~~**[AI-07-A]** Micro Capital Live Trading (LiveDerivGateway, CapitalAllocation, sécurité).~~ *(Fait)*
- **[AI-08-A] [PAUSED]** Intégration Kronos-mini Forecasting (Fine-tuning offline repoussé).
