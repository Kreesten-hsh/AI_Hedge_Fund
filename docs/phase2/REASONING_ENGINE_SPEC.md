# Spécification du Moteur de Raisonnement (Reasoning Engine)

Le Reasoning Engine constitue la couche AI-03 de l'OS Quantitatif Aegis. Il ne prend aucune décision de trading (réservée au Multi-Agent Council). Son rôle exclusif est de digérer la base d'expériences (Experience Memory) pour générer, valider et archiver des règles métiers statistiques ("Knowledge").

## 1. Architecture Générale

```text
FAISS (Experience Memory)
      │
      ▼
Pattern Cluster Engine (DBSCAN / HDBSCAN)
      │
      ▼
LLM Adapter (LocalLlamaReasoner) -> Génère une hypothèse
      │
      ▼
Knowledge Validator -> Vérifie l'hypothèse contre les datas réelles
      │
      ▼
Knowledge Repository (Stockage versionné)
```

## 2. Les Composants Clés

### 2.1 Experience Quality Analyzer
S'assure de l'hygiène des données *avant* l'injection dans FAISS.
- Vérifie la validité des bougies.
- Vérifie que le spread et le slippage n'étaient pas absurdes (erreur broker).
- Les expériences rejetées ne polluent jamais la mémoire.

### 2.2 Pattern Cluster Engine
Une abstraction `IClusterEngine` qui supporte plusieurs algorithmes (DBSCAN, HDBSCAN, OPTICS). K-Means est proscrit car le nombre de "vérités de marché" (k) est inconnu.
Il identifie des îlots vectoriels dans FAISS (ex: 200 pertes partageant le même sous-espace).

### 2.3 LLM Adapter
Interface `ILLMReasoner`.
- `MockReasoner` pour les tests.
- `OllamaReasoner` pour une exécution locale, privacy-first, sans appel d'API Cloud.
Il reçoit un cluster et "raconte" ce que ce cluster signifie mathématiquement.

### 2.4 Knowledge Validator
Le rempart contre les hallucinations de l'IA.
Toute règle émise par le LLM est confrontée statistiquement à la base FAISS. Si le support ou la confiance n'est pas mathématiquement prouvé, la règle est détruite.

### 2.5 Knowledge Score & Versioning
Toute règle vivante a un Score (Confiance, Récence, Stabilité).
Le système versionne la connaissance : on peut auditer les règles acquises à une date précise (`KnowledgeSnapshot`).
