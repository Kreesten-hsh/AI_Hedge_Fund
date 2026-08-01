# Phase 2 : Roadmap Détaillée et Stratégie de Validation

> **Document réécrit le 2026-07-31** sur la base de `docs/refont/AUDIT_COMPLET_2026-07-31.md` (verdict **NO-GO**).
> La version précédente déclarait `[CODE-READY]` sur des composants sans site d'appel, et `[x] VALIDATED` sur un cycle jamais exécuté. Ces statuts sont corrigés ci-dessous.

> **Source de vérité pour le GO/NO-GO : l'exécution réelle des validateurs, pas ce document ni `VALIDATION_PIPELINE_REPORT.md`.** À ce jour les 6 validateurs retournent `passed=True` codé en dur (`hold_out_validator.py:42-48`, `walk_forward_validator.py:21-26`, `monte_carlo_validator.py:22-27`, `benchmark_validator.py:21-26`, `multi_validators.py:21-26,37-42`). Aucun verdict issu de ce pipeline n'a de valeur probante tant que le **Lot 4** de `docs/refont/PLAN_DE_CORRECTION.md` n'est pas exécuté.

## Objectif du projet (rappel, non négociable)

Amener le système à un état où il peut (1) tourner en **démo réelle** sur compte Deriv pour accumuler de l'expérience exploitable, puis (2) **seulement si les gates de validation passent réellement**, opérer en capital réel. La démo n'est pas cosmétique : c'est la condition d'entrée de tout le pipeline scientifique.

**Statut actuel : la démo est structurellement impossible.** Aucun abonnement WebSocket tick dans le dépôt, fills constants (`fill_price = Decimal("100.0")`), drawdown câblé à `0.0` — le kill switch ne peut donc pas se déclencher — et les 8 agents votent `WAIT conf=0.0`.

## Légende des statuts (mesurable)

- `[ ]` : à faire, rien n'existe.
- `[ÉCRIT-NON-CÂBLÉ]` : le code existe, mais **zéro site d'appel en production** (vérifiable par grep).
- `[CÂBLÉ-NON-VALIDÉ]` : appelé en production, mais aucune validation statistique ni économique franchie.
- `[FAÇADE]` : retourne une constante, un mock ou une donnée aléatoire au lieu de calculer.
- `[VALIDÉ]` : un cycle réel a tourné, sur données réelles, avec métriques traçables (`git_version`, `data_hash`).

**Aucune mission de la Phase 2 n'est `[VALIDÉ]` au 2026-07-31.**

---

## Missions AI-01 à AI-08 — statut réel

### `[ÉCRIT-NON-CÂBLÉ]` AI-01 : Memory Engine
**Objectif :** fondations de l'Experience Memory (FAISS, embeddings).
**Réel :** le code existe, mais `MemoryManager(` ne compte **0 occurrence** hors définition. Rien ne l'instancie en production. L'ancien statut `[x] VALIDATED` était faux : aucun cycle réel n'a jamais alimenté cette mémoire.

### `[ÉCRIT-NON-CÂBLÉ]` AI-02 : Reflection Engine
**Objectif :** boucle post-trade (feature engineering, stockage).
**Réel :** `ReflectionPipeline(` compte **0 site d'appel**. La boucle post-trade n'est jamais déclenchée. De plus, l'extracteur embarque sa propre implémentation d'ATR (`application/reflection/extractor.py:54-101`), divergente des 3 autres du dépôt — traité au Lot 3.

### `[ÉCRIT-NON-CÂBLÉ]` AI-03 : Reasoning Engine
**Objectif :** transformer les expériences FAISS en règles métier statistiques, versionnées, vérifiables.
**Réel :** le raisonneur branché en production est `MockReasoner()` (`api/deps.py:53`). Aucune règle n'est produite à partir de données réelles. Le port est en outre déclaré dans `domain/reasoning.py:125` mais importé depuis `infrastructure/` par `pattern_agent.py:2` (violation d'axe, Lot 3).

