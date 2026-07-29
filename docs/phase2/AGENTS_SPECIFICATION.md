# Spécifications des Agents du Comité (Multi-Agent Council)

Chaque agent est une fonction spécialisée, déterministe ou prédictive, isolée et responsable d'une dimension spécifique du marché. Ils ne tradent pas ; ils **votent** (`BUY`, `SELL`, `WAIT`) avec un degré de `Confidence`.

## 1. Trend Agent
- **Responsable :** Analyse de la structure du marché à moyen terme.
- **Features surveillées :** EMA, MA, ADX, Structure des prix (Higher Highs, Lower Lows).
- **Sortie :** `[Vote, Confidence]`

## 2. Momentum Agent
- **Responsable :** Évaluation de la force immédiate du mouvement.
- **Features surveillées :** RSI, MACD, Momentum, ROC, CCI.
- **Sortie :** `[Vote, Confidence]`

## 3. Volatility Agent
- **Responsable :** Détection des régimes d'expansion ou de contraction.
- **Features surveillées :** ATR, Bandes de Bollinger, Volatility Regime (VIX proxy).
- **Sortie :** `[Vote, Confidence]`

## 4. Liquidity Agent
- **Responsable :** Validation de la capacité à exécuter un ordre sans slippage.
- **Features surveillées :** Volume, Spread, Slippage estimé, Profondeur du Carnet d'Ordres (Order Book).
- **Sortie :** `[Vote, Confidence]`

## 5. Pattern Agent
- **Responsable :** Projection prédictive et analyse vectorielle.
- **Technologies :** Kronos (Forecasting), Embedding FAISS.
- **Features surveillées :** Similarité de forme, Score d'échec/réussite historique.
- **Sortie :** `[Vote, Confidence]`

## 6. News Agent
- **Responsable :** Filtre macro-économique (Analyse asynchrone).
- **Technologies :** FinGPT, OpenBB.
- **Features surveillées :** Sentiment des news, Événements du calendrier économique.
- **Sortie :** `[Vote, Confidence]`

## 7. Portfolio Agent
- **Responsable :** Diversification et corrélation inter-actifs.
- **Features surveillées :** Corrélation avec les positions ouvertes, Exposition brute et nette.
- **Sortie :** `[Vote, Confidence]`

## 8. Execution Agent
- **Responsable :** Microstructure du routage d'ordre.
- **Features surveillées :** Broker API Status, Latence, Taux de "Fill" (exécution).
- **Sortie :** Recommande un type d'ordre (Market, Limit, TWAP).
