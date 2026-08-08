# Spécification — Intégration Kronos-mini (Sprint AI-08)

> Ce document répond à "qu'est-ce qu'on fait et où on va" avant d'écrire une ligne de code. Il précède `KRONOS_MINI_IMPLEMENTATION_INSTRUCTIONS.md` (le "comment"). À lire en complément de la section 5 (Kronos) de `GITHUB_INTEGRATION_GUIDE.md`, déjà à jour avec le statut "En évaluation — variante mini uniquement, CPU".

> **Correction du 2026-07-31 sur le cadrage ci-dessus.** Le cadrage est conservé tel quel — c'est
> l'intention. Ses deux renvois sont en revanche caducs :
> - `KRONOS_MINI_IMPLEMENTATION_INSTRUCTIONS.md` **n'existe nulle part dans le dépôt**. Le « comment »
>   annoncé n'a jamais été écrit. `docs/phase2/` ne contient que deux fichiers Kronos :
>   celui-ci et `KRONOS_EVALUATION_REPORT.md`.
> - La section 5 (Kronos) de `GITHUB_INTEGRATION_GUIDE.md` ne porte **pas** le statut « En évaluation »
>   annoncé ici : elle déclare `Status: **ACTIF**`, et nomme le modèle `shiyu-coder/Kronos` — deux
>   points contredits par le tableau ci-dessous. Ce fichier a déjà été traité par le présent chantier
>   mais sa section 5 n'a pas été reprise ; le point est ouvert.

> **État mesuré le 2026-07-31 — à lire avant le reste.** Ce document décrit une **intention de sprint**,
> pas un état livré. L'intention est conservée telle quelle ; seules les affirmations portant sur ce qui
> existe ont été corrigées.
>
> | Élément | Statut | Preuve vérifiable au `grep` |
> |---|---|---|
> | Modèle amont copié dans le dépôt | `[VENDORÉ]` | `src/aegis_trade/providers/kronos/shiyu_model/` — 3 fichiers `.py`, 1 249 lignes. **Aucun fichier `LICENSE` dans le dépôt.** |
> | `KronosAdapter` (couche anti-corruption) | `[ÉCRIT-NON-CÂBLÉ]` | `providers/kronos_adapter.py:14` existe ; **aucune instanciation** dans `src/` ni `scripts/` — seule occurrence : `tests/providers/test_kronos_cache_never_blocks_tick_loop.py:7` |
> | Contenu des prédictions | `[FAÇADE]` | `providers/kronos_adapter.py:67-71` prédit sur `np.random.randn(512, 6) + 100`. Le `data_provider` reçu en `:41` et transmis en `:53` n'est **jamais lu** ; `:59` le dit : « Fetch latest candles from data_provider (stubbed here) » |
> | Signal Kronos consommé par le Council | `[ ]` | `TrendAgent.__init__` (`trend_agent.py:10`) et `PatternAgent.__init__` (`pattern_agent.py:13`) acceptent un `forecaster` optionnel ; rien ne l'injecte. `trend_agent.py:43` et `pattern_agent.py:47` sortent avant tout usage. |
> | Fine-tuning | `[ÉCRIT-NON-CÂBLÉ]` | `providers/kronos/trainer.py` (`KronosFineTuner`) et `providers/kronos/dataset_builder.py` existent ; seul appelant `scripts/run_kronos_smoke_test.py:53` |
> | Critères de succès de la section 4 | `[ ]` | aucun MAPE ni RMSE calculé nulle part dans le dépôt — voir `KRONOS_EVALUATION_REPORT.md` |
>
> **Identité du modèle.** Le modèle réellement vendoré est `NeoQuasar/Kronos-mini`
> (`providers/kronos/model_factory.py:15`). Il est distinct d'`amazon/chronos-t5-mini` **et** de
> `shiyu-coder/Kronos` — le répertoire vendoré s'appelle `shiyu_model/`, d'où la confusion présente
> dans plusieurs documents du projet.

## Objectif rappelé

Ce document sert la finalité du système : **démo réelle sur Deriv pour entraîner le système, puis
capital réel.** Kronos n'a de valeur qu'à ce titre. Un signal prédictif qui n'a jamais été confronté à
une baseline naïve ne prépare pas le passage au capital réel — il le retarde en donnant l'impression
qu'une brique est acquise. Tant que la section 4 n'est pas mesurée, Kronos ne contribue rien à cet
objectif, et ce document décrit un travail à faire, pas un acquis à exploiter.

## 1. Objectif

