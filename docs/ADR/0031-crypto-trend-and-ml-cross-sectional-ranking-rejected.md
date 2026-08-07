# ADR 0031 — Réfutation Émpirique du Trend-Following Crypto 24/7 & du Ranking IA Cross-Sectionnel (OPTION A & B)

- **Statut** : REJETÉ / CLÔTURÉ (0/2 Approches Validées — Réfutation du Suivi de Tendance Univarié Crypto et du Ranking ML Multi-Actifs)
- **Date** : 2026-08-07
- **Contexte technique** : `user_data/strategies/AegisCryptoTrendStrategy.py`, `scripts/run_crypto_vectorbt_backtest.py`, `scripts/train_multi_asset_lightgbm.py`, `docs/research/LIGHTGBM_MULTI_ASSET_REPORT.md`
- **Dépend de** : ADR 0021 (péage et coûts), ADR 0030 (Refutation H4/D1)
- **Résout** : Évaluation des frameworks Open-Source (Freqtrade, VectorBT, LightGBM) en mode directionnel univarié et cross-sectionnel.

---

## 1. Contexte et Hypothèses Évaluées

À la suite de la refonte des infrastructures (matrice `BUILD_VS_REUSE.md`), deux approches basées sur l'écosystème Open-Source ont été implémentées et soumises aux bancs d'essai Out-Of-Sample :
1. **Option A (Freqtrade / VectorBT - Bot Crypto 24/7)** : Stratégie de suivi de tendance et de breakout de volatilité (`EMA 20/50/200`, `Bollinger Bands`, `ADX > 20`, `RSI`) avec Stop-Loss fixe ($-2.5\%$) et Trailing-Stop ($+1.5\%$) sur bougies 15m/1h.
2. **Option B (LightGBM / GBDT Cross-Sectional Ranking)** : Modèle de Machine Learning entraîné sur panier multi-actifs (`BTC-USD`, `ETH-USD`, `SOL-USD`, `XAUUSD`, `EURUSD`) avec normalisation des facteurs et prédiction du classement relatif à 5 jours.

---

## 2. Résultats Émpiriques et Bilan Quantitatif

### A. Option A — Bot Crypto Trend-Following 24/7 (Frais 10 bps Déduits)
Backtest vectorisé sur 2 ans d'historique (15m/1h) :

| Actif Crypto | Nombre de Trades | P&L Net Cumulé | Win Rate (%) | Ratio Sharpe | Max Drawdown (%) | Statut |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **BTC-USD** | 167 | **`-22.47%`** | 32.3% | -2.26 | **`-31.91%`** | ❌ **RÉFUTÉ** |
| **ETH-USD** | 137 | **`-6.36%`** | 32.1% | -0.06 | **`-23.36%`** | ❌ **RÉFUTÉ** |
| **SOL-USD** | 147 | **`-1.63%`** | 32.7% | +0.29 | **`-27.00%`** | ❌ **RÉFUTÉ** |

- **Analyse du Rejet** : Le taux de victoire de $32.3\%$ démontre que la tendance directionnelle univariée en timeframe court est soumise à des fausses cassures répétées (*whipsaws*). Le péage d'exécution de $10\text{ bps}$ dévorant chaque trade détruit le P&L.

### B. Option B — Moteur IA LightGBM Cross-Sectional Ranking
Évaluation Out-Of-Sample (Split Chronologique 70/30) :

- **Spearman Rank IC Out-Of-Sample** : **`-0.0087`** (Quasiment $0.00$)
- **Information Ratio (IR)** : **`-0.12`**
- **Analyse du Rejet** : L'utilisation de facteurs issus d'indicateurs techniques univariés classiques (RSI, EMA, Volatilité) au sein d'un modèle ML ne procure aucun pouvoir prédictif sur les rendements relatifs à 5 jours.

---

## 3. Décision d'Architecture et Orientations Futures

1. **Réfutation Définitive du Trading Directionnel Univarié sur Indicateurs** :
   - Les indicateurs techniques classiques sur séries temporelles de prix individuelles sont à efficience de marché complète.
2. **Conservation des Fichiers comme Preuve de Réfutation** :
   - [user_data/strategies/AegisCryptoTrendStrategy.py](file:///mnt/WindowsData/AI_Hedge_Fund/user_data/strategies/AegisCryptoTrendStrategy.py)
   - [scripts/run_crypto_vectorbt_backtest.py](file:///mnt/WindowsData/AI_Hedge_Fund/scripts/run_crypto_vectorbt_backtest.py)
   - [scripts/train_multi_asset_lightgbm.py](file:///mnt/WindowsData/AI_Hedge_Fund/scripts/train_multi_asset_lightgbm.py)
3. **Pivot Vers des Stratégies Rendement Structurel & Delta-Neutre** :
   - Redirection de la recherche vers les approches sans prédiction directionnelle (*Funding Rate Arbitrage Delta-Neutre*, *Pairs Trading Cointégré*).
