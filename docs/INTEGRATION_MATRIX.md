# Matrice de Délégation Architecturale

Conformément à la nouvelle vision d'Aegis Quant OS en tant que **Méta-Orchestrateur Institutionnel**, ce document cartographie les dépôts open-source évalués et définit précisément leur rôle et leur mode d'intégration via le **Pattern Adaptateur**. Le code métier propriétaire d'Aegis est réservé à l'Orchestrateur, la validation d'Alpha, la gouvernance IA et le risque.

| Dépôt / Framework | Statut | Rôle dans Aegis Quant OS | Interface de Connexion (Adaptateur) |
| :--- | :--- | :--- | :--- |
| **OpenBB** | 🟢 **Adopté** | Fournisseur de contexte macro-économique, données fondamentales et sentiment. | `aegis_trade.providers.openbb_adapter` encapsulant les DataFrames OpenBB en entités Aegis (`MarketBar`, `Dataset`). |
| **vn.py** (vnpy) | 🟢 **Adopté** | Moteur d'exécution Live et connectivité Broker (CTP, Binance, IB, MT5). | `ExecutionGateway` (Interface) -> `VnPyAdapter`. Les `OrderEvent` d'Aegis sont traduits en ordres vn.py. |
| **qlib** (Microsoft) | 🟡 **Adapté** | Pipeline d'entraînement ML vectorisé et framework de Feature Engineering à grande échelle. | Utilisation du module `qlib.data` wrappé derrière `aegis_trade.dataset.repository` pour le traitement lourd de features, sans utiliser son backtester. |
| **FinGPT** | 🟡 **Adapté** | Générateur de features de sentiment et raisonnement financier NLP. | API REST/locale wrappée derrière une interface `NLPFeatureProvider` alimentant le `Research Analyst`. |
| **akshare** | 🟡 **Adapté** | Fournisseur de données alternatives et marchés asiatiques (A-Shares). | `aegis_trade.providers.akshare_adapter` utilisé comme alternative ou complément à OpenBB. |
| **TradingAgents** | 🔵 **Inspiré** | Architecture conceptuelle pour les agents LLM. | Le concept est conservé, mais la logique (Research Council) est 100% réécrite dans Aegis pour garantir une gouvernance de risque stricte. |
| **Zipline** | 🔴 **Ignoré** | Moteur de backtest obsolète. | Non retenu. Aegis utilise son propre `aegis_trade.engine` événementiel et léger, déjà validé. |
| **AutoHedge** | 🔴 **Ignoré** | Monolithe boîte noire. | Ne respecte pas notre séparation stricte (Research / Portfolio / Execution). |
| **Vibe-Trading** | 🔴 **Ignoré** | Projet retail/récréatif. | Manque de rigueur quantitative (absence d'IC, Holdout, prise en compte des coûts). |
| **FinceptTerminal** | 🔴 **Ignoré** | Interface graphique (UI). | Aegis est conçu comme un système backend/headless institutionnel piloté par API et événements. |
| **daily_stock_analysis**| 🔴 **Ignoré** | Scripts d'analyse retail non systémiques. | Incompatible avec une approche quantitative institutionnelle. |
| **awesome-quant** | ⚪ **Ignoré** | Index de ressources. | Conservé uniquement comme référence bibliographique. |

## Règle d'Intégration (Architecture Hexagonale)
**Interdiction formelle** de fusionner du code de ces dépôts dans `src/aegis_trade`.
Toute intégration passe par l'implémentation d'un port/interface défini dans le domaine d'Aegis Quant OS, afin que l'infrastructure sous-jacente puisse être remplacée sans impact sur la logique de gouvernance.