Ajouter un signal de prédiction de série temporelle réel au système — la seule brique de tout Aegis Quant OS qui prédit littéralement le futur, plutôt que de décrire le présent (Council) ou d'apprendre du passé (Knowledge Base, RL). Kronos-mini (4.1M paramètres, conçu pour l'inférence CPU) regarde les dernières bougies et prédit les prochaines, sur Boom/Crash/Gold spécifiquement — pas en généraliste sur 45 bourses comme le modèle pré-entraîné de base.

**Ce que Kronos-mini n'est pas** : un remplaçant du Council. Sa sortie doit devenir une entrée supplémentaire pour le Trend Agent et le Pattern Agent — la décision finale reste toujours l'agrégation déterministe des 8 votes, jamais directement la prédiction de Kronos.

**État de cet objectif : non atteint.** Le signal existe sous forme de code, il ne circule pas. `providers/kronos_adapter.py:67-71` produit une prédiction à partir de bruit gaussien, et aucun agent ne reçoit d'instance de `KronosAdapter`. Le système ne prédit donc rien aujourd'hui.

## 2. Les 4 leviers pour compenser la taille réduite du modèle

Rappel du raisonnement déjà validé : un modèle à 4.1M de paramètres a structurellement moins de capacité qu'un modèle à 102M (base), mais on n'a pas besoin de généraliste — seulement d'être bon sur 2-3 actifs précis.

Le raisonnement tient. Aucun des quatre leviers n'est réalisé aujourd'hui ; le levier 2 est de plus contredit par le code qui devrait l'implémenter.

1. **Fine-tuning ciblé** — `[ÉCRIT-NON-CÂBLÉ]`. Ré-entraîner Kronos-mini spécifiquement sur l'historique de Boom 1000, Crash, et Gold — pas d'usage brut du modèle pré-entraîné généraliste. Concentre toute la capacité limitée du modèle sur exactement ce dont on a besoin.
   *Mesuré :* la machinerie existe (`providers/kronos/trainer.py`, `providers/kronos/dataset_builder.py`) mais n'est déclenchée que par `scripts/run_kronos_smoke_test.py:53`. Aucun poids fine-tuné n'est produit ni versionné dans le dépôt. Le chargement se fait sur le modèle amont brut (`providers/kronos/model_factory.py:14-15`).
2. **Fenêtre de contexte longue** — `[ ]`, **et contredit par le code**. L'intention était d'exploiter une fenêtre de 2048 bougies, réputée 4× plus longue que small/base.
   *Mesuré :* `providers/kronos/model_factory.py:45` construit le prédicteur avec `max_context=512`. La valeur par défaut de `KronosPredictor` est elle aussi `max_context=512` (`providers/kronos/shiyu_model/kronos.py:484`), et l'adaptateur assemble une fenêtre de 512 points (`providers/kronos_adapter.py:64`). Ce levier n'est donc pas seulement inactif : la configuration actuelle le rend impossible. Rien n'a été mesuré qui justifie 2048 plutôt que 512 — l'affirmation « 4× plus longue » n'a pas de source dans le dépôt et doit être revérifiée contre la documentation amont avant d'être réutilisée.
3. **Ensemble de prédictions** — `[FAÇADE]`. Plusieurs passes d'inférence avec échantillonnage différent (température/top_p variés), agrégées par moyenne ou médiane — réduit le bruit d'une prédiction individuelle, gratuit en paramètres supplémentaires.
   *Mesuré :* `providers/kronos_adapter.py:81` passe bien `sample_count=5`, mais sur le dataframe de bruit de `:67-71`. Un ensemble calculé sur des données aléatoires moyenne du bruit, il ne réduit rien.
4. **Validation systématique par le système existant, jamais confiance aveugle** — `[ ]`. La prédiction brute de Kronos-mini ne doit jamais piloter directement une décision. Elle doit passer par le Pattern Agent/FAISS (AI-01) pour vérifier si des prédictions similaires dans le passé se sont avérées justes, et le RL (AI-04) doit apprendre avec le temps le poids de confiance à accorder à ce signal — potentiellement différent par actif (peut-être fiable sur Gold, pas sur Crash).
   *Mesuré :* `pattern_agent.py:47` retourne avant d'utiliser le forecaster puisque aucun ne lui est fourni. Ce garde-fou n'est donc ni respecté ni violé — il n'est pas exercé.

## 3. Où Kronos-mini s'intègre dans l'architecture existante

Schéma **cible**, non réalisé. Les deux ruptures mesurées sont marquées dans le diagramme.

