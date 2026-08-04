# HANDOFF — reprise par un autre agent (Antigravity)

*Écrit le 2026-08-04. Ce fichier n'est PAS gitignoré (contrairement à
`docs/HANDOFF.md`) : il doit survivre à la reprise. `docs/HANDOFF.md` reste la
source d'instruction d'origine — le lire aussi, il contient les tableaux de
métriques SIG-02 à transcrire.*

---

## 0. Résumé en trois phrases

Les étapes 1 et 2 du plan SIG-02 sont **mesurées, terminées, vérifiées**. Il
reste **l'étape 3 : écrire `docs/ADR/0024-*.md`** puis mettre à jour
`docs/BACKLOG.md`. Rien n'a été commité — l'arbre de travail contient 4 fichiers
modifiés et 3 fichiers non suivis qui sont le livrable.

---

## 1. Contexte : ce que la campagne SIG-02 a produit

Branche `claude-code-takeover`, dernier commit `2618c50`, rien n'est poussé.

Deux entraînements LightGBM (300 arbres, 75000 barres M1, split chronologique
70/30, seuils d'entrée dérivés du coût selon l'ADR 0018) sur Crash 1000 h5 et
Boom 1000 h10. **Score 0/100 dans les deux cas, 4 campagnes de validation sur 4
en échec.** Les tableaux détaillés sont dans `docs/HANDOFF.md`, section
« Résultat SIG-02 — à transcrire dans l'ADR 0024 ». Ils doivent être recopiés
**intégralement** dans l'ADR : `.validation_registry/` et `data/` ne sont pas
versionnés, donc un chiffre hors ADR n'existe pas hors de cette machine.

**Le vrai sujet n'est pas l'échec, c'est sa cause.** L'étape « Recherche de
features » du pipeline de `CLAUDE.md` n'a jamais tourné sur ces deux séries :
LightGBM a été entraîné sur 23 features dont le pouvoir prédictif n'avait jamais
été mesuré. Les ADR 0018→0023 ont travaillé un seul terme de l'inégalité — le
coût — avec rigueur. L'autre terme, *le signal existe-t-il*, n'avait jamais été
posé. Les étapes 1 et 2 ci-dessous le posent.

---

## 2. ÉTAPE 1 — TERMINÉE. Décomposition P&L brut / coût

**Livrable** : `scripts/diagnose_pnl_decomposition.py` (non suivi) +
`tests/scripts/test_pnl_decomposition.py` (19 tests, tous verts).

Le script rejoue le backtest du segment de test et sépare le P&L en deux termes.
Il tourne deux fois : `actual` (coûts réels) et `frictionless` (coût broker mis à
zéro **en gardant** le seuil dérivé du coût réel — `MLStrategy.from_cost_model`
refuse un coût nul, donc les deux ne peuvent pas être passés à 0 ensemble).
Le second run contrôle que le sizer ne distord pas le verdict.

### Résultats mesurés (les deux runs sortent en code 0)

| | Crash 1000 h5 | Boom 1000 h10 |
|---|---|---|
| `--commission-rate` | 0.00003725 | 0.00005315 |
| coût A/R | 0.745 bps | 1.063 bps |
| seuil d'entrée | 0.000074 | 0.000106 |
| exécutions | 3618 | 3843 |
| turnover cumulé | 339 781 042.71 | 344 843 999.62 |
| **coût cumulé** | **12 656.84 (+12.6568 %)** | **18 328.46 (+18.3285 %)** |
| **BRUT** | **−2 315.29 (−2.3153 %)** | **+1 461.24 (+1.4612 %)** |
| brut bps / exécution | −0.0681 | +0.0424 |
| **t du brut** | **−0.71** | **+0.54** |
| net réalisé | −14 972.13 (−14.9721 %) | −16 867.22 (−16.8672 %) |
| brut frictionless | −2 409.36 (−2.4094 %), t −0.68 | +1 682.90 (+1.6829 %), t +0.56 |
| réconciliation | 1.89e−10 / 2.04e−10 | 1.46e−11 / 1.31e−10 |

