# Migration du Legacy Council

Durant la Phase 1 et le début de la Phase 2 (AI-03), le système utilisait un `CouncilSynthesizer` basé sur un LLM pour prendre des décisions directes de trading.

## 1. Problème Identifié
Suite à l'audit CTO (AI-05), il a été déterminé que l'utilisation directe d'un LLM pour générer des décisions de trading dans un pipeline HFT (High-Frequency Trading) sur un environnement CPU-only créait :
1. **Un risque de latence inacceptable** (secondes vs millisecondes requises).
2. **Un risque de non-déterminisme**, incompatible avec l'entraînement du Reinforcement Learning (AI-04).

## 2. Repositionnement (Asynchronous Macro Reporting)
Les fichiers présents dans `src/aegis_trade/agents/` (ex: `council.py`, `synthesizer.py`, `runner.py`) **ne sont pas supprimés**. 
Ils sont repositionnés en tant qu'**outils de reporting asynchrone**. 
Ils ne font plus partie du chemin critique de décision d'ordre.

## 3. Nouvelle Architecture Déterministe
Le chemin décisionnel critique (Tick $\rightarrow$ Event $\rightarrow$ Vote $\rightarrow$ Order) est désormais géré par `src/aegis_trade/application/council/`, un moteur purement mathématique (VoteAggregator) intégrant les poids du Reinforcement Learning.
L'influence du LLM est déportée hors du temps réel (ex: extraction de règles dans la Knowledge Base, ou stub dans le `NewsAgent` qui sera peuplé par un cache asynchrone).
