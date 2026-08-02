# État du chantier « mise en conformité des docs » — 2026-07-31

> **Rôle de ce fichier :** permettre à une session repartant d'un contexte vide de reprendre le chantier
> sans rien redemander. Il ne contient aucune information nouvelle sur le code — tout le fond est dans
> `AUDIT_COMPLET_2026-07-31.md` et `PLAN_DE_CORRECTION.md`, dans le même dossier.

## 0. Contraintes permanentes — à lire avant toute action

- **Branche de travail : `claude-code-takeover`.** Jamais `main`.
- **Les Lots 0 à 6 du `PLAN_DE_CORRECTION.md` ne sont PAS approuvés.** Aucun fichier de `src/` ne doit
  être modifié tant que l'utilisateur n'a pas donné un feu vert explicite, lot par lot ou en bloc.
  Seul `docs/` est autorisé à l'écriture pour le présent chantier.
- **Secrets : jamais de valeur recopiée.** Référencer par nom de clé + `fichier:ligne` + sha de commit.
  Ne pas lire le contenu de `.env` sans besoin précis et explicite.
- **TradingAgents / AutoHedge / FinceptTerminal / Vibe-Trading = `[INSPIRATION]`,** décision
  d'architecture explicite de l'utilisateur. Ce ne sont **pas** des lacunes, ne jamais les signaler
  comme manquants ni comme échecs d'intégration.
- **Ne faire confiance qu'à ce que `grep` montre.** Aucun rapport antérieur affirmant « les tests
  passent » ne fait foi ; tout se ré-exécute.
- Environnement : appeler `.venv/bin/python`, `.venv/bin/pytest`, `.venv/bin/mypy` **directement**.
  Ne pas utiliser `uv run` (il synchronise, donc il mute l'environnement).

## 1. Ce que ce chantier corrige

Objectif de l'utilisateur, à rappeler dans chaque fichier traité :
**démo réelle sur Deriv pour entraîner le système, puis capital réel pour produire de l'argent.**

Problème mesuré : §5.4 de l'audit relève **~30 lignes falsifiées sur 15 fichiers** — des docs qui
déclarent « Fait », « Intégré », « Entièrement implémenté » pour du code non câblé, façade ou absent.
Correspond à la ligne `PLAN_DE_CORRECTION.md:155`.

Principe directeur : **on ne réécrit pas l'intention, on corrige l'état déclaré.** Les documents disent
des choses justes sur ce qu'on veut construire ; ils mentent sur ce qui existe.

## 2. Avancement — Phase 3 (Qlib/LightGBM Réel) Clôturée (2026-08-02)

- **Lot 0 (Gates)** : ✅ TERMINÉ (413+ tests pass, mypy strict stable).
- **Lot 1 (RiskEngine Authority)** : ✅ TERMINÉ (4 chemins de bypass fermés, RiskGate centralisé).
- **Lot 2 / Phase 1 (Sourcing Réel)** : ✅ TERMINÉ (Crash 1000, Boom 1000, XAUUSD réels en Parquet).
- **Lot 4 / Phase 2 (Validateurs Réels)** : ✅ TERMINÉ.
  - Supprimé les `passed=True` en dur dans les 6 validateurs (`HoldOut`, `WalkForward`, `MonteCarlo`, `Benchmark`, `MultiMarket`, `MultiTimeframe`).
  - Calculs réels implémentés (Backtest, Monte-Carlo bootstrap 1000+ itérations, Sharpe/Drawdown/WinRate réels).
  - Dynamisé `git_version` (git rev-parse) et `data_hash` (SHA256 parquet) dans `ValidationRunner`.
  - Documenté les seuils provisoires dans `ValidationConfig`.
- **Phase 3 (Intégration Qlib/LightGBM Réelle)** : ✅ TERMINÉ.
  - Vrai `LightGBMModel` via `lightgbm.train()` (contournement LightGBM-direct, mlflow 1.27.0).
  - `DatasetBuilder.build_supervised()` construit le label `forward_return_1` (shift(-1) rendement).
  - `MLStrategy` recalibrée en seuils de rendement (0.0002/-0.0002).
  - Script `train_qlib_model.py` complet : load → features → split chrono → train → validation → export conditionnel.
  - 14 tests réels dans `test_qlib_adapter.py` (label leakage, real training, strategy wiring).
  - **Résultat de validation : score 30/100, REJETÉ.** Résultat scientifiquement correct (rejet propre = succès du pipeline).

| # | Fichier | Traitement appliqué |
|---|---|---|
| 1 | `PHASE2_ROADMAP.md` | Statuts réécrits avec le vocabulaire mesurable (§4) |
| 2 | `PHASE2_BACKLOG.md` | Idem + récapitulatif par statut recompté |
| 3 | `DEPENDENCY_MATRIX.md` | Réécrit : « Intégré » remplacé par statut mesuré + preuve |
| 4 | `VALIDATION_PIPELINE_REPORT.md` | Métriques annoncées vs métriques réellement calculables |
| 5 | `BENCHMARKS.md` | **Défendu** : ses chiffres sont justes. Ajout colonne « Mesurable aujourd'hui » |
| 6 | `GITHUB_INTEGRATION_GUIDE.md` | Corruption structurelle réparée + statuts d'intégration corrigés |
| 7 | `PROJECT_PHILOSOPHY.md` | Principes conservés mot pour mot, seul l'inventaire factuel corrigé |
| 8 | `AGENTS_SPECIFICATION.md` | Code réellement présent et appelé : concédé, dégradé sur le comportement |
| 9 | `ENGINEERING_RULES.md` | Tableau de respect mesuré (4 violées, 1 non vérifiable, 1 respectée) |
| 10 | `RESEARCH_LOGBOOK.md` | Erreurs annotées **en place**, jamais supprimées |
| 11 | `LIVE_TRADING_SAFETY_PROTOCOL.md` | Avertissement d'ouverture + les mécanismes de sécurité mesurés inopérants |

## 3. File d'attente — reste à traiter, dans cet ordre

**Bloc A — spécifications Kronos et migration (les plus divergentes du code) :**

1. `docs/phase2/KRONOS_MINI_INTEGRATION_SPEC.md` (64 lignes) — le modèle réellement vendoré est
   `NeoQuasar/Kronos-mini`, distinct d'`amazon/chronos-t5-mini` **et** de `shiyu-coder/Kronos`
   (le répertoire vendoré s'appelle `shiyu_model/`, d'où la confusion). 1 532 lignes copiées dans
   `src/aegis_trade/providers/kronos/shiyu_model/`, **aucune LICENSE dans le dépôt**.
   `kronos_adapter.py:40-41,63-71` prédit sur `np.random.randn`.
2. `docs/phase2/KRONOS_EVALUATION_REPORT.md` (27 lignes) — ne rapporte que des métriques de **coût**
   (~917 Mo de RAM crête, 49 s/epoch sur 1000 bougies), **jamais de qualité** : pas de MAPE ni de RMSE
   contre une baseline naïve. Une évaluation sans mesure de qualité n'évalue pas le modèle.
3. `docs/phase2/LEGACY_COUNCIL_MIGRATION.md` (17 lignes) — migration ni exécutée ni annulée. Rattachée
   au Lot 6 du plan de correction. Doit être marquée en suspens explicite, pas laissée ambiguë.

**Bloc B — specs phase2 à confronter au §5.4 de l'audit** (vérifier avant d'écrire : certaines sont
peut-être déjà exactes, auquel cas on les défend au lieu de les dégrader) :

