# DECISION MATRIX: BUILD VS REUSE (GOUVERNANCE AEGIS QUANT OS)

- **Date** : 2026-08-07
- **Auteur** : Senior Principal Engineer & Product Architect
- **Règle Fondamentale** : Interdiction de recoder tout composant existant et maintenu par la communauté open-source (indicateurs, moteurs de backtest, pipelines ML, connecteurs d'exécution).

---

## 1. Moteurs & Librairies Open-Source Retenus

| Composant Système | Solution Code en Interne (Interdit) | Solution OSS Sélectionnée (Recommandée) | Rationale & Justification Technique |
| :--- | :--- | :--- | :--- |
| **Indicateurs Techniques** | Scripts custom pandas/math | **`pandas-ta-classic` / `TA-Lib`** | 193+ indicateurs optimisés C/C++, aucune erreur d'implémentation mathématique. |
| **Backtesting Vectorisé Fast** | Loops Python custom | **`vectorbt` / `backtesting.py`** | Exécution via Numba/NumPy $100\times$ plus rapide, gestion d'ordres et métriques avancées native. |
| **Pipeline Machine Learning Quant** | Script custom OLS / Sklearn | **`Microsoft Qlib` / `LightGBM`** | Format de données mémoire ultra-rapide, standardisation cross-sectionnelle, modèles GBDT/GRU/Transformers natifs. |
| **Bot d'Exécution Crypto 24/7** | WebSockets custom CCXT | **`Freqtrade`** | Bot de production clé en main, gestion des limites d'API, stop-loss, trailing-stop, Telegram control. |
| **Moteur Événementiel Multi-Actifs** | Moteur de simulation custom | **`QuantConnect LEAN`** | Modélisation exacte du slippage, de la liquidité, de la marge et des frais d'exécution de courtier. |

---

## 2. Découpage Architectural Cible

1. **Layer 1 - Data & Ingestion** : Téléchargement et structuration via `yfinance`, `ccxt`, ou dataset formaté `Qlib`.
2. **Layer 2 - Feature Engineering** : Génération automatique de 100+ indicateurs via `pandas-ta-classic`.
3. **Layer 3 - Model & Alpha Pipeline** : Modèles `LightGBM` / `VectorBT` avec validation Walk-Forward strict.
4. **Layer 4 - Risk & Portfolio Management** : Dimensionnement de position (Kelly / Volatility Parity), Stop-Loss / Take-Profit dynamiques.
5. **Layer 5 - Execution Layer** : `Freqtrade` (Crypto) ou `Interactive Brokers API` / `Deriv WS` (Forex/Commodities).
