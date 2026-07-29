# Spécification du Multi-Agent Council (Déterministe)

Le Conseil est un comité de 8 agents fonctionnels isolés, responsables d'une dimension spécifique du marché. Ils ne tradent pas ; ils **votent** (`BUY`, `SELL`, `WAIT`) avec un degré de `Confidence`.

## 1. Les Rôles (8 Agents)

1. **Trend Agent** : Analyse de la structure du marché à moyen terme (EMA/SMA).
2. **Momentum Agent** : Évaluation de la force immédiate du mouvement (RSI/MACD).
3. **Volatility Agent** : Détection des régimes d'expansion ou de contraction (ATR/Bollinger).
4. **Liquidity Agent** : Validation de la capacité à exécuter un ordre sans slippage (Volume/Spread).
5. **Pattern Agent** : Utilise la mémoire FAISS (`Success Memory`, `Failure Memory`).
6. **Portfolio Agent** : Diversification, exposition, et corrélation inter-actifs.
7. **Execution Agent** : Microstructure du routage d'ordre (Latence, API Status).
8. **News Agent** : Filtre macro-économique (LLM Asynchrone, actuellement Stubbé).

## 2. Protocole de Vote (Orchestrator & Aggregator)
- Chaque agent évalue le `MarketContext` et émet un `AgentVote` (Action + Confiance).
- Le **VoteAggregator** rassemble les votes en appliquant les poids générés par le **Reinforcement Learning** (`PolicyDecision.agent_weights`).
- Si aucun poids n'est défini (avant l'entraînement), les poids sont strictement **égaux (1/8 chacun)**.

## 3. Gestion des Désaccords (Conflict Resolver)
- Le **ConflictResolver** mesure le ratio entre le score de la minorité et de la majorité.
- Si le désaccord est supérieur à `0.80` (Incertitude forte), la taille de position est **divisée par 4**.
- Si le désaccord est supérieur à `0.95` (Incertitude critique), le trade est **abandonné** (VETO de conflit).

## 4. Intégration RL & Risk Manager
- La décision finale est sujette au seuil de confiance ajusté par le module de Reinforcement Learning (RL).
- Si le trade est validé par le conseil, un `OrderEvent` est généré.
- **Droit de Veto Absolu** : Le `GlobalRiskManager` du Portfolio Engine a le dernier mot (Drawdown max, exposition brute, concentration). Même si le conseil valide à 100%, le Risk Manager peut bloquer l'ordre.
