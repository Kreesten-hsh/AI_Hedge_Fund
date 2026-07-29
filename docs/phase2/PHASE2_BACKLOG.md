# Phase 2 : Backlog Technique

## Priorité 0 (Bloquant)
- **[AI-01-A]** Choix et implémentation de la librairie d'Embedding (ex: SentenceTransformers / OpenAI Embeddings).
- **[AI-01-B]** Intégration de FAISS dans la couche Infrastructure et création des Adapters.
- **[AI-02-A]** Câblage du module "Feature Extraction" à l'EventBus (écoute des MarketBars et OrderEvents).
- **[AI-02-B]** Implémentation du routeur Post-Trade (Redirection Gain vers SuccessMemory, Perte vers FailureMemory).

## Priorité 1 (Critique)
- **[AI-03-A]** Conception mathématique de la *Reward Function* intégrant les 8 paramètres définis.
- **[AI-03-B]** Adapter FinRL à l'environnement Event-Driven d'Aegis (Custom Gym Environment).
- **[AI-04-A]** Définition des prompts et rôles du Comité Multi-Agents.
- **[AI-04-B]** Implémentation du Droit de Veto du Risk Engine au niveau du Domain.

## Priorité 2 (Optimisation & Exploitation)
- **[AI-05-A]** Automatisation de l'export des logs vers le *Research Logbook*.
- **[AI-05-B]** Optimisation de la recherche de similarité (Top 200) pour garantir une latence HFT-compatible.
- **[AI-06-A]** Dashboard Metrics pour le suivi de la taille de la mémoire (Nombre d'expériences par catégorie).
