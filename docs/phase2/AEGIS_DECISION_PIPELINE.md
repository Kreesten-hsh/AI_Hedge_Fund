# Le Pipeline de Décision Aegis (Aegis Decision Pipeline)

> **Règle Fondamentale :** Ce pipeline est la constitution du système. Tout développement d'Aegis Quant OS doit s'y conformer. Le LLM n'intervient jamais dans le chemin critique temps réel.

## Architecture du Pipeline

```text
Market Tick
     ↓
Market Feature Extraction (Volatilité, Liquidité, etc.)
     ↓
Indicators (RSI, ATR, MACD, etc.)
     ↓
Pattern Extraction
     ↓
Experience Embedding (Génération du Vecteur d'État)
     ↓
Similarity Search (Top 200 via FAISS)
     ↓
Success Memory Score
     ↓
Failure Memory Score
     ↓
Council Input (Appel au Comité Multi-Agents)
     ├─ Trend Agent
     ├─ Momentum Agent
     ├─ Volatility Agent
     ├─ Liquidity Agent
     ├─ Pattern Agent
     ├─ News Agent
     ├─ Portfolio Agent
     └─ Execution Agent
     ↓
Voting (Consensus et Agrégation des Scores)
     ↓
Risk Manager (Validation Déterministe et VETO)
     ↓
Position Sizing (Calcul de la Taille de Position)
     ↓
Broker (Routage d'Ordre via vn.py)
     ↓
Trade (Exécution)
     ↓
Monitoring (Suivi Live du Drawdown et PnL)
     ↓
Learning (Post-Trade Analysis)
     ↓
Memory (Stockage dans FAISS)
```