```text
Données de marché (Boom/Crash/Gold)
        │
        ╳  RUPTURE 1 — kronos_adapter.py:59 « stubbed here » :
        │   le data_provider reçu (:41) n'est jamais lu. L'entrée réelle
        │   est np.random.randn(512, 6) + 100 (:67-71).
        ▼
   Kronos-mini (fine-tuné, ensemble)   ← fine-tuning non exécuté, max_context=512 et non 2048
        │  prédiction + intervalle de confiance
        │
        ╳  RUPTURE 2 — aucune instance de KronosAdapter n'est construite
        │   dans src/ ni scripts/. Les agents sortent en trend_agent.py:43
        │   et pattern_agent.py:47 faute de forecaster.
        ▼
   Trend Agent / Pattern Agent (AI-05) ── consultent aussi FAISS (AI-01) et Knowledge Base (AI-03)
        │
        ▼
   Vote pondéré dans le Council (poids ajustés par le RL, AI-04)
        │
        ▼
   CouncilVerdict → GlobalRiskManager → Ordre
```

Kronos-mini doit se brancher en amont du Pattern Agent, jamais directement sur le chemin de décision. Cohérent avec la contrainte HFT déjà établie pour tous les composants IA du projet : l'inférence tourne en asynchrone/batch, jamais de façon synchrone dans la boucle tick-to-trade.

Cette contrainte-là est la seule du document qui soit tenue par du code : `providers/kronos_adapter.py:85`
déporte l'inférence via `asyncio.to_thread`, et `get_latest_forecast` (`:111`) lit un cache en O(1) sans
toucher au modèle. Le point est couvert par `tests/providers/test_kronos_cache_never_blocks_tick_loop.py`.
Structure correcte, alimentée par du bruit.

## 4. Critères de succès — avant d'activer Kronos en production

Ne pas intégrer sur la foi d'une intuition. Mesurer concrètement, comme déjà décidé dans `GITHUB_INTEGRATION_GUIDE.md`.

Les seuils ci-dessous sont maintenus mot pour mot. La colonne « Mesuré » dit où on en est ; **aucun critère
n'est franchi**, et trois des quatre ne sont pas seulement non franchis, ils ne sont pas calculables en
l'état puisque l'entrée du modèle est aléatoire.

| Critère | Seuil | Mesuré au 2026-07-31 |
|---|---|---|
| MAPE / RMSE vs baseline naïve (persistence, dernière valeur connue) | Doit battre la baseline, pas juste être "raisonnable" dans l'absolu | `[ ]` — aucun MAPE ni RMSE dans le dépôt. Aucune baseline naïve implémentée. `KRONOS_EVALUATION_REPORT.md` ne rapporte que du coût, jamais de la qualité. |
| Latence d'inférence (CPU, batch) | Documentée, doit rester compatible avec un usage asynchrone (pas de seuil dur type <20ms — ce n'est pas dans le chemin critique) | `[ ]` — non mesurée sur données réelles. Le chiffre disponible provient d'un entraînement sur bougies de test, pas d'une inférence de production. |
| RAM utilisée | < 4 GB (déjà noté dans `GITHUB_INTEGRATION_GUIDE.md`), à re-confirmer sur le matériel réel (12 GB total, ~2 GB dispo au repos) | Seul critère avec une mesure : ~917 Mo de crête relevés lors du smoke test (voir `RESEARCH_LOGBOOK.md`, section « Intégration Kronos (Sprint AI-08) »). Sous le seuil de 4 GB, mais **au-dessus** de la contrainte « <300 Mo » énoncée ailleurs dans le projet — contradiction non tranchée à ce jour. |
| Impact sur le Win Rate du Council quand le signal Kronos est activé vs désactivé | Comparaison A/B nécessaire — le signal doit démontrer un gain mesurable, pas juste "exister" | `[ ]` — l'A/B est impossible : il n'existe pas d'état « activé ». Aucun forecaster n'est injecté dans le Council. |

