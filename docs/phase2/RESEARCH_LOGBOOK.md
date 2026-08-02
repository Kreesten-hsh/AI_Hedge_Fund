# Journal de Recherche & Expériences (Research Logbook)

> **Important** : Ce document est le registre officiel de toutes les expériences (gagnantes ou perdantes) d'Aegis Quant OS. Il est le socle de l'apprentissage asymétrique. Chaque ligne correspond à un vecteur dans la base FAISS.

> **Document annoté le 2026-07-31** sur la base de `docs/refont/AUDIT_COMPLET_2026-07-31.md`.
>
> **Ce registre est vide de toute expérience.** Zéro trade consigné, zéro politique évaluée. La phrase
> « chaque ligne correspond à un vecteur dans la base FAISS » est fausse dans les deux sens : il n'y a pas
> de ligne, et la base FAISS n'est jamais alimentée (`MemoryManager(` : 0 occurrence dans le dépôt).
>
> Les seules entrées existantes sont des **événements de gouvernance**, pas des expériences. Deux d'entre
> elles affirment un succès que le code contredit — annotées en place ci-dessous, jamais supprimées : un
> logbook dont on effacerait les erreurs ne serait plus un logbook.
>
> **Objectif rappelé : démo réelle sur Deriv pour entraîner le système, puis capital réel.** Ce fichier est
> le support de l'entraînement. Tant qu'il est vide, la phase démo n'apprend rien — elle tourne.


## Template d'Expérience

```yaml
Experience: #00001
Date: YYYY-MM-DD HH:MM:SS
Actif: Boom1000
Configuration_Marche:
  Volatilité_ATR: 
  Spread:
  Trend_MVA:
  RSI:
  Momentum:
Embedding_ID: vector_id_12345
Décision_Initiale: 
  Agents_votants: Quant, Macro, Memory
  Vote: APPROVED
  Risk_Veto: FALSE
  Ordre: BUY 0.1 Lot
Résultat:
  PnL: +X
  Max_Drawdown: -Y
  Temps_en_position: Z secondes
  Slippage: S
Catégorie: SUCCESS_MEMORY
Pourquoi: (Commentaire auto-généré par le LLM post-trade)
```

## Logs d'Expériences (Phase Live / AI-07)

*Les logs des 200 trades du cycle papier réel et du cycle capital réel (AI-07) seront injectés ici automatiquement.*

> **Correctif de statut (2026-07-31) :** aucune injection automatique n'existe. Aucun code du dépôt
> n'écrit dans ce fichier, et les 200 trades annoncés n'ont jamais eu lieu — le `PaperTradingOrchestrator`
> produit `VERDICT: WAIT | mult=0.0 | conf=0.0` à chaque cycle, donc zéro trade ouvert. **Compte réel
> d'expériences consignées : 0.**


