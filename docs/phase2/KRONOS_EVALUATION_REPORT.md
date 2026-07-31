# Kronos-mini CPU Evaluation Report

> **État mesuré le 2026-07-31 — à lire avant le reste.** Ce rapport est un **rapport de coût**, pas une
> évaluation de modèle. Il mesure de la RAM et des secondes ; il ne mesure **aucune qualité de
> prédiction**. Aucun MAPE, aucun RMSE, aucune baseline naïve n'existe nulle part dans `src/`,
> `scripts/` ni `tests/`. Un modèle prédictif dont on ne connaît que le prix n'est pas évalué.
>
> Les chiffres eux-mêmes ne sont pas contestés : ils ont été relevés. Ce qui est corrigé, c'est **ce sur
> quoi ils ont été relevés** — des données synthétiques dans les deux cas.
>
> | Affirmation d'origine | Statut | Preuve vérifiable au `grep` |
> |---|---|---|
> | Nom du modèle `shiyu-coder/Kronos-mini` | faux | Le modèle chargé est `NeoQuasar/Kronos-mini` (`providers/kronos/model_factory.py:15`), tokeniseur `NeoQuasar/Kronos-Tokenizer-base` (`:14`). `shiyu-coder/Kronos` est un dépôt distinct ; le répertoire vendoré s'appelle `shiyu_model/`, d'où la confusion. |
> | Chiffres d'inférence (latence, mémoire) | `[FAÇADE]` | L'unique chemin d'inférence prédit sur `np.random.randn(512, 6) + 100` (`providers/kronos_adapter.py:67-71`). Le `data_provider` reçu (`:41`) et transmis (`:53`) n'est jamais lu — `:59` : « Fetch latest candles from data_provider (stubbed here) ». |
> | Isolation asynchrone du `tick_loop` | `[VALIDÉ]` | Seule affirmation du document tenue par du code **et** couverte par un test : `providers/kronos_adapter.py:85` (`asyncio.to_thread`), `:111` (lecture de cache O(1)), `tests/providers/test_kronos_cache_never_blocks_tick_loop.py`. |
> | Chiffres de fine-tuning (RAM, temps/epoch) | `[ÉCRIT-NON-CÂBLÉ]` | Mesurés sur une marche aléatoire géométrique de graine fixe, pas sur des bougies : `scripts/run_kronos_smoke_test.py:24-26` (`np.random.seed(42)`, `np.random.normal`, `np.exp(np.cumsum(...))`), `:66` (`generate_dummy_data(1000)` étiqueté « GOLD »). |
> | Extrapolation à 105 000 bougies | `[ ]` | Jamais exécutée. Aucun script, aucun log, aucun artefact de run complet dans le dépôt. C'est un calcul de coin de table, pas une mesure. |
> | Qualité prédictive du modèle | `[ ]` | Zéro occurrence de MAPE ou RMSE dans `src/`, `scripts/`, `tests/`. `providers/qlib/trainer.py:32` le dit pour sa propre couche : « Dans un scénario complet, on retournerait ici les métriques ». |

## Objectif rappelé

Ce document sert la finalité du système : **démo réelle sur Deriv pour entraîner le système, puis
capital réel.** Un rapport de faisabilité de coût répond à « peut-on se permettre de faire tourner ce
modèle ? ». Il ne répond pas à « ce modèle rapporte-t-il quelque chose ? ». Or seule la seconde question
autorise le passage au capital réel. En l'état, ce rapport dit qu'on peut payer pour un signal dont on
ignore la valeur — c'est un feu vert d'infrastructure, jamais un feu vert de production.

Ce rapport documente les métriques de coût CPU observées pour l'entraînement et l'inférence de
`NeoQuasar/Kronos-mini` sur l'infrastructure actuelle, **sur données synthétiques dans les deux cas**.

## Contexte
- **Modèle** : `NeoQuasar/Kronos-mini` (`providers/kronos/model_factory.py:15`). La rédaction initiale
  écrivait `shiyu-coder/Kronos-mini` — nom inexistant, croisement entre le dépôt amont
  `shiyu-coder/Kronos` et le modèle réellement téléchargé.
- **Provenance « Modèle AAAI 2026 natif finance »** : affirmation reprise de l'amont, **sans source dans
  le dépôt**. Aucun ADR, aucun lien, aucun papier référencé. À vérifier avant réutilisation.
