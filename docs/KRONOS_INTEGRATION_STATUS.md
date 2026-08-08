# Kronos — Statut d'intégration réel et condition d'activation (v2.0)

> Ce document ré-audite `providers/kronos_adapter.py` au 2026-08-08, en complément de `docs/archive/KRONOS_EVALUATION_REPORT.md` (2026-07-31), déjà présent dans le dépôt. Les deux audits convergent : rien n'a changé sur ce module depuis le 31 juillet.

## 1. État vérifié au grep

| Élément | Statut | Preuve |
|---|---|---|
| Identité du modèle | Corrigée | Modèle réellement vendoré : `NeoQuasar/Kronos-mini` (`providers/kronos/model_factory.py:15`). **Pas** `shiyu-coder/Kronos` — dépôt distinct, confusion fréquente car le dossier local s'appelle `shiyu_model/` |
| Chargement du predictor | `[VALIDÉ]` | `KronosModelFactory.get_predictor()` charge un `KronosPredictor` réel |
| Données d'entrée du predictor | `[FAÇADE]` | `kronos_adapter.py:59-66` : `dummy_df = pd.DataFrame(np.random.randn(512, 6) + 100, ...)`. Le paramètre `data_provider` reçu par `start_background_refresh` n'est jamais lu pour construire ce dataframe |
| Isolation asynchrone du tick loop | `[VALIDÉ]` | `asyncio.to_thread(run_prediction)` (`:85`), lecture cache O(1) (`:111`), couvert par `tests/providers/test_kronos_cache_never_blocks_tick_loop.py` |
| Instanciation en production | `[ ]` | `KronosAdapter` n'apparaît nulle part hors de son propre fichier dans `src/` |
| Injection dans les agents Council | `[ÉCRIT-NON-CÂBLÉ]` | `PatternAgent.__init__` et `TrendAgent.__init__` acceptent un `forecaster: Optional[IForecaster]` — rien ne l'instancie ni ne l'injecte |
| Qualité prédictive | `[ ]` | Zéro MAPE, zéro RMSE, zéro baseline naïve nulle part dans `src/`, `scripts/`, `tests/` |

## 2. Conséquence pour le pivot v2.0

Kronos reste un objectif technique légitime du projet, mais **son état actuel ne doit influencer aucune décision de trading**, même en démo — un forecast produit à partir de bruit aléatoire n'est pas un signal dégradé, c'est un signal inexistant qui aurait l'apparence d'un signal. L'injecter tel quel dans le Module 2 romprait la traçabilité (résumé v4 §3 : le motif documenté toute la semaine était précisément des composants qui *semblent* fonctionner sans l'être).

## 3. Conditions d'activation (les trois doivent être remplies, pas une sélection)

1. **Données réelles** : `data_provider` effectivement lu dans `_refresh_loop`, alimentant `dummy_df` avec de vraies bougies OHLCV H4/D1 du symbole concerné — plus de `np.random`.
2. **Qualité mesurée** : MAPE et/ou RMSE calculés sur un jeu de validation réel, comparés à une baseline naïve (ex : dernière valeur connue). Sans ce chiffre, aucune décision ne peut s'appuyer sur Kronos, même en signal secondaire.
3. **Câblage réel** : `KronosAdapter` instancié et injecté dans le composant d'analyse structurelle du Module 2 (successeur de `PatternAgent`), avec un test qui prouve que le forecast est effectivement lu et utilisé dans la décision finale — pas seulement câblable en théorie.

## 4. Portée dans ce sprint

Kronos est **hors chemin critique** du Module 2 pour la première itération. Le Module 2 doit être fonctionnel et testé sans dépendre de Kronos. L'activation de Kronos est un sprint séparé, déclenché uniquement une fois les trois conditions ci-dessus remplies et documentées dans un ADR dédié.
