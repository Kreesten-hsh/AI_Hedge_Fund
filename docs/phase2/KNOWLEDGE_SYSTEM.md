# Système de Connaissances (Knowledge System)

Le Système de Connaissances (Knowledge System) est le cerveau analytique d'Aegis Quant OS. Il transforme les expériences de marché brutes (les trades passés) en règles métier exploitables, statistiques, versionnées et vérifiables.

## 1. Principes Fondamentaux

- **Le LLM n'est pas une source de vérité** : Les modèles de langage sont utilisés uniquement pour générer des hypothèses ou formuler des observations. Ils ne décident pas et ne créent pas de faits.
- **La Validation Statistique est obligatoire** : Toute connaissance générée doit être appuyée par des données issues de FAISS (Experience Memory).
- **Versioning** : Le système de connaissance évolue dans le temps. Ce qui était vrai (un pattern qui fonctionne) peut disparaître avec un changement de régime de marché.
- **Local-First** : Aucun appel réseau externe critique. Les modèles LLM (comme Llama 3 via Ollama) tournent localement.

## 2. Le Cycle de Vie d'une Connaissance

### Étape 1 : Création (Discovery)
L'EventBus émet un événement `ExperienceSavedEvent`. Le moteur de Clustering asynchrone (`FailurePatternDiscovery` ou `SuccessPatternDiscovery`) analyse périodiquement FAISS.
S'il détecte un cluster mathématiquement significatif (ex: 300 expériences de pertes très proches vectoriellement), il délègue l'analyse au `KnowledgeGenerator`.

### Étape 2 : Raisonnement (LLM Adapter)
Le LLM Adapter (`OllamaReasoner`) reçoit le contexte brut du cluster (moyennes des features, variance, descriptions textuelles). Il génère une **Hypothèse** :
> "Le modèle indique que le RSI extrême couplé à une faible liquidité engendre un slippage entraînant une perte de 80% des cas."

### Étape 3 : Validation (KnowledgeValidator)
L'hypothèse est soumise au `KnowledgeValidator`.
Le validateur vérifie :
- Y a-t-il suffisamment d'occurrences dans FAISS ? (Support minimum).
- La probabilité de succès/échec correspond-elle ? (Confidence minimum).
**Si validé** -> L'hypothèse devient une `Knowledge`.
**Si invalidé** -> L'hypothèse est rejetée (Audit Log: `KnowledgeRejected`).

### Étape 4 : Utilisation
La base de connaissances (`KnowledgeRepository`) est chargée en mémoire.
Lors d'une opportunité, les agents (AI-05 Multi-Agent Council) interrogent le `KnowledgeRepository` pour appliquer un Veto ou confirmer un signal.

### Étape 5 : Obsolescence & Rétrogradation
Un `KnowledgeScore` suit l'efficacité de chaque règle.
Si une `Knowledge` cesse d'être observée ou se trompe (Stabilité en baisse, Récence lointaine), son score diminue. Si le score passe sous un seuil, la `Knowledge` est archivée.

## 3. Entités du Système

- **Knowledge** : L'interface mère de toute connaissance.
- **AvoidPattern** : Une règle stricte signalant un cluster d'échecs (déclenche souvent le Risk Veto).
- **PreferredPattern** : Une configuration validée avec un edge positif.
- **RiskObservation** : Une note macro ou de liquidité.
- **KnowledgeScore** : Évalue la fiabilité : `confidence` (%), `support` (nb d'occurrences), `frequency` (répartition), `recency`, `stability`.

## 4. Versioning

Le `KnowledgeRepository` maintient des snapshots :
- `KnowledgeVersion` : L'état de la base à un instant T.
- `KnowledgeSnapshot` : L'export statique (JSON/Pickle) des règles valides.
- `KnowledgeDiff` : Les changements d'apprentissage entre deux semaines (Qu'a appris Aegis ?).