`KNOWLEDGE_SYSTEM.md`, `AEGIS_DECISION_PIPELINE.md`, `REASONING_ENGINE_SPEC.md`,
`PHASE2_MASTER_PLAN.md`, `FEATURE_ENGINEERING.md`, `COUNCIL_VOTING_SPEC.md`, `RL_TRAINING_GUIDE.md`,
`EXPERIENCE_MEMORY_SPEC.md`, `ARCHITECTURE_AI.md`, `MULTI_AGENT_COUNCIL.md`,
`PHASE2_IMPLEMENTATION_ORDER.md`, `RL_LEARNING_SPEC.md`.

**Bloc C — hors `phase2/`, points précis relevés par l'audit :**

- `docs/SYSTEM_ARCHITECTURE.md:79`
- `README.md:107-117` — annonce 12 sous-paquets, il y en a 9
- `docs/PAPER_TRADING_ARCHITECTURE.md:4`
- `docs/ADR/ADR-002:8,9` — FinGPT n'y est pas marqué `Superseded` alors que cinq fichiers réécrits
  le désignent désormais comme abandonné
- `docs/PROVIDERS_ROADMAP.md:52-53`

## 4. Vocabulaire de statut — à réutiliser tel quel

Ne pas inventer d'autres libellés : la cohérence entre fichiers est le seul moyen de relire l'ensemble.

