# PLAN DE CORRECTION — Aegis Quant OS

**Date** : 2026-07-31
**Branche** : `claude-code-takeover`
**Source** : `docs/refont/AUDIT_COMPLET_2026-07-31.md` (verdict NO-GO, 21 bloquants P0–P3)
**Statut** : **proposé, non exécuté.** Aucun lot ne démarre sans validation explicite.

> Principe directeur : on ne rajoute aucune fonctionnalité tant que le système ne sait pas
> **échouer bruyamment**. Un `NotImplementedError` est supérieur à un `passed=True` codé en dur.
> Un `TypeError` visible est supérieur à une tâche `asyncio` qui meurt en silence.

---

## ORDRE NON NÉGOCIABLE (Mis à jour — Directive CTO 2026-08-02)

```
Lot 0 ✅ ──► Lot 1 ✅ ──► Lot 2 (Complété: Sourcing Réel) ──► Lot 4 (Validateurs Réels)
                         │
                         └──► Intégration Qlib/Kronos Réelle (Phases 3-6)
                                   │
                                   ▼
                         [Démo Fonctionnelle]
                                   │
                                   ├──► Lot 3 (Souveraineté Numérique) — MANDAT AVANT AI-07b LIVE REAL MONEY
                                   ├──► Lot 5 Complet (Docker non-root, Upgrade mlflow, Clean deps, LICENSE)
                                   └──► Lot 6 (Dette résiduelle)
```

Règles de séquencement impératives :

1. **Lot 0 et Lot 1 : TERMINÉS.** Les fondations (Gates & RiskEngine Authority) sont scellées et validées par tests.
2. **Sourcing de Données Réelles (Lot 2 complet) + Validateurs Réels (Lot 4) avant Intégration ML.** Aucun modèle (Qlib/LightGBM ou Kronos) n'est entraîné ni validé sans calculs réels sur de vraies données (Deriv WS / OpenBB).
3. **Engagements explicites sur Lot 3 et Lot 5 :**
   - **Lot 3 (Souveraineté numérique & déduplication)** : Reporté temporairement après la démo fonctionnelle. **RAPPEL : Le Lot 3 est un prérequis OBLIGATOIRE avant toute ouverture de la phase AI-07b (trading réel avec argent réel).**
   - **Lot 5 complet (Upgrade `mlflow`, Docker, deps, LICENSE)** : Le passage par LightGBM-direct (Phases 3-6) est un contournement temporaire dû à l'incompatibilité de `mlflow 1.27.0`. **Le Lot 5 est OBLIGATOIRE avant de pouvoir sortir du contournement LightGBM-direct et réactiver le `qlib.init()` standard.**

---

## LOT 0 — RESTAURER LES GATES

Objectif : rendre le projet **mesurable**. Zéro correction fonctionnelle dans ce lot.

| Action | Cible | Bloquants couverts |
|---|---|---|
| Créer 36 `__init__.py` manquants | tous les sous-paquets sauf `domain`, `engine`, `core`, `utils`, `dataset` (déjà présents) | 10 |
| Réécrire 7 imports `src.…` en `aegis_trade.…` | 4 fichiers de tests RL | 10 |
| Ajouter `pytest-asyncio` + un `conftest.py` racine | `pyproject.toml`, `tests/conftest.py` | 9 |
| Corriger `explicit_package_bases` / `mypy_path` | `pyproject.toml` | 7 |

**Critère de sortie — mesurable, pas déclaratif :**

- `pytest -v` **collecte** 265 tests (0 erreur de collection). Les 5 échecs connus peuvent rester
  rouges : ils sont réels et seront traités au Lot 1.
- `mypy --strict src/` produit un **compte stable et honnête** (~929 erreurs attendues).
  On ne vise pas zéro ici : on établit la ligne de base contre laquelle les lots suivants se mesurent.
- `ruff check` produit un compte stable (~329).

Ce lot ne touche à **aucun** fichier de `engine/`, `domain/` ni `providers/`.