### `[ÉCRIT-NON-CÂBLÉ]` AI-04 : Reinforcement Learning
**Objectif :** FinRL/SB3 pour l'optimisation asynchrone (offline) des poids du Conseil et du sizing. Hors chemin critique temps réel.
**Réel :** `PolicyEvaluator(`, `PolicyTrainer(`, `ValidationRunner(` comptent **0 site d'appel**. L'entrée RL en production est `np.zeros(30)` (`orchestrator.py:97`) — un vecteur nul, donc une politique qui n'observe rien. Les 4 fichiers de tests RL n'étaient pas collectés (imports `src.…`, corrigé au Lot 0).

### `[CÂBLÉ-NON-VALIDÉ]` AI-05 : Multi Agent Council
**Objectif :** comité de décision (Trend, Momentum, Volatility, …) exploitant le RL et les règles du Reasoning Engine.
**Réel :** seule mission réellement câblée. `MultiAgentCouncil.evaluate()` s'exécute, mais la sortie mesurée est `7 agents WAIT conf=0.0` puis `VERDICT: WAIT | mult=0.0 | conf=0.0` — les agents reçoivent des features placeholders dont les clés ne correspondent pas à celles qu'ils attendent. Deux Councils coexistent par ailleurs dans le dépôt (`LEGACY_COUNCIL_MIGRATION.md` ni exécuté ni annulé, Lot 6).
**Non validé :** aucune métrique économique n'a été produite à partir de ses décisions.

### `[FAÇADE]` AI-08 : Kronos-mini Forecasting
**Objectif :** intégrer les prédictions LLM time-series dans les agents Trend et Pattern.
**Réel :** `kronos_adapter.py:40-41,63-71` prédit sur `np.random.randn` — le modèle infère sur du bruit, pas sur des prix. 1 532 lignes de l'amont `NeoQuasar/Kronos-mini` sont vendorées dans `providers/kronos/shiyu_model/` **sans LICENSE** (Lot 5). Couverture de tests : `kronos.py` 8 %, `kronos/trainer.py` 16 %.
**Corrections de la version précédente de ce document :** (1) le modèle est `NeoQuasar/Kronos-mini`, pas un modèle d'Amazon Science — la confusion venait de `amazon/chronos-t5-mini`, qui est un autre modèle ; (2) l'empreinte « <300MB RAM » est contredite par `RESEARCH_LOGBOOK.md` (entrée de gouvernance « Intégration Kronos (Sprint AI-08) », ~917 MB mesurés). Le statut `[PAUSED]` masquait 1 532 lignes vendorées : ce n'est pas une intégration en pause, c'est du code amont non licencié dans le dépôt.
**Décision attendue au Lot 4 :** brancher un vrai `data_provider`, ou marquer le module explicitement inactif.

---

## Pipeline de Validation (AI-06 à AI-07)

Ce pipeline reste la bonne cible. Ce qui change : **aucune de ses étapes n'a été franchie**, et les 3 dernières étaient marquées `[CODE-READY]` alors que les données réelles n'entrent pas dans le système. Rappel de la loi `CLAUDE.md` : aucune étape ne se saute.

### `[ ]` 1. Historical Validation (AI-05a)
- **Objectif :** backtest pur sur données EOD et tick-by-tick passées, contrôles d'overfitting.
- **Bloquant :** le `Backtester` est bien construit dans `hold_out_validator.py:32` mais **jamais lancé** ; le validateur retourne `passed=True` sans avoir backtesté. Aucun `git_version` ni `data_hash` réel (`validation_runner.py:57,60`).

### `[ ]` 2. Replay Validation (AI-05b)
- **Objectif :** tick-replay, rejeu d'une semaine historique à 100x pour éprouver latence et stabilité.
- **Bloquant :** aucun flux tick n'existe à rejouer. Prérequis = Lot 2 (`DerivMarketGateway` + abonnement WebSocket).