**Si Kronos-mini ne bat pas la baseline naïve après fine-tuning**, la décision par défaut est de ne pas l'activer en production plutôt que de l'intégrer quand même "parce qu'on a fait le travail" — cohérent avec la discipline scientifique déjà appliquée ailleurs dans le projet (le même principe qui a fait annuler l'ancien Council LLM).

Cette clause reste la bonne, et elle n'a jamais été exercée : on ne peut pas échouer à battre une baseline
qu'on n'a pas construite. L'ordre de travail correct est donc **baseline naïve d'abord, fine-tuning
ensuite** — pas l'inverse.

## 5. Séquencement avec le live-trading en démo

> **Correction du 2026-07-31.** La rédaction initiale affirmait que le live-trading en démo
> (`scripts/run_live_paper_trading.py`) « n'attend pas » Kronos pour démarrer, « le Council à 8 agents
> fonctionne déjà de façon autonome ». Faux sur les deux points : le script est **mort à l'import**.
> `scripts/run_live_paper_trading.py:10` importe `aegis_trade.application.council.aggregator`, module
> inexistant — le fichier réel est `application/council/vote_aggregator.py`. Le Council ne tourne donc
> pas de façon autonome, il ne démarre pas du tout par ce chemin.

**Préalable, hors périmètre de ce sprint mais bloquant pour lui :** rétablir le démarrage du
live-trading en démo. Tant que ce point n'est pas réglé, l'étape 4 ci-dessous est inatteignable, quel
que soit l'état de Kronos.

Séquencement visé, Kronos s'ajoutant en parallèle du live plutôt qu'en préalable :

1. Construire la **baseline naïve** (persistence) et l'appareil de mesure MAPE/RMSE. Sans elle, la
   section 4 n'a aucun critère opposable. Premier travail, avant tout entraînement.
2. Fine-tuning et validation de Kronos-mini en offline (sur données historiques déjà disponibles), pas
   besoin d'attendre le live pour ça. Préalable technique : brancher un vrai `data_provider` dans
   `providers/kronos_adapter.py:41,53`, aujourd'hui reçu puis ignoré.
3. Une fois les critères de succès de la section 4 validés, brancher le signal dans le Trend/Pattern
   Agent — c'est-à-dire construire un `KronosAdapter` et l'injecter, ce que rien ne fait aujourd'hui.
4. Le live-trading en démo sert alors doublement d'objectif : accumuler les 200 trades/2 semaines déjà
   exigés pour la validation globale, **et** servir de terrain d'entraînement en conditions réelles pour
   affiner la confiance du RL envers le signal Kronos au fil du temps.

## 6. Ce qui reste hors scope pour ce sprint

- Pas de version small/base de Kronos — uniquement mini, pour rester CPU-only. *Tenu :* `model_factory.py:14-15` charge `NeoQuasar/Kronos-mini` et `NeoQuasar/Kronos-Tokenizer-base`, sur `device = "cpu"` (`model_factory.py:20`).
- Pas de fine-tuning continu automatique en production pour l'instant — le fine-tuning est un processus offline déclenché manuellement, pas un cycle hebdomadaire automatisé comme le RL (à réévaluer plus tard si les résultats sont bons).
- Pas de News Agent réactivé en parallèle — reste en stub neutre comme décidé en AI-05, sans lien avec ce sprint.

## 7. Dette ouverte par le vendoring — hors scope produit, pas hors scope juridique

`src/aegis_trade/providers/kronos/shiyu_model/` contient 1 249 lignes de code amont copiées dans le
dépôt, **sans fichier `LICENSE`**. Aucun ADR ne couvre cette décision de vendoring. Le point est
indépendant de la valeur prédictive du modèle : il resterait à traiter même si Kronos était abandonné
demain, et il doit l'être avant toute distribution ou publication du dépôt.

## Ce que ce document ne promet pas

- **Pas un signal de prédiction disponible.** Rien dans le système ne prédit quoi que ce soit
  aujourd'hui : l'unique chemin d'inférence lit `np.random.randn` (`providers/kronos_adapter.py:67-71`)
  et n'est de toute façon jamais instancié hors test.
- **Pas une évaluation du modèle.** Aucune métrique de qualité n'existe. La présence de `trainer.py` et
  d'un smoke test ne dit rien de la capacité prédictive de Kronos-mini sur Boom/Crash/Gold.
- **Pas la fenêtre de 2048 bougies.** La configuration effective est `max_context=512`
  (`providers/kronos/model_factory.py:45`). Le levier 2 de la section 2 décrit une intention, pas la
  configuration en place.
- **Pas un feu vert de production.** Les quatre critères de la section 4 sont non franchis, et trois ne
  sont pas calculables en l'état. Activer Kronos avant de les mesurer serait exactement l'erreur que la
  section 4 avait été écrite pour empêcher.
- **Pas une remise en cause de l'intention.** Le raisonnement des sections 1 à 4 reste valable. Ce
  document a été corrigé sur son état déclaré, pas sur son objectif.