Rapports JSON complets, mis à l'abri de `/tmp` :
`docs/measures/sig-02/decomp_crash_h5.json`,
`docs/measures/sig-02/decomp_boom_h10.json`.

### Lecture

- **Crash 1000 : brut négatif. Pas d'edge directionnel.** Le coût n'était pas le
  problème ; l'horizon, la marge et le modèle ne le sont pas non plus.
- **Boom 1000 : brut positif de SIGNE SEULEMENT.** `|t| = 0.54` — le brut n'est
  **pas distinguable de zéro**. Ne pas écrire « un edge existe mais le coût le
  mange » : ce serait refaire exactement l'erreur du `dir_acc 0.7733` in-sample
  que `docs/HANDOFF.md` documente. Pour mémoire, même réel, l'edge vaudrait
  +0.0847 bps par aller-retour contre 1.0630 bps de péage, soit **12.5x** — non
  finançable.
- **Augmenter la taille des positions ne peut rien changer** : brut et commission
  sont tous deux linéaires en notionnel, leur rapport est invariant à la taille.
  La seule piste théorique restante serait *moins d'allers-retours à temps de
  marché égal* — à mesurer, pas à supposer.
- L'estimation au dos de l'enveloppe du handoff précédent était juste sur le coût
  (12.66 % / 18.33 % mesurés contre 12.8 % / 19.4 % estimés) et **trop optimiste
  de 40 % sur le brut Boom** (+1.46 % contre +2.5 %).

### Une réserve à connaître

Le `t` calculé ici est une **borne supérieure optimiste** : il traite les
exécutions comme indépendantes alors qu'elles sont corrélées. Un `|t|` qui ne
franchit pas 2 sur la borne optimiste ne le franchira sous aucune correction.
Le seuil ne sert donc qu'à **clore**, jamais à conclure positivement.

### Reproduire

```bash
PYTHONPATH=scripts .venv/bin/python scripts/diagnose_pnl_decomposition.py \
  --symbol CRASH1000 --parquet crash1000.parquet --horizon 5 \
  --commission-rate 0.00003725 --json-out /tmp/decomp_crash_h5.json \
  > /tmp/decomp_crash_h5.log 2>&1

PYTHONPATH=scripts .venv/bin/python scripts/diagnose_pnl_decomposition.py \
  --symbol BOOM1000 --parquet boom1000.parquet --horizon 10 \
  --commission-rate 0.00005315 --json-out /tmp/decomp_boom_h10.json \
  > /tmp/decomp_boom_h10.log 2>&1
```

~14 min chacun. **Garder `--log-level WARNING` (défaut)** : INFO produit ~34 Mo
par run. Rediriger hors du dépôt.

**Un détail à savoir** : les fichiers `.log` actuellement dans `/tmp` ont été
produits **avant** la dernière réécriture du bloc VERDICT du script (qui a ajouté
la branche « positif mais non distinguable de zéro » pour Boom). Les JSON sont à
jour et corrects ; seul le texte imprimé est périmé. Relancer les deux commandes
si l'on veut le verdict imprimé à jour — les chiffres, eux, ne bougeront pas.

---

## 3. ÉTAPE 2 — TERMINÉE. Audit puis exécution de l'Alpha Research

### 3.1 L'audit (à faire AVANT toute mesure — c'était l'ordre imposé)

Le seul rapport d'Alpha Research existant
(`data/reports/alpha_research_BTCUSD_20260727_012740.json`) affiche `ic_mean
0.9645` pour `macd_signal`. **Verdict de l'audit : fuite de cible dans le jeu de
démonstration, pas un défaut du moteur.** `scripts/generate_dummy_features.py`
écrit le rendement de demain plus un bruit `N(0, 0.005)` dans cette colonne. La
corrélation théorique attendue, `0.02 / sqrt(0.02² + 0.005²) = 0.9701`, colle au
0.9645 observé. Le `macd_signal` du vrai `TechnicalFeatureExtractor` est une
authentique ligne de signal MACD — vérifié, il n'est pas en cause.