## Événements de Gouvernance
- **[2026-07-30] Intégration Kronos (Sprint AI-08)** : Erreur de modèle corrigée (passage de l'Amazon Chronos générique au vrai modèle natif finance `shiyu-coder/Kronos`). Fine-tuning et inférence sur CPU testés avec succès via `run_kronos_smoke_test.py`. Isolation totale via l'Adapter. Les résultats de la première évaluation sont très positifs (RAM Peak à ~917 MB, 49s par epoch de 1000 bougies). Décision : **ACTIF**, prêt pour le fine-tuning complet.

  > **Correctif (2026-07-31)** — l'entrée est conservée telle quelle, quatre points sont faux :
  > 1. Le dépôt réellement vendoré est `NeoQuasar/Kronos-mini`, pas `shiyu-coder/Kronos` (le répertoire
  >    porte ce nom, ce qui a entretenu la confusion). À ne pas confondre non plus avec
  >    `amazon/chronos-t5-mini`, qui est un troisième modèle.
  > 2. « Testés avec succès » : le smoke test passe, mais `providers/kronos_adapter.py:40-41,63-71`
  >    alimente le modèle avec `np.random.randn`. Ce qui a été validé, c'est que l'inférence **s'exécute**
  >    sur du bruit — pas qu'elle prédit quoi que ce soit.
  > 3. « Résultats très positifs » : aucune métrique de qualité (MAPE, RMSE vs baseline naïve) n'a été
  >    produite. Les deux chiffres cités (~917 MB, 49 s/epoch) sont des mesures de **coût**, pas de
  >    performance. Ils restent valables comme tels et font foi pour l'empreinte RAM.
  > 4. Les 1 532 lignes amont copiées dans `providers/kronos/shiyu_model/` n'ont **aucun fichier
  >    LICENSE** dans le dépôt (Lot 5).
  >
  > Statut mesuré réel : `[FAÇADE]` + `[VENDORÉ]`, pas `ACTIF`.
- **[2026-07-30] Modèles externes** : 
  - Qlib (Microsoft) : Actif. Modèle `LGBModel` fonctionnel pour features alpha.
  - Kronos (shiyu-coder) : Actif. Modèle AAAI 2026 natif finance avec discrétisation OHLCV `BSQuantizer`. Entraînement et inférence CPU fonctionnels en tâche de fond.
  - Chronos (Amazon) : Rejeté. Modèle générique (T5) non adapté aux séries temporelles financières (remplacé par Kronos).

  > **Correctif (2026-07-31)** — « Actif » ne signifie rien de vérifiable ici. Mesure : Qlib est
  > `[ÉCRIT-NON-CÂBLÉ]` (aucun cycle de production n'appelle `QlibPredictor` ; deux `DatasetBuilder`
  > divergents coexistent) et Kronos est `[FAÇADE]` + `[VENDORÉ]`. Le rejet de Chronos, lui, reste une
  > décision valide et documentée.

- **[2026-07-30] Correction de Gouvernance (Post AI-07)** : Alignement de la Roadmap (`PHASE2_ROADMAP.md`) avec le `VALIDATION_PIPELINE_REPORT.md` réel. Modification des statuts de AI-06/AI-07 à `[CODE-READY]`. FinGPT (Abandonné, remplacé par Ollama) et lightweight-charts (Planifié post-validation spec).

  > **Correctif (2026-07-31)** — « remplacé par Ollama » est faux. **Aucun analyste macro n'existe dans le
  > dépôt**, ni FinGPT ni Ollama : `MockReasoner()` est injecté en production (`api/deps.py:53`). FinGPT
  > est abandonné sans remplaçant. Par ailleurs `ADR-002` n'a jamais été passé à `Superseded`, ce qui
  > laisse deux sources de vérité contradictoires sur ce point (Lot 6).

## Logs de Validation de Politique (Policy Promotion Gate)
Trace des validations de politiques RL (AI-04).
- *[DATE] Policy [ID] évaluée vs [ID_ACTUELLE]. Statut : PROMOTED / REJECTED.*

> **Correctif de statut (2026-07-31) :** **zéro politique évaluée.** L'environnement RL retourne
> `np.zeros(30)` comme observation (`orchestrator.py:97`) : un agent entraîné dessus n'apprend rien du
> marché. Aucune promotion n'est possible tant que le Lot 2 n'a pas alimenté l'observation avec des
> données réelles.

## Ce que ce document ne promet pas

- **Pas d'apprentissage.** Un registre vide ne fonde aucun « apprentissage asymétrique ». Les 0
  expériences consignées ne sont pas un retard de saisie : rien n'écrit ici, et rien n'a été tradé.
- **Pas de traçabilité rétroactive.** Les décisions prises avant que ce fichier soit alimenté sont
  perdues. On ne pourra pas les rejouer.
- **Les événements de gouvernance ne sont pas des expériences.** Ils enregistrent des choix d'outillage,
  pas des résultats de marché. Les compter comme du contenu de logbook a entretenu l'illusion d'activité.

---

## 2026-08-02 — Phase 1 Clôturée : Sourcing de Données Réelles (Deriv WS & OpenBB)

- **Actions réalisées** :
  1. Adaptation de `OpenBBDataProvider` dans `openbb_provider.py` : levée de la restriction restreignant l'accès à DXY/US10Y uniquement, ajout de la correspondance `XAUUSD: GC=F`.
  2. Création de `DerivHistoricalData` dans `src/aegis_trade/providers/deriv/historical_data.py` pour l'extraction asynchrone des bougies (candles) via l'API WebSocket Deriv (`?app_id=1089`).
  3. Création du script `scripts/fetch_training_data.py` et extraction réussie des jeux de données réels.
- **Résultats obtenus (Données réelles sauvegardées dans `data/market_data/`)** :
  - `crash1000.parquet` : 5 000 bougies M1 réelles de l'indice Crash 1000 (176.5 KB)
  - `boom1000.parquet` : 5 000 bougies M1 réelles de l'indice Boom 1000 (134.0 KB)
  - `xauusd.parquet` : 124 bougies D1 de l'Or (XAUUSD) via OpenBB (8.8 KB)
- **Vérifications de santé de la base de code** :
  - `pytest` : 414 tests passing (0 failure)
  - `mypy --strict src/` : 537 erreurs (-1 vs baseline 538)
  - `ruff check` : 309 erreurs (-1 vs baseline 310)

---

## 2026-08-02 — Phase 2 Clôturée : Réparation Intégrale des 6 Validateurs (Lot 4)

- **Actions & Corrections réalisées (Audit CTO 4/4)** :
  1. `MonteCarloValidator` : Élimination du `passed=True` en cas de 0 trade. Désormais, 0 trade produit explicitement `passed=False` avec motif `"Aucun trade généré, résultat non concluant"`.
  2. `WalkForwardValidator` : Découpe réelle en fenêtres glissantes (5 folds réels) et évaluation des Sharpe/WinRate sur les folds.
  3. `BenchmarkValidator` : Implémentation du vrai benchmark `BuyAndHoldStrategy`. Suppression de la constante `beta = 0.8` ; calculs réels de l'Alpha (`strat_return - bench_return`) et du Beta empirique.
  4. Tests unitaires comportementaux (`tests/validation/test_validators_real_metrics.py`) :
     - Stratégie inerte (0 trade) -> Échoue au Monte-Carlo (`passed=False`).
     - Stratégie perdante -> Échoue au Hold-Out et au Benchmark (`passed=False`, Alpha < 0).
     - Stratégie gagnante -> Passe le Walk-Forward et le Benchmark (`passed=True`, Alpha >= 0).
- **Vérifications de santé de la base de code** :
  - `pytest` : 417 tests passing (0 failure) — **Delta: +3 tests de validation ajoutés, 0 régression**
  - `mypy --strict src/` : 537 erreurs (baseline: 537) — **Delta: 0 régression**
  - `ruff check` : 308 erreurs (baseline: 310) — **Delta: -2 erreurs (amélioration)**

---

## 2026-08-02 — Phase 3 Clôturée : Intégration Réelle Qlib/LightGBM (Lot 4 §Qlib)

- **Hypothèse testée** : Un modèle LightGBM entraîné sur les features techniques du FeatureStore
  (return_*, ema_*, rsi, macd, atr, bb_*) avec cible `forward_return_1` (rendement barre suivante)
  peut-il surperformer un benchmark Buy & Hold sur Crash 1000 M1 ?

- **Résultat : REJETÉ (score 30/100, is_approved=false).** C'est un résultat scientifiquement correct.
  Le pipeline de validation fonctionne exactement comme prévu : il a rejeté une hypothèse faible.
  - Hold-Out : Sharpe -0.39, max_drawdown 1.8% → **FAIL**
  - Walk-Forward : Sharpe -0.69, win_rate 0.0% (5 folds) → **FAIL**
  - Monte-Carlo : P(ruine) 0.0% (1 seul trade échantillonné) → **PASS**
  - Benchmark : Alpha -0.0173, Beta -1.006 → **FAIL**

- **Composants créés/réécrits** :
  1. `scripts/train_qlib_model.py` : Pipeline complète (load parquet → features → split chrono 70/30 → train LightGBM → validation 4 campagnes → export conditionnel).
  2. `providers/qlib/model_factory.py` : Vrai `LightGBMModel` via `lightgbm.train()`, avec save/load sidecar JSON, exclusion de `close_price` et de la cible de la matrice de features.
  3. `providers/qlib/dataset_builder.py` : `build_supervised()` calcule le vrai label `forward_return_1` via `price.shift(-1) / price - 1`.
  4. `providers/qlib/trainer.py` : Métriques réelles (RMSE, MAE, directional_accuracy).
  5. `application/strategy/ml_strategy.py` : Seuils en rendement (0.0002/-0.0002) au lieu de probabilité (ancien mock 0.52/0.48).
  6. `tests/providers/qlib/test_qlib_adapter.py` : 14 tests réels couvrant label leakage, real training, strategy wiring, et rejets bruyants.

- **Décision architecturale** : LightGBM-direct est un contournement temporaire (mlflow 1.27.0 incompatible avec qlib 0.9.7). Retour à `qlib.init()` standard au Lot 5 après upgrade mlflow.

- **Vérifications de santé de la base de code** :
  - `pytest` : 430 tests passing (0 failure) — **Delta: +13 tests Qlib, 0 régression**
  - `mypy --strict src/` : 536 erreurs (baseline: 537) — **Delta: -1 (amélioration)**
  - `ruff check` : 305 erreurs (baseline: 308) — **Delta: -3 (amélioration)**

- **Prochaine étape** : Le rejet du modèle baseline est normal — les features techniques standard
  sur du M1 synthétique n'ont pas assez de signal prédictif. Les axes d'amélioration sont :
  (a) features microstructure spécifiques aux synthétiques Deriv, (b) horizon de prédiction ajusté,
  (c) hyperparameter tuning. Mais d'abord, Phase 4 (Kronos-mini) puis Phase 5 (wiring agents).
