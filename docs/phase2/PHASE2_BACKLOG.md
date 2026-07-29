# Phase 2 : Backlog Technique

## Priorité 0 (Bloquant)
- ~~**[AI-01-A]** Choix et implémentation de la librairie d'Embedding (ex: SentenceTransformers / OpenAI Embeddings).~~ *(Fait - BasicDeterministicEmbedding)*
- ~~**[AI-01-B]** Intégration de FAISS dans la couche Infrastructure et création des Adapters.~~ *(Fait - FaissVectorStore)*
- **[AI-02-A]** Câblage du module "Feature Extraction" à l'EventBus (écoute des MarketBars et OrderEvents).
- **[AI-02-B]** Implémentation du routeur Post-Trade (Redirection Gain vers SuccessMemory, Perte vers FailureMemory).

## Priorité 1 (Critique)
- **[AI-03-A]** Conception de l'abstraction `IClusterEngine` (DBSCAN/HDBSCAN) et clustering des expériences de FAISS.
- **[AI-03-B]** Implémentation du LLM Adapter Local (`OllamaReasoner`) et du `KnowledgeValidator` avec la création des objets `Knowledge` et `KnowledgeScore`.
- **[AI-04-A]** Conception mathématique de la *Reward Function* intégrant les 8 paramètres définis.
- **[AI-04-B]** Adapter FinRL à l'environnement Event-Driven d'Aegis (Custom Gym Environment).
- **[AI-05-A]** Définition des prompts et rôles du Comité Multi-Agents.
- **[AI-05-B]** Implémentation du Droit de Veto du Risk Engine au niveau du Domain basé sur la Knowledge Base.

## Priorité 2 (Optimisation & Exploitation)
- **[AI-05-A]** Automatisation de l'export des logs vers le *Research Logbook*.
- **[AI-05-B]** Optimisation de la recherche de similarité (Top 200) pour garantir une latence HFT-compatible.
- **[AI-06-A]** Dashboard Metrics pour le suivi de la taille de la mémoire (Nombre d'expériences par catégorie).