- **Tokenisation** : `KronosTokenizer` via `BSQuantizer` (discrétisation OHLCV).
- **Hardware** : CPU local (sans CUDA) — cohérent avec `providers/kronos/model_factory.py:20`
  (`self.device = "cpu"`).
- **Objectif de la campagne de mesure** : valider la faisabilité **de coût** du fine-tuning et de
  l'inférence en arrière-plan sans bloquer la boucle de trading. Cet objectif-là est atteint. Il ne
  couvre pas la capacité prédictive, qui n'a jamais été mesurée.

## Inférence (Background Task) — `[FAÇADE]`

Chiffres relevés, mais sur du bruit gaussien. Ils mesurent le coût de traverser le modèle, pas le coût
de prédire un marché.

- **Latence par requête** : ~500 ms à 1500 ms (selon `pred_len` et `sample_count`).
  *Mesuré sur :* `providers/kronos_adapter.py:67-71` — `np.random.randn(512, 6) + 100`. La latence reste
  indicative pour le dimensionnement : la charge de calcul dépend de la forme du tenseur (512 × 6) et de
  `sample_count=5` (`:81`), pas du contenu. Elle n'a en revanche jamais été relevée sur le chemin de
  production, puisque ce chemin n'existe pas.
- **Mémoire** : ~630 MB.
- **Isolation** : **`[VALIDÉ]`**. Totalement isolée via `asyncio.to_thread`
  (`providers/kronos_adapter.py:85`). La boucle de prix `tick_loop` n'est pas bloquée. `get_latest_forecast`
  (`:111`) lit le cache en O(1) sans toucher au modèle. Couvert par
  `tests/providers/test_kronos_cache_never_blocks_tick_loop.py`.
  C'est le seul point de ce rapport qui soit à la fois vrai, prouvé et testé — la structure
  anti-blocage est correcte. Elle est simplement alimentée par du bruit.

**Réserve d'échelle non levée.** Ces chiffres viennent d'un refresh sur un seul symbole. La boucle
itère sur `symbols` en séquentiel (`providers/kronos_adapter.py:58`) avec un intervalle par défaut de
60 s (`:20`, `refresh_interval_sec: int = 60`). À 1500 ms par symbole le budget tient pour quelques
actifs ; rien n'a été mesuré au-delà, et aucun test ne couvre le cas où la boucle dépasse son
intervalle — `:108` se contente d'un `max(1.0, ...)` qui masquerait la saturation au lieu de la signaler.

## Fine-tuning (Offline) — `[ÉCRIT-NON-CÂBLÉ]`

- **Dataset de test** : 1000 bougies OHLCV **générées** (stride=10).
  *Précision indispensable :* « générées » veut dire marche aléatoire géométrique de graine fixe —
  `scripts/run_kronos_smoke_test.py:24-26` : `np.random.seed(42)`, puis
  `close = 1000 * np.exp(np.cumsum(np.random.normal(0, 0.001, rows)))`. Ces séries sont étiquetées
  `"GOLD"` en `:66`, ce qui est trompeur : aucune bougie Gold réelle n'a été chargée. Le `stride=10` est
  exact (`providers/kronos/dataset_builder.py:81`), mais la fenêtre utilisée est
  `lookback_window=90, predict_window=10` (`run_kronos_smoke_test.py:68`) — ni 512 ni 2048.
- **RAM initiale** : ~568 MB
- **RAM en pic** : ~917 MB (delta : +351 MB)
- **Temps par epoch** : ~15 s pour 1000 lignes (total incluant preprocessing/validation : ~49 s).
- **Métriques de qualité produites par ce run** : aucune exploitable. `run_kronos_smoke_test.py:80`
  récupère bien un `metrics` de `trainer.train(...)`, mais `:89` se borne à le logger. Aucune valeur
  n'est archivée, comparée à quoi que ce soit, ni reportée ici. Ce qui a survécu du run, ce sont deux
  chiffres de RAM et un chronomètre.

**Ce que le run n'établit pas :** qu'un entraînement sur du bruit converge vers quoi que ce soit. La
perte peut baisser sur une marche aléatoire sans qu'aucune structure ne soit apprise — c'est le
comportement attendu d'un modèle qui mémorise. Aucune conclusion sur la capacité d'apprentissage ne
peut être tirée de ce smoke test ; il valide la plomberie, rien d'autre.