**Mais le moteur avait trois vrais défauts, corrigés :**

1. **Il calculait Pearson en se disant Spearman.** Sur des rendements à queues
   épaisses, Pearson lit comme du signal ce qui est une poignée de barres.
2. **Aucun test de significativité.** Un IC sans budget de dispersion ne peut pas
   répondre « y a-t-il un signal » — même faute que lire un `dir_acc` in-sample
   comme une validation.
3. **Le chevauchement des rendements forward était ignoré.** Les lignes t et t+1
   partagent N−1 barres de leur fenêtre forward. Lire un `t` sur le compte brut
   à l'horizon 10 le gonfle d'un facteur ~√10 : ça transforme du bruit en
   « découverte ».

Fichiers modifiés :

- `src/aegis_trade/domain/research.py` — bloc de significativité ajouté au
  `FeatureScore` gelé : `ic_spearman`, `observations`, `effective_observations`,
  `ic_t_stat`, `is_significant`. **Tous avec valeur par défaut nulle /
  non-significative**, pour qu'un producteur qui ne les calcule pas ne puisse pas
  revendiquer silencieusement une significativité.
- `src/aegis_trade/infrastructure/research/research_engine.py` — vrai Spearman
  plein échantillon, rolling sur les rangs, helpers `_effective_observations`
  (`observations // horizon`) et `_rank_ic_t_stat`
  (`t = ic·sqrt((n−2)/(1−ic²))` sur l'échantillon **effectif**), et `final_score`
  mis à 0 quand l'IC ne franchit pas sa propre barre d'erreur.
- `tests/test_research_engine.py` — 3 tests préexistants conservés, **11 ajoutés**
  (14 verts). Le test décisif est
  `test_ic_is_invariant_under_a_monotone_transform` : sous un cube, Spearman est
  invariant, Pearson ne l'est pas. Vérifié qu'il a des dents par sonde directe —
  Pearson bouge de −0.0880 à −0.0222, Spearman reste exactement −0.0953, donc
  l'ancienne implémentation échouerait ce test.

**Une décision de conception à ne pas défaire** : quand `|IC| = 1`, le `t` est
infini. Le code **borne** l'IC à ±(1 − 1e−12) au lieu de renvoyer 0. Renvoyer 0
enterrerait la fuite de cible tout en bas du classement — exactement ce que
l'audit existe pour attraper. Un `t` énorme mais fini la garde en haut, visible.

### 3.2 La mesure

**Livrable** : `scripts/run_feature_research.py` (non suivi). Mesure l'IC sur
train et test **séparément**, même découpage chronologique 70/30 que SIG-02.
C'est le seul garde-fou contre les features de NIVEAU (`ema_50`, `bb_upper`,
`typical_price`) : sur une série qui dérive, un niveau se corrèle au temps donc à
tout ce qui a une tendance. Un IC de niveau né de la dérive change de signe ou
s'effondre hors échantillon — la comparaison train/test le démasque sans test de
stationnarité supplémentaire.

Une feature « SURVIT » si elle est significative sur le TEST **et** de même signe
que sur le train. Le classement est trié sur |IC test| : trier sur le train
reviendrait à sélectionner sur les données d'ajustement, la faute même sous
instruction.

### Résultat : **0 / 25 features survivent, dans les quatre cas**

(Crash h5, Crash h10, Boom h5, Boom h10.)

Le `|t|` maximum observé **n'importe où** est **1.87** (Boom h10,
`typical_price`), sous le seuil de 2. Rapports complets, mis à l'abri de `/tmp` :
`docs/measures/sig-02/features_crash.json`,
`docs/measures/sig-02/features_boom.json`.

Trois observations qui méritent d'entrer dans l'ADR :

