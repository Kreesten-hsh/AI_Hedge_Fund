# Matrice des Dépendances (Dependency Matrix)

| Repo / Package | Statut | Valeur | Fichiers d'implémentation réels | Modules utilisés |
|------|--------|--------|--------|------------------|
| python-deriv-api | Intégré | Broker Live | `infrastructure/paper/deriv_gateway.py` | `DerivGateway`, `LiveDerivGateway` |
| MetaTrader5 | Intégré | Broker Legacy | `providers/mt5_provider.py`, `providers/normalization.py` | `MT5Provider` |
| OpenBB | Intégré | Macro Data | `infrastructure/data/providers/openbb_provider.py` | `OpenBBDataProvider` |
| Qlib | Intégré | Feature Extr. | `providers/qlib_adapter.py`, `providers/qlib/*`, `application/strategy/ml_strategy.py` | `QlibAdapter`, `QlibDataset`, `QlibPredictor` |
| stable_baselines3 (FinRL) | Intégré | Reinforcement | `infrastructure/rl/sb3_policy_adapter.py`, `infrastructure/rl/policy_checkpoint_store.py` | `PPO`, `DummyVecEnv` |
| Kronos | Reporté | Forecasting | N/A (Matériel insuffisant) | Aucun |
| FinGPT | Abandonné | Raisonnement | N/A (Remplacé par Ollama local) | Aucun |
| lightweight-charts | Planifié | Dashboard | N/A (Attente Dashboard spec) | React integration, Canvas charting |
| TradingAgents | Abandonné | Architecture | N/A (Architecture custom) | Aucun |
| AutoHedge | Abandonné | Orchestration | N/A (Architecture custom) | Aucun |
| FinceptTerminal | Abandonné | UI/UX | N/A | Design inspiration only |
| Vibe-Trading | Abandonné | UI/UX | N/A | Design inspiration only |
| Zipline | Abandonné | N/A | N/A | Aucun |
| QuantLib | Abandonné | N/A | N/A | Aucun |
| AkShare | Abandonné | N/A | N/A | Aucun |
| daily_stock_analysis | Abandonné | N/A | N/A | Aucun |
