# Phase 2 : Backlog Technique

> **Document réécrit le 2026-07-31** sur la base de `docs/refont/AUDIT_COMPLET_2026-07-31.md` (verdict **NO-GO**).
> La version précédente barrait 13 tâches sur 17 avec la mention *(Fait)*. Mesure par grep : aucune de ces
> tâches n'a de cycle d'exécution réel derrière elle. **« Écrit » n'est pas « fait ».**

> **Vocabulaire de statut, identique à `PHASE2_ROADMAP.md` :**
> `[ÉCRIT-NON-CÂBLÉ]` code présent, **zéro site d'appel en production** —
> `[CÂBLÉ-NON-VALIDÉ]` appelé en production, aucune validation franchie —
> `[FAÇADE]` retourne une constante, un mock ou une donnée aléatoire au lieu de calculer —
> `[VALIDÉ]` cycle réel, données réelles, `git_version` + `data_hash` traçables —
> `[ ]` rien n'existe.
>
> **Zéro tâche `[VALIDÉ]` au 2026-07-31.**

## Objectif de ce backlog

Rendre atteignable la **démo réelle sur compte Deriv** (accumulation d'expérience exploitable), puis —
et seulement si les gates passent réellement — le **capital réel**. Une tâche cochée qui ne contribue
pas à ce chemin est une tâche fausse, pas une tâche terminée.

**Prérequis transverse à tout ce backlog : le Lot 0 de `docs/refont/PLAN_DE_CORRECTION.md`.** Tant que
`pytest` n'assemble pas la suite (36 `__init__.py` manquants, 7 imports `src.…`) et que `mypy --strict`
n'analyse rien, aucune tâche ci-dessous n'est vérifiable — on la cocherait à l'aveugle.

---

## Priorité 0 — Bloquant

### `[ÉCRIT-NON-CÂBLÉ]` AI-01-A — Librairie d'embedding
Livré : `BasicDeterministicEmbedding`. Le code existe et est testé en isolation.
**Pourquoi pas *(Fait)* :** `MemoryManager(` compte **0 occurrence** hors définition — rien n'instancie
la mémoire en production, donc aucun embedding réel n'a jamais été produit par le système en marche.

### `[ÉCRIT-NON-CÂBLÉ]` AI-01-B — FAISS dans l'infrastructure
Livré : `FaissVectorStore` + adapters. Même réserve que AI-01-A : index jamais alimenté par un cycle réel.
`faiss-cpu` est par ailleurs absent de `pyproject.toml` (7 dépendances omises, Lot 5) — l'installation
depuis le seul `pyproject.toml` ne fournit pas FAISS.

### `[ ]` AI-02-A — Câblage du Feature Extraction à l'EventBus
Écoute des `MarketBar` et `OrderEvent`. Non commencé.
**Bloquant amont :** aucun abonnement WebSocket tick n'existe dans le dépôt (Lot 2). Il n'y a
actuellement aucun `MarketBar` réel à écouter.

### `[ ]` AI-02-B — Routeur post-trade (gain vers SuccessMemory, perte vers FailureMemory)
Non commencé, et le routeur ne peut pas être correct avant le Lot 2 : `fill_price` est la constante
`Decimal("100.0")`, donc le signe du PnL qui déciderait du routage est fabriqué, pas mesuré.
`ReflectionPipeline(` compte 0 site d'appel : la boucle post-trade n'est jamais déclenchée.

---

## Priorité 1 — Critique

### `[ÉCRIT-NON-CÂBLÉ]` AI-03-A — Abstraction `IClusterEngine` (DBSCAN/HDBSCAN)
Code présent. Clustering jamais exécuté sur des expériences réelles : l'index FAISS qu'il devrait
consommer n'est pas alimenté (AI-01-B).

### `[ÉCRIT-NON-CÂBLÉ]` AI-03-B — `OllamaReasoner` + `KnowledgeValidator`
`OllamaReasoner` existe. **Ce n'est pas ce que la production câble :** `api/deps.py:53` injecte
`MockReasoner()`. Tout raisonnement servi par l'API est donc un mock, pas un LLM local.
Le port est déclaré dans `domain/reasoning.py:125` mais `application/council/agents/pattern_agent.py:2`
l'importe depuis `infrastructure/` — inversion de dépendance à corriger (Lot 3).

### `[ÉCRIT-NON-CÂBLÉ]` AI-04-A — Reward function 8 paramètres
`RewardCalculator` présent et testé en isolation. Jamais alimenté par un épisode réel.

### `[ÉCRIT-NON-CÂBLÉ]` AI-04-B — FinRL/SB3 sur environnement event-driven
`CustomAegisEnv` + `PolicyTrainer` asynchrone présents. `PolicyTrainer(` : 0 site d'appel.
L'observation passée au RL en production est `np.zeros(30)` (`application/council/orchestrator.py:97`) —
un vecteur nul, pas un état de marché.

### `[ÉCRIT-NON-CÂBLÉ]` AI-04-C — Policy Promotion Gate
`PolicyEvaluator` présent. `PolicyEvaluator(` et `ValidationRunner(` : 0 site d'appel.
Aucune politique n'a jamais été soumise au gate, donc le gate n'a jamais rien refusé ni promu.

### `[CÂBLÉ-NON-VALIDÉ]` AI-05-A — Prompts et rôles du Comité Multi-Agents
**Seule mission réellement câblée en production.** 8 agents déterministes, `MultiAgentCouncil.evaluate()`
appelé par l'orchestrateur.
Sortie mesurée à l'exécution : `7 agents WAIT conf=0.0` → `VERDICT: WAIT | mult=0.0 | conf=0.0`.
Le comité tourne mais ne décide rien, faute de `FeatureStore` réel en entrée (Lot 2).

### `[ ]` AI-05-B — Droit de veto du Risk Engine au niveau Domain
Déclaré *(Fait — GlobalRiskManager intègre le Veto)*. **Grep : 0 occurrence d'un veto basé sur la
Knowledge Base.** Pire, l'autorité du `RiskEngine` est actuellement contournable par 4 chemins d'ordre
(`api/routers/positions.py:43`, `providers/vnpy_adapter.py:52,57,79`,
`infrastructure/live/vnpy/execution.py:14,47`) — Lot 1. Un veto sur un moteur contournable n'est pas un veto.

---

## Priorité 2 — Exploitation et validation

> **Correction d'identifiants :** la version précédente réutilisait `AI-05-A` et `AI-05-B` dans cette
> section alors que ces identifiants sont déjà pris en Priorité 1. Ils deviennent `AI-09-A` et `AI-09-B`.

### `[ ]` AI-09-A — Export automatique des logs vers le Research Logbook
Non commencé. Sans données réelles (Lot 2), le logbook n'aurait à exporter que des constantes.

### `[ ]` AI-09-B — Optimisation de la recherche de similarité (Top 200), latence HFT
Non commencé. Optimiser une recherche sur un index vide n'a pas de sens : dépend de AI-01-B câblé.

### `[ ]` AI-06-A — Historical & Replay Validation (TickReplayEngine, BenchmarkGate)
Déclaré *(Fait)*. **Mesure :** les 6 validateurs retournent `passed=True` **codé en dur**
(`hold_out_validator.py:42-48`, `walk_forward_validator.py:21-26`, `monte_carlo_validator.py:22-27`,
`benchmark_validator.py:21-26`, `multi_validators.py:21-26,37-42`). Le `Backtester` est construit à
`hold_out_validator.py:32` puis **jamais lancé**. `git_version` et `data_hash` sont factices
(`validation_runner.py:57,60`). Aucune validation historique n'a donc eu lieu. Traité au Lot 4.

### `[ ]` AI-06-B — Live Paper Trading & Shadow Trading
Déclaré *(Fait — DerivGateway, ShadowTradingEngine)*. **Mesure :** aucun abonnement WebSocket tick
dans le dépôt ; `fill_price = Decimal("100.0")` et `latency_ms = 50.0` constants ;
`risk_decision="APPROVED"` codé en dur ; `on_trade` a pour corps `pass`
(`infrastructure/live/vnpy/execution.py:69`) ; `scripts/run_live_paper_trading.py` meurt à l'import.
Un paper trading qui remplit toujours à 100.0 ne produit pas de l'expérience, il produit un faux
historique — c'est-à-dire un poison pour AI-01 et AI-02. Traité au Lot 2.

### `[ ]` AI-07-A — Micro Capital Live Trading
Déclaré *(Fait — LiveDerivGateway, CapitalAllocation, sécurité)*. **Mesure, de nature sécuritaire :**
`i_understand_this_is_real_money` vaut le littéral `True` (`api/deps.py:43`) — le consentement argent
réel n'est dérivé d'aucune action utilisateur ; l'API n'a **aucune authentification** (POST et
WebSocket) et tourne en `allow_origins=["*"]` avec `allow_credentials=True` (`api/main.py:16-19`) ;
le tiers `api/routers/capital.py:23` est inerte ; le drawdown est constant à `0.0`, donc le kill
switch ne peut structurellement pas se déclencher. Lots 1 et 2.

### `[FAÇADE]` AI-08-A — Kronos-mini Forecasting
Statut précédent `[PAUSED]`. Ce n'est pas une intégration en pause : `kronos_adapter.py:40-41,63-71`
**prédit sur `np.random.randn`** — le modèle infère sur du bruit, pas sur des prix. 1 532 lignes de
l'amont `NeoQuasar/Kronos-mini` sont vendorées dans `providers/kronos/shiyu_model/` **sans LICENSE**
(Lot 5). Couverture : `kronos.py` 8 %, `kronos/trainer.py` 16 %.
Décision attendue au Lot 4 : brancher un vrai `data_provider`, ou marquer le module explicitement inactif.

---

## Récapitulatif mesuré

| Statut | Nombre | Tâches |
|---|---|---|
| `[VALIDÉ]` | 0 | — |
| `[CÂBLÉ-NON-VALIDÉ]` | 1 | AI-05-A |
| `[ÉCRIT-NON-CÂBLÉ]` | 7 | AI-01-A, AI-01-B, AI-03-A, AI-03-B, AI-04-A, AI-04-B, AI-04-C |
| `[FAÇADE]` | 1 | AI-08-A |
| `[ ]` | 8 | AI-02-A, AI-02-B, AI-05-B, AI-09-A, AI-09-B, AI-06-A, AI-06-B, AI-07-A |

La version précédente comptait 13 tâches barrées *(Fait)*. Aucune ne survit à la mesure.

## Ordre de reprise

Ce backlog ne se traite pas dans l'ordre de ses priorités historiques, mais dans l'ordre imposé par
`docs/refont/PLAN_DE_CORRECTION.md` :

1. **Lot 0** — restaurer `pytest` et `mypy --strict`. Sans ça, cocher une tâche est un acte de foi.
2. **Lots 1–2** — RiskEngine non contournable, puis données réelles entrantes. Débloque AI-02-A/B,
   AI-05-A, AI-06-B, AI-07-A.
3. **Lot 4** — validateurs qui calculent réellement. Débloque AI-06-A, AI-04-C, AI-08-A.
4. **Puis seulement** AI-01/AI-03/AI-04 câblés, une fois qu'il existe de l'expérience réelle à mémoriser.

## Ce que ce backlog ne promet pas

- **Pas de rentabilité.** Ce document ordonne du travail d'ingénierie, il ne prédit aucun P&L.
- **Pas que les tâches débloquées passeront.** Une fois les validateurs réels (Lot 4), il est possible
  qu'aucune stratégie ne franchisse `benchmark_gate.py:14-15` (`0.85` / `2.0`). Conformément à
  `CLAUDE.md`, **un rejet propre et reproductible est un progrès**, pas un échec de session.
- **Pas de délai.** Aucune date n'est avancée : l'estimation était précisément le mécanisme qui a
  produit 13 tâches faussement terminées.