### Extrapolation pour un run complet — `[ ]`, jamais exécutée

Le calcul ci-dessous est conservé tel quel : c'est une estimation légitime pour dimensionner du
matériel. Il n'est **pas** une mesure et ne doit jamais être cité comme telle.

Pour un dataset réel de 105 000 bougies (ex : Boom_1000) :
- Temps d'entraînement CPU pour 1 epoch estimé à environ **25-30 minutes** par actif.
- Consommation RAM maximale estimée autour de **1.5 GB - 2 GB**.

*Mesuré :* rien. Aucun run sur données réelles n'a été lancé, aucun artefact de poids fine-tunés n'est
présent ni versionné dans le dépôt. L'extrapolation est linéaire en nombre de lignes, hypothèse jamais
vérifiée pour ce modèle. Le préalable technique est le même que pour l'inférence : brancher un vrai
`data_provider` (`providers/kronos_adapter.py:41,53`, aujourd'hui reçu puis ignoré).

## Conclusion — corrigée dans sa portée

Rédaction d'origine : « Le fine-tuning CPU est parfaitement réaliste en tâche de fond. Le smoke test
confirme que le script d'entraînement est non-bloquant et que l'empreinte mémoire est suffisamment
faible pour tourner en parallèle du moteur de trading. »

Ce qui tient : le coût est soutenable. ~917 Mo de crête restent sous le seuil de 4 GB retenu dans les
critères de succès de `KRONOS_MINI_INTEGRATION_SPEC.md` (section « Critères de succès »), et
l'inférence ne bloque pas la boucle de trading — prouvé, testé.

Ce qui ne tient pas :
- **« non-bloquant » vaut pour l'inférence, pas pour l'entraînement.** La preuve d'isolation
  (`providers/kronos_adapter.py:85`) porte sur `_refresh_loop`. Le fine-tuning est lancé par un script
  autonome (`scripts/run_kronos_smoke_test.py`) qui ne tourne jamais en parallèle du moteur : aucune
  exécution concurrente des deux n'a été mesurée. La phrase généralise une mesure à un cas non testé.
- **« empreinte suffisamment faible » est en contradiction non tranchée** avec la contrainte « <300 Mo »
  énoncée ailleurs dans le projet. 917 Mo passe un seuil et échoue à l'autre. Le point est ouvert.
- **« parfaitement réaliste » porte sur le coût seul.** Rien dans ce rapport ne dit que le fine-tuning
  vaut la peine d'être lancé. Décider de l'exécuter sur cette base reviendrait à financer un
  entraînement de 25-30 minutes par actif sans critère d'arrêt ni critère de succès.

**Ordre de travail qui découle de ce rapport :** construire d'abord la baseline naïve (persistence,
dernière valeur connue) et l'appareil de mesure MAPE/RMSE, puis seulement fine-tuner. Un entraînement
lancé avant la baseline produit un modèle qu'on ne saura pas juger — exactement la situation que ce
rapport documente aujourd'hui.

## Ce que ce document ne promet pas

- **Pas une évaluation du modèle.** Le titre dit « Evaluation Report » ; le contenu est un rapport de
  faisabilité de coût. Aucune métrique de qualité prédictive n'y figure, et aucune n'existe dans le
  dépôt.
- **Pas une mesure sur données réelles.** Inférence et fine-tuning ont tous deux été chronométrés sur
  des séries synthétiques (`providers/kronos_adapter.py:67-71` ; `scripts/run_kronos_smoke_test.py:24-26`).
  L'étiquette `"GOLD"` du smoke test ne désigne aucune donnée de marché.
- **Pas une preuve que Kronos-mini apprend quoi que ce soit.** Une perte qui baisse sur une marche
  aléatoire de graine fixe n'est pas un signal.
- **Pas un feu vert de production.** Un seul des quatre critères de succès de
  `KRONOS_MINI_INTEGRATION_SPEC.md` dispose d'une mesure — la RAM. Les trois autres ne sont pas
  calculables tant que l'entrée du modèle est aléatoire.
- **Pas une remise en cause des chiffres.** Les valeurs relevées sont conservées telles quelles. Seul
  leur périmètre de validité a été corrigé.