---

## LOT 1 — REFERMER L'AUTORITÉ DU RISKENGINE

Objectif : rendre **structurellement impossible** l'acheminement d'un ordre sans risk check.
Couvre les 6 bloquants P0.

| Action | Cible |
|---|---|
| Un **point d'entrée unique** pour tout ordre. Les 4 chemins actuels convergent vers lui. Suppression des `submit_order` / `send_order` directs | `api/routers/positions.py:43`, `providers/vnpy_adapter.py:52,57,79`, `infrastructure/live/vnpy/execution.py:14,47` |
| Corriger la signature de l'appel : 3 arguments (`order`, `portfolio`, `latest_prices`) | `application/council/orchestrator.py:132-134` |
| Déplacer l'appel **à l'intérieur** du `try/except`, et échouer bruyamment (log + arrêt de la tâche) au lieu de mourir en silence | `application/council/orchestrator.py:95-134` |
| Résoudre `IPaperBroker` (import réel ou `TYPE_CHECKING` + `from __future__ import annotations`), typer le retour autrement que `dict` | `engine/global_risk.py:29` |
| Remplacer `MagicMock(spec=…)` par un double qui **vérifie la signature** (`autospec=True` ou double explicite) | `tests/application/paper_trading/test_orchestrator_council_integration.py:30-50` |
| Auth locale obligatoire sur tous les POST **et** sur le WebSocket ; borner `topic` à une liste blanche | `api/main.py`, `api/ws/manager.py:37-45` |
| `allow_origins` explicite (pas `["*"]` avec `allow_credentials=True`) | `api/main.py:16-19` |
| `i_understand_this_is_real_money` dérivé d'un consentement réel, jamais littéral `True` | `api/deps.py:43` |
| Tests d'API **depuis zéro**, dont un test qui prouve qu'aucun chemin ne peut soumettre un ordre sans check | `tests/api/` (inexistant aujourd'hui) |
| Corriger les 3 échecs `Can't instantiate abstract class PaperBroker` et l'échec `expected call not found` | `tests/` + `PaperBroker` |

**Critère de sortie :** un test paramétré qui, pour chacun des 4 anciens chemins, prouve que l'ordre
est refusé si le RiskEngine refuse. `pytest -v` intégralement vert. Zéro `F821` dans `src/`.

---

## LOT 2 — DONNÉES RÉELLES ENTRANTES

Objectif : que le système voie de vrais prix et de vrais fills.

| Action | Cible |
|---|---|
| Créer `DerivMarketGateway` : abonnement WebSocket aux ticks, port dédié côté domaine | `providers/deriv/` (aucun subscribe/tick/quote aujourd'hui) |
| Supprimer le fill constant : prix de fill issu de la réponse broker | `providers/deriv/…:87 fill_price = Decimal("100.0")`, `:88 latency_ms = 50.0` |
| Supprimer `risk_decision="APPROVED"` codé en dur | `…:128` |
| Implémenter `on_trade` : les fills live alimentent le Portfolio | `infrastructure/live/vnpy/execution.py:69` (corps `pass`) |
| Conserver le snapshot et calculer un **drawdown réel** — condition d'existence du kill switch | `application/council/orchestrator.py:169-184` (`:172,173,184`) |
| Réparer **ou supprimer** `run_live_paper_trading.py`. Un script mort à l'import ne reste pas dans le dépôt | `scripts/run_live_paper_trading.py:9-12,44-49,63-68` |
| Remplacer les features placeholders par le `FeatureStore` réel ; aligner les clés attendues par les 8 agents | `orchestrator.py`, `agents/*.py` (§4.3 de l'audit) |

**Critère de sortie :** en démo, un tick réel produit un vote non nul d'au moins un agent, et le
drawdown affiché varie. Le kill switch se déclenche sur un test d'injection de drawdown > 5 %.

---

## LOT 3 — SOUVERAINETÉ NUMÉRIQUE : UNE SEULE IMPLÉMENTATION PAR GRANDEUR

Objectif : que le kill switch et le tableau de bord parlent de la même somme d'argent.

| Grandeur | Implémentations actuelles | Cible |
|---|---|---|
| Indicateurs / ATR | 4 impl., 3 ATR divergents : `utils/math.py:66-135`, `engine/strategy.py:118-145`, `application/reflection/extractor.py:54-101`, `infrastructure/features/technical_extractor.py:100-140` | une seule, dans le `FeatureEngine` |
| PnL réalisé | `engine/portfolio.py:92-93`, `engine/backtester.py:180-188`, `application/monitoring/engine.py:126-129` | `engine/portfolio.py` fait autorité |
| Equity | `engine/portfolio.py:165`, `application/monitoring/engine.py:100` | idem |
| Annualisation | `engine/portfolio.py:227`, `engine/performance.py:70,74` | `engine/performance.py` fait autorité |
| Verdict → ordre | `application/council/orchestrator.py:72-91`, `application/validation/council_adapter.py:82-95` | un seul convertisseur |
| `DatasetBuilder` | `providers/qlib/dataset_builder.py:26`, `dataset/builder.py:8` | un seul |

Plus, dans le même lot, les violations de dépendance :

- `domain/council.py:5` importe `engine.portfolio.Portfolio` (usage `:35`) — seule brèche de la pureté du domaine.
- 5 axes inversés : `engine → agents`, `engine → infrastructure`, `core → infrastructure`,
  `infrastructure → application`, `infrastructure → engine`.
- `application/strategy/ml_strategy.py` importe les classes concrètes `QlibPredictor` / `DatasetBuilder`.
- `pattern_agent.py:2` importe le port depuis `infrastructure/` alors que `domain/reasoning.py:125` le déclare.

**Critère de sortie :** un test de non-régression numérique par grandeur (mêmes entrées → même sortie,
quel que soit l'appelant). `architecture-guardian` repasse sans violation d'axe.

---

## LOT 4 — PIPELINE SCIENTIFIQUE RÉEL

Objectif : que le mot « validé » redevienne vrai. Couvre P2.

| Action | Cible |
|---|---|
| Les 6 validateurs **calculent réellement**, ou lèvent `NotImplementedError`. Un `passed=True` codé en dur est pire que rien : il ment au gate | `hold_out_validator.py:42-48`, `walk_forward_validator.py:21-26`, `monte_carlo_validator.py:22-27`, `benchmark_validator.py:21-26`, `multi_validators.py:21-26,37-42` |
| Exécuter le `Backtester` construit à `hold_out_validator.py:32` et jamais lancé | idem |
| Traçabilité réelle : `git_version` depuis `git rev-parse`, `data_hash` depuis un hash du dataset | `validation_runner.py:57,60` |
| Aligner les seuils code/doc : `benchmark_gate.py:14-15` (`0.85`/`2.0`) contre `VALIDATION_PIPELINE_REPORT.md:16` (`0.55`/`1.2`). **Décider lequel fait foi et documenter la décision en ADR** | `engine/benchmark_gate.py`, doc |
| Décider de Qlib : soit `import qlib` réel consommant le `FeatureStore`, soit suppression de la façade (`LightGBMModelMock`, `mock_loss`, `bootstrap.py:17-18`) | `providers/qlib/` |
| Décider de Kronos : brancher un vrai `data_provider` (`kronos_adapter.py:40-41,63-71` prédit sur `np.random.randn`) ou marquer le module explicitement inactif | `providers/kronos/` |
| Remplacer `MockReasoner()` par `OllamaReasoner` en production, ou assumer le mock par configuration explicite | `api/deps.py:53` |
| Entrée RL réelle au lieu de `np.zeros(30)` | `orchestrator.py:97` |

**Critère de sortie :** un rapport de validation dont les métriques proviennent d'un backtest exécuté
sur des données réelles, avec `git_version` et `data_hash` vérifiables. **Un rejet propre est un succès de ce lot.**

---

## LOT 5 — DÉPÔT, SUPPLY CHAIN, DOCUMENTATION

| Action | Cible |
|---|---|
| Ajouter le LICENSE amont de Kronos, ou dé-vendorer les 1 532 lignes | `providers/kronos/shiyu_model/` |
| Réparer `.gitignore` (dernière ligne `r e f e r e n c e /` inopérante), désindexer `.coverage` et `src/aegis_trade.egg-info/`, statuer sur `models/` | racine |
| Traiter `mlflow 1.27.0` (144 vulnérabilités OSV, 21 CRITICAL) : pin transitif ou retrait de `pyqlib` si Qlib est supprimé au Lot 4 | `uv.lock:2820-2822` |
| `Dockerfile.backend` : `USER` non-root, installation depuis `uv.lock` et non `pyproject.toml`, ne pas publier `0.0.0.0` sans auth | `Dockerfile.backend:28`, `docker-compose` |
| Réconcilier `requirements.txt` / `uv.lock` / `pyproject.toml` : mlflow `3.14.0` vs `1.27.0`, 7 dépendances omises (torch, stable-baselines3, finrl, faiss-cpu, gymnasium, tenacity, einops), épingler `pyproject.toml:16,17,22,34-36` | racine |
| Statuer sur `sparsediffpy==0.3.0` (aucune provenance, jamais importé) et sur `gym==0.26.2` (déprécié) | `uv.lock:1162,5740` |
| Unifier la numérotation ADR (`docs/ADR/0001-0016` vs `docs/architecture/adr/ADR-001-003`), marquer `ADR-002` `Superseded`, écrire les 3 ADR manquants (vendoring Kronos, RL/SB3, frontière `infrastructure/live/vnpy/`) | `docs/ADR/` |
| Mettre les docs Phase 2 en conformité avec le code mesuré (§5.4 de l'audit : ~30 lignes, 15 fichiers) | `docs/phase2/`, `README.md`, `PROJECT_PHILOSOPHY.md` |

**Historique git : aucune réécriture sans décision explicite de l'utilisateur.** Les 23 commits à
message de refus sont documentés dans l'audit ; les réécrire change tous les sha.

---

## LOT 6 — DETTE RÉSIDUELLE

Ce lot existe parce que le plan initial en 6 lots (0–5) laissait ces points **non assignés**.
Ils sont réels, mesurés, et n'appartenaient à aucun lot.

| # | Point | Cible |
|---|---|---|
| 1 | Deux Councils coexistent ; exécuter ou annuler `LEGACY_COUNCIL_MIGRATION.md` | `application/council/` |
| 2 | Supprimer `find_violations.py` et `exceptions.py` (outillage mort) | `src/` |
| 3 | 329 violations ruff dont 249 `F401` (imports morts), 33 `F405`, 19 `E402`, 14 `F841` | `src/`, `tests/`, `scripts/` |
| 4 | Frontend : **aucun test, aucun script de test** ; `ws://127.0.0.1:8000` codé en dur, pas de `wss`, `JSON.parse` non validé injecté dans le store, toutes les dépendances en `^` | `frontend/` |
| 5 | Tiers `capital.py` inerte | `api/routers/capital.py:23` |
| 6 | Exceptions avalées silencieusement ; `import random` mort ; `process_event` de 75 lignes avec `ev` ré-annoté deux fois | `application/monitoring/engine.py:18,87-89,91-165` |
| 7 | Télémétrie de dashboard falsifiée : `cpu_usage=0.0`, `BrokerSnapshot(connected=True, latency_ms=12.5, gateway="BINANCE")` alors que le broker est Deriv, `StrategySnapshot(status="Live", running_time="14h 22m")` | `application/monitoring/engine.py:60-78` |
| 8 | Aucun test pour `engine/reasoning_events.py` ni `domain/trade_record.py` | `tests/` |
| 9 | Modules les plus faibles en couverture : `kronos.py` 8 %, `kronos/trainer.py` 16 %, `module.py` 19 %, `vnpy/execution.py` 33 %, `engine/risk.py` 71 %, `engine/global_risk.py` **77 %** | `tests/` |
| 10 | Restriction OpenBB « Mission C » (DXY / US10Y seulement) : lever ou documenter en ADR | `openbb_provider.py:43,100,103,106` |
| 11 | `Exchange.SMART` codé en dur court-circuite `mapper.py` ; `gateway_name = exchange # simplification` ; `return "mock_id"` | `providers/vnpy_adapter.py:69,82`, `live/vnpy/execution.py:46` |
| 12 | Les 2 `# type: ignore` nus de `src/` doivent être justifiés ou supprimés | `infrastructure/risk/global_risk_adapter.py:86`, `providers/mt5_provider.py:4` |

---

## TABLE DE CORRESPONDANCE BLOQUANT → LOT

Les 21 bloquants de `AUDIT_COMPLET_2026-07-31.md:§10` sont tous assignés.

| Bloquant | Sévérité | Lot |
|---|---|---|
| 1 — 4 chemins contournent le RiskEngine | P0 | **1** |
| 2 — signature `validate_order` (2 args sur 3) | P0 | **1** |
| 3 — appel hors `try/except`, mort silencieuse | P0 | **1** |
| 4 — `F821 IPaperBroker` sur `emergency_halt` | P0 | **1** |
| 5 — `MagicMock(spec=…)` masque le bug | P0 | **1** |
| 6 — API sans auth (CORS, WS, rate limit, Docker root) | P0 | **1** (Docker → **5**) |
| 7 — `mypy --strict` n'analyse rien | P1 | **0** |
| 8 — `i_understand_this_is_real_money=True` littéral | P1 | **1** |
| 9 — `pytest` n'assemble pas la suite | P1 | **0** |
| 10 — 36 `__init__.py` + 7 imports `src.` | P1 | **0** |
| 11 — zéro test d'API, ratio 0,40 | P1 | **1** (API) + **6** (reste) |
| 12 — 6 validateurs `passed=True` codé en dur | P2 | **4** |
| 13 — traçabilité falsifiée (`v1.0.0-mock`) | P2 | **4** |
| 14 — Qlib façade (`LightGBMModelMock`) | P2 | **4** |
| 15 — aucune donnée réelle, runner mort | P2 | **2** |
| 16 — duplications numériques (ATR, PnL, equity) | P3 | **3** |
| 17 — Kronos vendoré sans LICENSE | P3 | **5** |
| 18 — `mlflow 1.27.0`, 21 CRITICAL | P3 | **5** |
| 19 — Dockerfile ignore `uv.lock`, tourne en root | P3 | **5** |
| 20 — 23 commits à message de refus | P3 | **5** (documentation seule) |
| 21 — ~30 lignes de doc fausses | P3 | **5** |

---

## CE QUE CE PLAN NE PROMET PAS

1. **Il ne promet pas la rentabilité.** Les Lots 0–6 rendent le système **validable**.
   Qu'une stratégie soit profitable est un résultat empirique, pas un livrable d'ingénierie.
2. **Il ne promet pas que les validateurs passeront.** Une fois qu'ils calculent réellement (Lot 4),
   ils peuvent rejeter les stratégies actuelles. Ce serait un résultat correct, pas un échec du plan.
3. **Il ne promet aucun délai.** Le Lot 4 dépend de la disponibilité de données historiques réelles,
   qui n'entrent pas encore dans le système (Lot 2).

## PORTE DE SORTIE PAR LOT

Aucun lot n'est déclaré terminé sans, sur le module touché :
`pytest -v` vert, `mypy --strict src/` sans régression du compte de base, coverage mesurée,
et la liste explicite des tests de régression couvrant `engine/`, `domain/`, `providers/`.