| Statut | Signification stricte |
|---|---|
| `[ ]` | Rien n'existe |
| `[ÉCRIT-NON-CÂBLÉ]` | Code présent, **zéro** site d'appel en production |
| `[CÂBLÉ-NON-VALIDÉ]` | Appelé en production, aucune étape de validation franchie |
| `[FAÇADE]` | Retourne une constante, un mock ou une donnée aléatoire |
| `[VALIDÉ]` | Cycle réel, données réelles, `git_version` + `data_hash` traçables |
| `[VENDORÉ]` | Code amont copié — question de licence, pas d'intégration |
| `[INSPIRATION]` | Jamais intégré, référence de conception assumée |
| `[ABANDONNÉ]` | Évalué puis écarté |

## 5. Méthode, éprouvée sur les 11 fichiers traités

Pour chaque fichier, dans cet ordre :

1. **`grep -n` les citations entrantes AVANT d'annoter.** Une annotation décale les numéros de ligne et
   casse silencieusement les renvois des fichiers déjà terminés. Incident réel : annoter
   `RESEARCH_LOGBOOK.md` a déplacé son entrée Kronos de `:37` à `:51`, ce qui aurait invalidé trois
   renvois (`PHASE2_ROADMAP.md:52`, `DEPENDENCY_MATRIX.md:36`, `BENCHMARKS.md:50`). Tous convertis en
   références par **nom de section** (« Intégration Kronos (Sprint AI-08) »), qui ne dérivent pas.
   **Règle : ne jamais citer un numéro de ligne pointant vers un fichier qu'on édite aussi.**
2. **Remplacer le vocabulaire déclaratif par le vocabulaire mesurable** du §4 ci-dessus.
3. **Justifier chaque dégradation par un `fichier:ligne` vérifiable au `grep`.** Une dégradation sans
   preuve est une opinion ; ce chantier n'en produit pas.
4. **Ajouter une section « Objectif rappelé »** rattachant le document à la finalité : démo pour
   l'entraînement, puis capital réel.
5. **Clore par « Ce que ce document ne promet pas ».** C'est la section qui empêche la relecture
   optimiste de réintroduire la falsification qu'on vient de retirer.

### Règles éditoriales par type de document

- **Document de décisions** → clause de périmètre + corrections ciblées. Pas de réécriture.
- **Document dont les chiffres sont justes** → on le **défend**, on ne le dégrade pas (`BENCHMARKS.md`).
- **Document dont les principes sont justes** → principes conservés **mot pour mot**, seul l'inventaire
  factuel est corrigé (`PROJECT_PHILOSOPHY.md`, `ENGINEERING_RULES.md`).
- **Document d'historique** → erreurs annotées **en place**, jamais supprimées. Un logbook dont on
  effacerait les erreurs ne serait plus un logbook (`RESEARCH_LOGBOOK.md`).
- **Document dont le code existe et est réellement appelé** → le concéder franchement, et dégrader sur
  le **comportement** et non sur l'existence (`AGENTS_SPECIFICATION.md`).

### Contraintes d'outillage

- **Lire le fichier juste avant sa première écriture.** L'état de lecture du harnais ne survit pas à une
  compaction de contexte.
- Écrire par tranches de **~50 lignes / ~4000 caractères maximum**, en s'ancrant sur un marqueur
  `<!-- CHUNK-MARKER -->` que chaque écriture ré-émet ; la dernière le consomme.
- Après une écriture réussie, **ne pas relire** le fichier pour vérifier : l'état est déjà à jour.

## 6. Reprise à froid — les deux fils possibles

- **Reprendre ce chantier docs :** lire §5.4 de `AUDIT_COMPLET_2026-07-31.md`, puis dérouler la file du
  §3 ci-dessus avec la méthode du §5. Rien d'autre n'est nécessaire.
- **Exécuter une correction de code (si et seulement si l'utilisateur a donné le feu vert explicite) :**
  `PLAN_DE_CORRECTION.md` et `AUDIT_COMPLET_2026-07-31.md` se suffisent à eux-mêmes. Chaque lot y porte
  son périmètre, ses fichiers, ses preuves et son critère de sortie. Aucun contexte de conversation
  antérieure n'est requis. Ordre imposé : **Lot 0 d'abord** — il débloque la collecte des tests et de
  `mypy`, sans quoi aucun autre lot n'est vérifiable.

## Ce que ce document ne promet pas

- **Pas un état du code.** Il décrit l'avancement d'un chantier documentaire. L'état du code est dans
  l'audit, et l'audit a une date : le revérifier au `grep` avant d'en tirer une action.
- **Pas une autorisation.** Rien ici ne vaut approbation des Lots 0 à 6.
- **Pas une liste close.** Le Bloc B du §3 est une liste de fichiers **à confronter** à l'audit, pas une
  liste de fichiers dont on sait déjà qu'ils sont faux.
