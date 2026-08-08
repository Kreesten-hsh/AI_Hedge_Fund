# ADR 0032 — Pivot vers le Pipeline Cognitif Sémantique v2.0 & Audit de Réutilisation Système

- **Statut** : ACCEPTÉ / SCELLÉ (Pivot Stratégique v2.0)
- **Date** : 2026-08-08
- **Contexte technique** : `src/aegis_trade/application/paper_trading/orchestrator.py`, `src/aegis_trade/domain/council.py`, `src/aegis_trade/infrastructure/llm/adapters/ollama_adapter.py`, `src/aegis_trade/infrastructure/memory/faiss_store.py`
- **Dépend de** : ADR 0017 (Score Monotone), ADR 0018 (Seuils Dérivés du Coût), ADR 0021 (Péage d'Exécution), ADR 0024 (Rejet SIG-02), ADR 0028 (Council Audit), ADR 0030 (Réfutation H4/D1 Macro), ADR 0031 (Réfutation Crypto Trend & ML Ranking)
- **Résout** : Échec structurel des approches par force brute statistique et redirection intégrale des ressources vers l'autonomie cognitivo-sémantique via LLM local.

---

## 1. Contexte et Motif du Pivot Stratégique

Entre les ADR 0017 et 0031, le projet Aegis Quant OS a évalué **216 hypothèses quantitatives et statistiques** réparties sur :
1. Les indicateurs de tendance et de cassure univariés (EMA, RSI, Bollinger) à haute et basse fréquence (M1, H4, D1).
2. Les facteurs macroéconomiques et de positionnement (FRED, CFTC COT, GLD ETF).
3. Le ranking cross-sectionnel Machine Learning multi-actifs (LightGBM / GBDT).
4. Le suivi de tendance crypto 24/7 (VectorBT / Freqtrade).

### Bilan Quantitatif d'Échec : **0 / 216 hypothèses validées**
- **ADR 0024 (SIG-02)** : 0/25 features significatives sur Crash 1000 et Boom 1000. Brut non distinguable de zéro ($|t| < 1.87$).
- **ADR 0030 (Macro H4/D1)** : 0/188 features validées. Rejet du DXY pour régression fallacieuse et absence de pouvoir prédictif hors échantillon.
- **ADR 0031 (Crypto & ML Ranking)** : Sharpe de $-2.26$ sur BTC-USD, IC Out-Of-Sample de $-0.0087$ pour le ranking LightGBM.

**Conclusion** : La recherche d'alpha par extraction de signaux numériques en force brute sur données de prix univariées est à efficience de marché complète face aux péages d'exécution ($1.859\text{ bps}$ sur l'Or, $10\text{ bps}$ sur Crypto Spot).

En conséquence, Aegis Quant OS effectue un **pivot d'architecture vers la version 2.0** : remplacement du moteur de prédiction statistique par un **pipeline cognitif sémantique autonome**, piloté par un LLM local (Ollama / vLLM), sans intervention humaine dans la boucle de décision.

---

## 2. Décisions Fondatrices de la Version 2.0

1. **Autonomie Sémantique Complète** : Le LLM local analyse le contexte sémantique (régimes de marché, actualités, structure de carnet et dynamiques de volatilité) pour formuler des hypothèses et émettre des intentions de trading.
2. **Coexistence des Garde-Fous Déterministes** : Le `MultiAgentCouncil` préexistant et les règles de gestion du risque du Module 1 conservent leur autorité absolue. Le gate de risque s'applique **strictement APRES** la proposition sémantique du LLM. Un veto déterministe est final et irrévocable.
3. **Apprentissage par Mémoire d'Expérience (RAG)** : Aucune modification des poids du modèle n'est effectuée. L'apprentissage repose sur la capitalisation des trades passés (contexte, décision, P&L net) journalisés sous forme d'embeddings vectoriels (`FaissVectorStore`) et réinjectés dans le prompt du LLM.

---

## 3. Carte d'Audit et de Réutilisation du Codebase Existant

Pour éviter toute réécriture superflue (Conformité Directive AGENTS.md §2 et §4), les composants existants du dépôt sont cartographiés et réutilisés intégralement selon la matrice suivante :

| Module V2.0 | Composant Existant | Emplacement Fichier:Ligne | Statut de Réutilisation | Rôle dans l'Architecture V2.0 |
| :--- | :--- | :--- | :--- | :--- |
| **Module 1 : Orchestrateur Déterministe** | `Orchestrator` | `src/aegis_trade/application/paper_trading/orchestrator.py` | **Réutilisé à 100%** | Boucle d'événement, séquencement et dispatch des ordres |
| | `MultiAgentCouncil` & `AgentVote` | `src/aegis_trade/domain/council.py:1-85` | **Réutilisé à 100%** | Veto déterministe impératif (Liquidity/Execution $\ge 0.8$) après prompt LLM |
| | `RiskGate` | `src/aegis_trade/engine/risk_gate.py:1-95` | **Réutilisé à 100%** | Contrôle des limites de capital et drawdown maximum |
| | `SimulatedBroker` / `DerivGateway` | `src/aegis_trade/infrastructure/brokers/simulated_broker.py:1-90` | **Réutilisé à 100%** | Adaptateur d'exécution broker et simulation de slippage |
| **Module 2 : Agent Cognitif** | `OllamaAdapter` | `src/aegis_trade/infrastructure/llm/adapters/ollama_adapter.py:1-110` | **Réutilisé à 100%** | Inférence LLM locale via API Ollama / vLLM |
| | `LLMProviderFactory` | `src/aegis_trade/infrastructure/llm/factory.py:1-50` | **Réutilisé à 100%** | Instanciation dynamique du fournisseur LLM selon `config/llm.yaml` |
| | `DecisionCache` | `src/aegis_trade/infrastructure/cache/decision_cache.py:1-80` | **Réutilisé à 100%** | Déduplication des contextes d'inférence et économie de jetons |
| | Templates de Prompt | `src/aegis_trade/prompts/` | **À étendre** | Templates `cognitive_agent_v1.md` pour le raisonnement sémantique |
| **Module 3 : Boucle RAG** | `FaissVectorStore` | `src/aegis_trade/infrastructure/memory/faiss_store.py:1-120` | **Réutilisé à 100%** | Indexation vectorielle et récupération k-NN de la mémoire d'expérience |
| | `BasicEmbedding` | `src/aegis_trade/infrastructure/memory/basic_embedding.py:1-60` | **Réutilisé à 100%** | Vectorisation des contextes décisionnels et résultats de P&L |
| | `MemoryEntry` | `src/aegis_trade/domain/memory.py:1-50` | **Réutilisé à 100%** | Structure de données immuable des souvenirs d'expérience |
| **Module 4 : Observation** | `LLMMetrics` | `src/aegis_trade/infrastructure/llm/metrics.py:1-75` | **Réutilisé à 100%** | Journalisation JSON structurée (latence, tokens, cache hits) |
| | Frontend Dashboard | `frontend/` | **Conservé (Lot 2)** | Observation temps réel de l'état du système et de la mémoire |

---

## 4. Conséquences et Prochaines Étapes

1. **Aucun code applicatif** n'est produit dans ce sprint (Sprint Documentaire).
2. Rédaction des spécifications d'ingénierie V2.0 (`SYSTEM_ARCHITECTURE_V2.md`, `RAG_LEARNING_LOOP_SPEC.md`, `DEMO_EXIT_CRITERIA.md`).
3. Les sprints ultérieurs mettront en œuvre l'assemblage du pipeline sémantique et la validation empirique sur $N \ge 100$ trades.
