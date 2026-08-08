# Matrice des Dépendances (Dependency Matrix)

> **Document réécrit le 2026-07-31** sur la base de `docs/refont/AUDIT_COMPLET_2026-07-31.md` (verdict **NO-GO**).
> La version précédente marquait 5 paquets « Intégré ». Mesure par grep : « présent dans le dépôt »
> et « importé quelque part » ne valent pas « intégré au chemin de production ».

> **Vocabulaire de statut, identique à `PHASE2_ROADMAP.md` et `PHASE2_BACKLOG.md` :**
> `[ÉCRIT-NON-CÂBLÉ]` code d'adaptation présent, **zéro site d'appel en production** —
> `[CÂBLÉ-NON-VALIDÉ]` réellement appelé en production, aucune validation franchie —
> `[FAÇADE]` l'adaptateur retourne une constante, un mock ou une donnée aléatoire —
> `[VENDORÉ]` code amont copié dans le dépôt (question de licence, pas d'intégration) —
> `[INSPIRATION]` décision explicite : jamais intégré, sert de référence de conception —
> `[ABANDONNÉ]` évalué puis écarté, rien dans le dépôt.

## Ce que cette matrice sert à décider

Savoir **quelles dépendances doivent fonctionner pour que la démo réelle sur compte Deriv tourne**, et
lesquelles ne sont sur le chemin critique d'aucun objectif. Une ligne « Intégré » qui n'a pas de site
d'appel induit en erreur exactement là où ça compte : au moment de brancher de l'argent.

## Sur le chemin critique de la démo réelle

| Paquet | Statut mesuré | Rôle visé | Fichiers réels | Preuve du statut |
|---|---|---|---|---|
| python-deriv-api | `[FAÇADE]` | Broker démo puis réel | `infrastructure/paper/deriv_gateway.py` (`DerivGateway`, `LiveDerivGateway`) | **Aucun abonnement WebSocket de prix dans le dépôt.** Le remplissage est la constante `fill_price = Decimal("100.0")` et `latency_ms = 50.0` (`application/council/orchestrator.py:87-88`). Le jeton d'accès est une valeur factice, référencée par nom de clé dans l'audit §2 — pas un secret réel, mais pas une connexion non plus. |
| vn.py | `[CÂBLÉ-NON-VALIDÉ]` | Routage d'ordres | `providers/vnpy_adapter.py`, `infrastructure/live/vnpy/execution.py` | **Ligne absente de la version précédente de cette matrice** alors que ce code route des ordres. `on_trade` a un corps `pass` (`infrastructure/live/vnpy/execution.py:69`) : aucun retour d'exécution ne remonte. `Exchange.SMART` en dur, `gateway_name = exchange  # simplification` (`providers/vnpy_adapter.py:69,82`), `return "mock_id"` (`infrastructure/live/vnpy/execution.py:46`). Contourne le `RiskEngine` sur 3 chemins (Lot 1). |
| MetaTrader5 | `[ÉCRIT-NON-CÂBLÉ]` | Broker legacy | `providers/mt5_provider.py`, `providers/normalization.py` | `# type: ignore` nu en tête de fichier (`providers/mt5_provider.py:4`). Aucun chemin de production n'instancie `MT5Provider`. |
| OpenBB | `[ÉCRIT-NON-CÂBLÉ]` | Données macro | `infrastructure/data/providers/openbb_provider.py` | Restriction non documentée dans le contrat du port (`openbb_provider.py:43,100,103,106`). Zéro site d'appel en production. |

## Modélisation et apprentissage

| Paquet | Statut mesuré | Rôle visé | Fichiers réels | Preuve du statut |
|---|---|---|---|---|
| Qlib | `[ÉCRIT-NON-CÂBLÉ]` | Consommation du `FeatureStore` | `providers/qlib_adapter.py`, `providers/qlib/*`, `application/strategy/ml_strategy.py` | Deux `DatasetBuilder` divergents (`providers/qlib/dataset_builder.py:26`, `dataset/builder.py:8`). `ml_strategy.py` importe des classes concrètes au lieu des ports. Aucun cycle de production n'appelle `QlibPredictor`. La loi « Qlib ne calcule jamais d'indicateurs » est respectée à la lettre, mais 4 implémentations d'ATR divergentes coexistent en amont (Lot 3). |
| stable_baselines3 (FinRL) | `[ÉCRIT-NON-CÂBLÉ]` | Politique par renforcement | `infrastructure/rl/sb3_policy_adapter.py`, `infrastructure/rl/policy_checkpoint_store.py` | `PolicyTrainer(`, `PolicyEvaluator(`, `ValidationRunner(` : **0 site d'appel** hors définition et tests. L'observation réellement passée en production est `np.zeros(30)` (`application/council/orchestrator.py:97`) — un vecteur nul, pas un état de marché. `stable-baselines3`, `finrl`, `torch` et `gymnasium` sont absents de `pyproject.toml` (7 dépendances omises, Lot 5). Aucun ADR ne couvre ce choix. |
| Kronos (`NeoQuasar/Kronos-mini`) | `[FAÇADE]` + `[VENDORÉ]` | Prévision | `providers/kronos_adapter.py`, `providers/kronos/shiyu_model/` (1 532 lignes amont) | La version précédente disait « Reporté — N/A (Matériel insuffisant) — Aucun ». **Mesure : le code est dans le dépôt et il tourne.** `kronos_adapter.py:40-41,63-71` prédit sur `np.random.randn` : le modèle infère sur du bruit, pas sur des prix. **Aucun fichier LICENSE pour ces 1 532 lignes vendorées** (Lot 5). Couverture `kronos.py` 8 %, `kronos/trainer.py` 16 %. À ne pas confondre avec `amazon/chronos-t5-mini` : ce n'est pas le même modèle. Empreinte mesurée ~917 MB (`RESEARCH_LOGBOOK.md`, entrée de gouvernance « Intégration Kronos (Sprint AI-08) »), pas « <300MB ». |
| Ollama (raisonnement local) | `[ÉCRIT-NON-CÂBLÉ]` | Raisonnement des agents | `infrastructure/reasoning/ollama_reasoner.py` | `OllamaReasoner` existe. **La production ne le câble pas :** `api/deps.py:53` injecte `MockReasoner()`. Le port `domain/reasoning.py:125` est par ailleurs importé depuis `infrastructure/` par `application/council/agents/pattern_agent.py:2` (violation de frontière, Lot 3). |
| FinGPT | `[ABANDONNÉ]` | Raisonnement | Aucun | Décision consignée dans `ADR-002`, qui déclare le remplacement par Ollama. **`ADR-002` n'est pas marqué `Superseded`** alors que la production tourne sur `MockReasoner()` : l'ADR décrit un état qui n'existe pas (Lot 5). |

## Références de conception — jamais destinées à être intégrées

Ces entrées ne sont **pas des lacunes**. Ce sont des décisions d'architecture explicites : l'architecture
du comité et de l'orchestration est écrite maison, en s'inspirant de ces dépôts. Les marquer
« Abandonné » laissait croire à un échec d'intégration ; il n'y a jamais eu d'intégration prévue.

| Source | Statut | Ce qui en a été repris |
|---|---|---|
| TradingAgents | `[INSPIRATION]` | Modèle de comité multi-agents avec vote. Implémentation maison : `IVotingAgent`, `MultiAgentCouncil`, `VoteAggregator`, `ConflictResolver`. Cohérent avec `PROJECT_PHILOSOPHY.md` (ligne TradingAgents du tableau écosystème). |
| AutoHedge | `[INSPIRATION]` | Modèle d'orchestration de bout en bout. Implémentation maison : `PaperTradingOrchestrator`. |
| FinceptTerminal | `[INSPIRATION]` | Références UI/UX du dashboard. |
| Vibe-Trading | `[INSPIRATION]` | Références UI/UX du dashboard. |

## Planifié

| Paquet | Statut | Rôle visé | Blocage réel |
|---|---|---|---|
| lightweight-charts | `[ ]` | Graphiques du dashboard | Rien à tracer tant qu'aucun tick réel n'entre (Lot 2). Le frontend n'a par ailleurs aucun test et code en dur `ws://127.0.0.1:8000` sans `wss` (Lot 6). |

## Évalués puis écartés — rien dans le dépôt

Zipline, QuantLib, AkShare, daily_stock_analysis : `[ABANDONNÉ]`, aucun fichier, aucun import.

## Ce que cette matrice ne promet pas

Elle ne dit pas qu'un paquet `[CÂBLÉ-NON-VALIDÉ]` fonctionne — seulement qu'il est atteint par le
chemin d'exécution. Elle ne dit pas qu'un paquet `[ÉCRIT-NON-CÂBLÉ]` sera câblé : cette décision
appartient aux lots du plan de correction, non exécutés à ce jour. **Aucune dépendance de ce dépôt
n'est `[VALIDÉ]` au 2026-07-31.**
