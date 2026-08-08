# Feature Engineering (Paramètres d'État du Marché)

> Ce document liste de manière exhaustive les paramètres qui représentent un état de marché. C'est l'encodage de ces paramètres qui formera l'**Embedding** injecté dans les bases FAISS.

## Liste des Paramètres Extraits

### 1. Market Data (Données Brutes)
- `Price` (Bid/Ask actuel)
- `OHLC` (Open, High, Low, Close des N dernières périodes)
- `Spread` (Différentiel bid-ask en pips ou points)
- `Volume` (Volume échangé sur la bougie ou le tick)
- `Order Book Imbalance` (Pression acheteuse vs vendeuse)

### 2. Time & Session (Temps et Contexte)
- `Time of Day` (Heure UTC, minute)
- `Session` (London, NY, Tokyo, Asian Box)
- `Time since last economic event` (Minutes)
- `Economic Calendar Flag` (Présence d'une annonce NFP, FOMC dans les 60 min)

### 3. Oscillators & Trend (Analyse Technique)
- `EMA` (Distance du prix par rapport à EMA20, EMA50)
- `RSI` (Valeur 14 périodes)
- `MACD` (Histogramme et Signal)
- `Momentum` (Rate of Change - ROC)
- `VWAP` (Écart au Volume-Weighted Average Price)

### 4. Volatility & Liquidity (Risque du Marché)
- `ATR` (Average True Range)
- `Volatility State` (Écart-type des rendements glissants)
- `Liquidity Density` (Densité du carnet autour du prix)

### 5. Portfolio Correlation (Risque Systémique)
- `Correlation_Active_Positions` (Corrélation de l'actif avec le portefeuille actuel)

## Processus de Transformation
Toutes ces valeurs sont **normalisées** (Z-Score ou Min-Max scaling) avant d'être concaténées en un vecteur `V` unique. Ce vecteur représente l'Expérience.