### `[ ]` 3. Paper Trading (AI-06a)
- **Objectif :** exécution live sans argent réel, compte démo, connectivité broker, accumulation d'expériences.
- **Bloquant :** ~~`fill_price = Decimal("100.0")` et `latency_ms = 50.0` constants ; `risk_decision="APPROVED"` codé en dur~~ (levés au Lot 2B) ; `on_trade` est un `pass` (`infrastructure/live/vnpy/execution.py:69`) ; ~~`scripts/run_live_paper_trading.py` meurt à l'import~~ (script supprimé au Lot 2F). Un paper trading qui remplit toujours à 100.0 n'accumule pas de l'expérience, il fabrique un faux historique — donc pire que rien pour AI-01/AI-02.
- **Bloquant restant :** aucun consommateur ne relie `DerivMarketGateway` (flux de `Tick`) à l'orchestrateur (qui consomme `IMarketFeed`, un flux de `MarketBar`). L'agrégation tick → barre n'existe nulle part dans le dépôt. Tant qu'elle manque, aucun tick Deriv réel n'atteint le Council.
- **Devient atteignable après les Lots 0 → 2.**

### `[ ]` 4. Shadow Trading (AI-06b)
- **Objectif :** signaux générés et loggés sur données du compte live, **sans envoi d'ordre**. Comparaison prix théoriques vs réels.
- **Bloquant :** exige des prix réels des deux côtés (Lot 2) et un chemin d'exécution où l'inhibition d'envoi est garantie — or 4 chemins contournent aujourd'hui le `RiskEngine` (`api/routers/positions.py:43`, `providers/vnpy_adapter.py:52,57,79`, `infrastructure/live/vnpy/execution.py:14,47`). Tant que ces chemins existent, « ne pas envoyer l'ordre » n'est pas une garantie architecturale.

### `[ ]` 5. Micro Capital (AI-07a, AI-07b)
- **Objectif :** capital réel limité (50 $), lot minimum, via `LiveDerivGateway` et ségrégation `CapitalAllocation`.
- **Bloquant, et il est de nature sécuritaire :** `i_understand_this_is_real_money` vaut le littéral `True` (`api/deps.py:43`) — le consentement argent réel n'est dérivé d'aucune action utilisateur. L'API n'a aucune authentification (POST et WebSocket), `allow_origins=["*"]` avec `allow_credentials=True` (`api/main.py:16-19`), le tiers `capital.py:23` est inerte, et le kill switch ne peut pas se déclencher puisque le drawdown est constant à `0.0`.
- **Cette étape ne s'ouvre qu'après validation réelle des étapes 1 à 4, pas après « correction du code ».**

### `[ ]` 6. Production (Phase 3)
- **Objectif :** scale-up, allocation du capital total.
- **Condition :** respect intégral d'`AEGIS_DECISION_PIPELINE.md` et gates franchis avec métriques traçables.

---

## Séquence réelle jusqu'à la démo puis l'argent réel

```
Lots 0–1  ──►  Lot 2  ──►  Étapes 1–2  ──►  Lot 4  ──►  Étape 3  ──►  Étape 4  ──►  Étape 5
gates +      données      validation     validateurs     démo       shadow      micro
RiskEngine    réelles     historique       réels        réelle                  capital
```

Détail dans `docs/refont/PLAN_DE_CORRECTION.md`. **Statut de ce plan : proposé, non exécuté.**

## Ce que cette roadmap ne promet pas

1. **Pas la rentabilité.** Franchir les lots rend le système *validable*, pas profitable. La profitabilité est un résultat empirique.
2. **Pas que les validateurs passeront.** Une fois qu'ils calculent réellement, ils peuvent rejeter les stratégies actuelles — notamment aux seuils `benchmark_gate.py:14-15` (`0.85` / `2.0`). Conformément à `CLAUDE.md`, **un rejet propre et reproductible est un progrès**, pas un échec.
3. **Aucun délai.** L'étape 1 dépend de données historiques réelles qui n'entrent pas encore dans le système.