- **Le haut de tous les classements est systématiquement occupé par des NIVEAUX
  de prix** (`ema_*`, `bb_*`, `typical_price`, `median_price`), avec un IC de
  même signe sur train et test. C'est l'artefact de dérive attendu — démasqué
  comme prévu par le cadrage train/test, et de toute façon non significatif.
- **`rel_volume` et `vwap` reportent `n_eff = 0`, `volume_sma_20` a un IC
  exactement nul.** Cause vérifiée : la colonne `volume` des deux parquets vaut
  **0.0 partout** (`nunique = 1`, min = max = 0, aucun NaN) — les indices
  synthétiques Deriv n'ont pas de volume. **Trois des 23 features fournies à
  LightGBM ne portaient donc aucune information.** C'est un constat de qualité de
  données, pas un bug, et il a sa place dans l'ADR.
- Aucune correction pour tests multiples n'est appliquée. Même si une feature
  avait franchi le seuil, 25 features × 2 horizons produisent des `|t| > 2` par
  hasard seul. Le résultat ici est négatif, donc la question ne se pose pas.

### Reproduire

```bash
PYTHONPATH=scripts .venv/bin/python scripts/run_feature_research.py \
  --symbol CRASH1000 --parquet crash1000.parquet --horizons 5 10 \
  --json-out /tmp/features_crash.json

PYTHONPATH=scripts .venv/bin/python scripts/run_feature_research.py \
  --symbol BOOM1000 --parquet boom1000.parquet --horizons 5 10 \
  --json-out /tmp/features_boom.json
```

