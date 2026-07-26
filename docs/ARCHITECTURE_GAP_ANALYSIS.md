# Analyse des Écarts (Architecture Gap Analysis)

Ce document met en lumière l'état actuel de la base de code (`src/aegis_trade/`) par rapport à la vision cible définie dans `SYSTEM_ARCHITECTURE.md`. Son but est d'identifier de manière exhaustive les composants embryonnaires ou manquants afin d'alimenter la Roadmap et le Backlog.

## 1. Moteurs Fondamentaux (Core Engines)

### État Actuel
- **Domain & Events** : Le modèle de domaine (Trade, Position, Signal) et le bus d'événements mémoire (`EventBus`) sont implémentés de façon propre et respectent le DDD.
- **AI Council** : Architecture de base en place. Le `AgentRunner` utilise la Factory LLM avec un cache fonctionnel.
- **Portfolio & Risk Engine** : Logiques basiques (sizing de position, vérification de drawdown) présentes dans `portfolio.py` et `global_risk.py`.

### Écarts Identifiés (Gaps)
- ❌ **Execution Engine Absent** : Le composant qui transforme un ordre du Risk Engine en transaction réelle (incluant le routage, la gestion du slippage et les algorithmes VWAP/TWAP) n'est pas encore structuré.
- ❌ **Feature Engine Non-Standardisé** : Les stratégies calculent actuellement leurs indicateurs manuellement (`rsi_strategy.py`). Il manque un moteur centralisé d'extraction de *features* (alimenté par Qlib) dont l'IA dépendra.

## 2. Infrastructure et Données

### État Actuel
- **LLM Infrastructure** : Parfaitement opérationnelle (Mission INFRA-01). Isolation via `llm.yaml`, validation, logging JSON, et Factory.
- **Dataset / Storage** : Un moteur rudimentaire de `DatasetEngine` gère des fichiers de données statiques.

### Écarts Identifiés (Gaps)
- ❌ **Data Pipeline Absent** : Aucune orchestration pour l'ingestion quotidienne/temps réel. Le projet ne télécharge pas automatiquement ses données de marché. Il manque une architecture solide de *Data Lake* temporel (Parquet ou TimescaleDB).

## 3. Fournisseurs (Providers)

### État Actuel
- **LLMs** : Support natif d'Ollama (implémenté).
- **Qlib & vn.py** : Des *adapters* (`qlib_adapter.py`, `vnpy_adapter.py`) existent en l'état, mais ne sont ni connectés à un *Data Pipeline* vivant, ni utilisés en production.

### Écarts Identifiés (Gaps)
- ❌ **Data Providers** : L'intégration officielle avec OpenBB ou Polygon pour le Market Data est absente.
- ❌ **Brokers** : vn.py n'est pas encore pleinement câblé avec un Execution Engine capable de router en live.

## 4. Supervision (Dashboard)

### État Actuel
- **Aucun** : L'interaction se fait via les logs terminaux et des scripts Python de lancement (`run_ai_backtest.py`).

### Écarts Identifiés (Gaps)
- ❌ **Dashboard Totalement Manquant** : Il n'y a ni base de données de journalisation persistante (pour les trades), ni API (FastAPI), ni interface front-end (React/Streamlit) permettant le contrôle visuel du système, le suivi des métriques de performance, ou le déclenchement du Kill Switch.

---

## Conclusion de l'Analyse

Le noyau (Core/Domain) d'Aegis Quant OS est solide, agnostique et testé. Le gap principal réside aujourd'hui dans l'ingestion de données (Data Pipeline) et la supervision visuelle (Dashboard). Ces lacunes bloquent toute mise en production (Paper Trading ou Live) et dictent logiquement les prochaines étapes du développement.