Rapide (~1 min chacun, aucun modèle n'est entraîné).

---

## 4. La question ouverte du handoff — TRANCHÉE

`docs/HANDOFF.md` demandait de vérifier avant de se fier aux chiffres pourquoi
`hold_out` et `benchmark` reportent un `net_return` identique à la décimale
(−14.9721 % sur Crash). **Réponse : parce que c'est littéralement le même
backtest.**

`scripts/train_qlib_model.py:210` passe `ListDataFeed(test_sets)` — **le même
flux à tous les validateurs**. `HoldOutValidator` appelle
`backtester.run(symbol, timeframe)` sur ce flux entier ;
`BenchmarkValidator` fait le même appel puis ajoute un Buy & Hold pour l'alpha et
le beta. Le `details: {'ratio': config.test_ratio}` de `hold_out` est une
métadonnée **décorative : elle ne découpe rien**.

Conséquences, à écrire telles quelles dans l'ADR :

- **Les chiffres sont valides et bien hors échantillon.** Le segment de test de
  22500 barres n'a jamais servi à l'entraînement. `−14.9721 %` est un vrai
  rendement net hors échantillon. Le verdict de rejet tient.
- **Mais `HoldOutValidator` ne fait pas ce que son nom annonce** : il ne réserve
  aucun sous-segment, il évalue tout ce qu'on lui donne. Idem pour
  `WalkForwardValidator`, qui découpe le flux en 5 blocs chronologiques
  **sans jamais réentraîner** la stratégie : c'est un contrôle de stabilité
  inter-période, pas un walk-forward au sens propre.
- **À ajouter au backlog comme dette** (`DEBT-03` proposé) : soit les validateurs
  honorent leurs ratios, soit ils sont renommés. Un nom qui ment sur ce qu'il
  mesure est plus dangereux qu'une métrique absente.

---

## 5. CE QU'IL RESTE À FAIRE — étape 3

### 5.1 Écrire `docs/ADR/0024-<slug>.md`

Le dernier ADR est `0023-signal-persistence-exit-validated.md`. Slug suggéré :
`0024-sig-02-rejected-feature-research-skipped.md`.

**Format d'en-tête, copié sur l'ADR 0023** :

```markdown
# ADR 0024 — <titre>

- **Statut** : Accepté
- **Date** : 2026-08-04
- **Contexte technique** : <une ligne>
- **Dépend de** : ADR 0018, 0020, 0021, 0023
- **Résout** : SIG-02

## Contexte
...
```

**Contenu obligatoire** (exigé mot pour mot par `docs/HANDOFF.md`, section
« Étape 3 ») :

1. **Les tableaux de métriques SIG-02, intégralement** — les recopier depuis
   `docs/HANDOFF.md` : le tableau comparatif des deux runs, les 4 campagnes de
   Crash, les 4 campagnes de Boom, les rendements par fold. Ne rien résumer :
   ces chiffres n'existent nulle part ailleurs de façon versionnée.
2. **La décomposition brut / coût de l'étape 1** — le tableau de la section 2
   ci-dessus, avec les `t`, la réconciliation, et l'argument d'invariance
   d'échelle (augmenter la taille ne peut pas aider).
3. **Le résultat de l'Alpha Research de l'étape 2** — le 0/25 aux quatre cas, le
   `|t|` max de 1.87, l'explication de la fuite 0.9645, les trois défauts du
   moteur corrigés, et le constat `volume = 0`.
4. **L'étape de pipeline sautée** — `docs/HANDOFF.md` la désigne comme « la
   conclusion la plus utile de la campagne ». C'est la section qui compte le
   plus : montrer que « Recherche de features » a été enjambée, que les ADR
   0018→0023 n'ont travaillé qu'un seul terme de l'inégalité, et que les deux
   mesures indépendantes (P&L et IC) concordent aujourd'hui pour dire qu'il n'y
   a pas de signal mesurable à ces horizons sur ces séries.
5. **La réserve de la section 4** sur `hold_out` / `walk_forward`.

**Ce que l'ADR ne doit PAS dire** : « il n'y a pas d'edge sur ces instruments ».
Ce qui est démontré, c'est qu'**aucune des 23 features testées ne porte de
relation mesurable au rendement futur aux horizons 5 et 10**, et que le brut du
modèle qui s'appuie dessus n'est pas distinguable de zéro. C'est un rejet de
l'hypothèse testée, pas un théorème sur l'instrument.

### 5.2 Mettre à jour `docs/BACKLOG.md`

- `SIG-02` : `EN COURS` → **`REJETÉ`**, avec renvoi à l'ADR 0024. La section est
  vers la ligne 128.
- `KRO-01` : reste **`SUSPENDU`**. Un meilleur modèle sur des features au pouvoir
  prédictif mesuré nul est le raisonnement déjà réfuté par l'ADR 0019.
- **Ajouter « Recherche de features » comme mission BLOQUANTE** (`FE-01`). Sans
  elle, la même omission se reproduira : c'est le point entier de la campagne.
  L'outil est maintenant correct et testé, il n'y a plus d'excuse.
- Optionnel : `DEBT-03` pour les validateurs qui mentent sur leur nom
  (section 4).

### 5.3 Commit

**Rien n'a été commité.** Arbre de travail :

```
 M .gitignore                                              (modifié AVANT cette session)
 M src/aegis_trade/domain/research.py
 M src/aegis_trade/infrastructure/research/research_engine.py
 M tests/test_research_engine.py
?? scripts/diagnose_pnl_decomposition.py
?? scripts/run_feature_research.py
?? tests/scripts/test_pnl_decomposition.py
?? docs/HANDOFF_ANTIGRAVITY.md                             (ce fichier)
?? docs/measures/sig-02/*.json                             (4 rapports de mesure)
?? .validation_registry/val_2026080*_MLStrategy_score_0.json   (3 fichiers, artefacts de run)
```

Règle du projet, non négociable : **aucun commit ne part sans message généré à
partir du diff réel**. Lire le diff, puis écrire le message. Découpage suggéré :

- `fix(research): l'IC est une corrélation de rang, mesurée avec sa taille d'échantillon`
  → `domain/research.py`, `research_engine.py`, `tests/test_research_engine.py`
- `feat(sig-02): décomposition P&L brut/coût et recherche de features mesurées`
  → les deux scripts + `tests/scripts/test_pnl_decomposition.py`
- `docs(sig-02): ADR 0024, rejet documenté et étape de pipeline manquante`
  → l'ADR + `BACKLOG.md`

Décider si les `.validation_registry/*.json` entrent dans le dépôt — ils ne
l'ont jamais fait jusqu'ici.

---

## 6. État de la porte de vérification (à re-passer avant de déclarer terminé)

Au moment d'écrire, tout est vert :

```bash
.venv/bin/python -m mypy --strict scripts/diagnose_pnl_decomposition.py scripts/run_feature_research.py
# Success

.venv/bin/python -m ruff check scripts/diagnose_pnl_decomposition.py scripts/run_feature_research.py \
  tests/scripts/test_pnl_decomposition.py tests/test_research_engine.py \
  src/aegis_trade/domain/research.py src/aegis_trade/infrastructure/research/research_engine.py
# All checks passed!

PYTHONPATH=scripts .venv/bin/python -m pytest tests/scripts/test_pnl_decomposition.py \
  tests/test_research_engine.py tests/test_research_report.py -q
# 35 passed
```

**Scoper ruff aux fichiers touchés.** Un `ruff check` large remonte 26 erreurs
qui sont de la dette préexistante dans des fichiers non touchés (le handoff en
documente 24 dans 9 scripts). Ne pas les attribuer à ce travail, ne pas les
corriger au passage.

---

## 7. Pièges — ce qui est interdit sur cette reprise

1. **Ne pas rejouer l'entraînement en changeant un paramètre.** Ni marge 2.0x, ni
   horizon 6 ou 8, ni coûts live COST-02 (0.652 / 0.951 bps — plus bas, donc plus
   flatteurs). Un modèle qui échoue au holdout est une hypothèse abandonnée, pas
   une hypothèse à repasser jusqu'à ce qu'elle passe. Étape 2 vient de montrer
   qu'il n'y a rien à récupérer en aval : le problème est en amont du modèle.
2. **Ne pas brancher KRO-01.**
3. **Ne pas lire le `dir_acc 0.7733 / 0.7745` comme une preuve de signal.**
   `trainer.py` le dit dans son propre commentaire : mesuré **sur les données
   d'entraînement**. Les seuls chiffres hors échantillon sont les win rates de
   30.3 % et 25.8 %.
4. **Ne jamais afficher les credentials Deriv** (`DERIV_API_TOKEN`,
   `DERIV_APP_ID` dans `.env`) — noms de clés, longueurs, préfixes uniquement.
5. **Le rejet est un résultat.** Un ADR qui documente proprement l'absence
   d'edge, avec ses preuves reproductibles, vaut mieux qu'un modèle forcé.

---

## 8. Environnement

- Interpréteur : `.venv/bin/python`. Scripts important d'autres scripts :
  `PYTHONPATH=scripts`.
- `DEBT-01` : `pytest --cov` échoue sur tout module important pandas (numpy ≥ 2.4
  refuse ses extensions C sous traceur actif). Contournement :
  ```bash
  printf 'import pandas  # noqa: F401\n' > /tmp/preload_pandas.py
  PYTHONPATH=/tmp:scripts .venv/bin/python -m pytest <tests> -p preload_pandas --cov=<module>
  ```
- `providers/deriv/` et `infrastructure/paper/deriv_gateway.py` sont sur
  l'ancienne API WebSocket v3, cassés côté serveur silencieusement. Hors du
  chemin de SIG-02, délibérément non touchés.
- Préexistants hors périmètre : 24 erreurs ruff dans 9 scripts, 536 erreurs
  `mypy --strict` sur `src/` complet.
- Logs : rediriger vers `/tmp`, jamais dans le dépôt.
- Divergence documentaire à trancher un jour : `PRODUCT_ROADMAP.md` annonce
  « Sprint 4 : Dashboard [EN COURS] » pendant que `BACKLOG.md` tient SIG-02 pour
  critique et bloquant de la Phase 4. Les deux ne décrivent pas le même présent.
