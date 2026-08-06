# BUILD VS REUSE — Audit Écosystème Open Source

**Objectif** : Avant toute construction de module de calcul, d'analyse, ou d'infrastructure générique, documenter ici la recherche d'alternatives existantes. Décision explicite : construire nous-mêmes, ou réutiliser.

**Date de création** : 2026-08-05

---

## 1. Indicateurs Techniques (ATR, RSI, MACD, EMA)

**Date d'audit** : 2026-08-05  
**Contexte** : Aegis possède 4 implémentations d'ATR divergentes (Lot 3), consolidées vers `utils/math.py`. RSI, MACD, EMA également implémentés manuellement.

### Recherche

**pandas-ta (twopirllc)** — lib originale, **DISCONTINUED**  
- Mainteneur affiche avertissement : niveau de soutien actuel insoutenable, risque d'arrêt du projet
- **Statut** : abandonné, ne pas utiliser

**pandas-ta-classic** — fork communautaire  
- **Dépôt** : `github.com/xgboosted/pandas-ta-classic`, PyPI `pandas-ta-classic` 0.6.52
- **Mainteneur** : **xgboosted — sans lien avec twopirllc.** Fork communautaire indépendant, pas une succession officielle. (Le brief d'origine affirmait « twopirllc successeur » : **faux**, corrigé après vérification.)
- **Fonctionnalités** : 193 indicateurs + 62 patterns (release PyPI) ; branche `main` en avance à 224 + 62
- **Dépendances** : aucune dépendance TA-Lib requise ; `talib=True` bascule optionnellement vers l'implémentation C
- **Performance** : accélération numba `6×–230×`, exposée via `pip install pandas-ta-classic[performance]`
- **Couverture** : ATR (Wilder), RSI, MACD, EMA tous présents ; parité TA-Lib vérifiée par `test_oracle_talib.py`
- **Qualité** : tests par propriétés (Hypothesis), versioning setuptools-scm sur tags git

### ⚠️ L'argument performance ne s'applique PAS à notre cas

Le gain numba `6×–230×` porte sur **10 indicateurs à boucle chaude nommément** : QQE, RSX, HWMA, SSF, PSAR, Supertrend, MCGD (PR #99). **Aucun n'est ATR, RSI, MACD ni EMA** — nos quatre cibles. Le CPU dual-core sans GPU ne bénéficie donc de rien sur le périmètre concerné.

Ce qui reste réellement en faveur de la migration : correction validée par une communauté (parité TA-Lib testée) plutôt que par nous seuls, et suppression de code maison à maintenir. **Pas la vitesse.**

### Décision

**REPORTER À LOT 6 (après Gold)** — évaluer migration de `utils/math.py` vers `pandas-ta-classic`.

**Raison du report** :
- Lot 3 vient de consolider vers une seule implémentation exacte (Wilder 1978) dans `utils/math.py`
- Migration immédiate = rouvrir un chantier juste refermé
- Le bénéfice restant (validation communautaire) est réel mais faible face au risque de régression numérique sur une grandeur qui vient d'être scellée par tests

**Critères d'évaluation future (Lot 6)** :
- Les sorties de `pandas-ta-classic.atr()` correspondent-elles exactement à `utils/math.compute_atr` sur nos datasets de test ?
- La lib respecte-t-elle la formule Wilder (lissage `alpha = 1/14`, amorce correcte — c'est précisément le défaut qu'avait `technical_extractor.py` avec son `ewm` sans amorce) ?
- Peut-elle remplacer RSI, MACD, EMA sans régression ?
- Le mainteneur unique (`xgboosted`) est-il un risque acceptable ? La lib est vendorisable si besoin (licence à vérifier).

**Action si migration acceptée** : remplacer `utils/math.py` par appels pandas-ta-classic, vérifier que tous les appelants pandas convertissent via `.to_numpy(dtype=float)`.

---

## 2. Analyse de Facteurs / Information Coefficient (IC)

**Date d'audit** : 2026-08-05  
**Contexte** : `research_engine.py` calcule IC (Spearman), taille d'échantillon effective pour rendements chevauchants, gate de significativité. Débogage récent (Pearson→Spearman, n_eff, gate).

### Recherche

**alphalens-reloaded** — moteur d'analyse de facteurs quantitatifs  
- **Dépôt** : `github.com/stefan-jansen/alphalens-reloaded`, PyPI `alphalens-reloaded` 0.4.6
- **Mainteneur** : Stefan Jansen (auteur *Machine Learning for Trading*, écosystème ml4trading)
- **Statut** : activement maintenu (fork du projet Quantopian abandonné)
- **Fonctionnalités** :
  - Attend : valeur de facteur par actif × jour + prix pour calcul rendements futurs
  - Produit : rendements par quantile, **Information Coefficient Spearman** (`factor_information_coefficient`), statistiques de turnover, autocorrélation de rang
  - **Détection sur-ajustement** : problème de tests multiples documenté (300+ facteurs académiques publiés = probables faux positifs, Harvey/Liu/Zhu)
  - Intégration : fonctionne avec Zipline (backtesting) et Pyfolio (perf/risk), tous trois sous l'ombrelle "reloaded" de Jansen
- **Pertinence** : on teste 25 features à la fois → détection tests multiples directement utile
- **Sources** : [GitHub](https://github.com/stefan-jansen/alphalens-reloaded), [PyPI](https://pypi.org/project/alphalens-reloaded/), [PyQuantNews tutorial](https://www.pyquantnews.com/free-python-resources/real-factor-alpha-how-to-measure-it-with-information-coefficient-and-alphalens-in-python)

### Décision

**ÉVALUER AVANT MIGRATION** — ne pas remplacer `research_engine.py` à l'aveugle.

**Ce que alphalens-reloaded apporte vs notre implémentation** :
- IC Spearman ✅ (couvert, `factor_information_coefficient`)
- Autocorrélation de rang ✅ (nous n'avons pas, utile)
- Analyse par quantile ✅ (nous n'avons pas, utile pour vérifier monotonicité)
- Détection tests multiples ✅ (Harvey/Liu/Zhu documenté, nous n'avons pas — **critique** car on teste 25 features)
- Turnover analysis ✅ (nous n'avons pas)
- Intégration Zipline/Pyfolio ⚠️ (hors périmètre, on a déjà Backtester maison)

**Ce que notre `research_engine.py` fait et qu'il faut vérifier** :
1. **Taille d'échantillon effective (`n_eff`)** — corrige surestimation due aux rendements chevauchants (facteur ~√N sur t-stat à N=10). Formule : `observations // horizon`. **Inconnue dans alphalens** — à vérifier dans le code source.
2. **Gate de significativité** — seuil |t| > 2,0, délibérément pas un seuil de découverte (pas de correction Bonferroni ici, elle appartient à l'étape suivante). **Inconnu dans alphalens** — à vérifier.
3. **14 tests unitaires** couvrant cas limites (IC = ±1, n < 3, horizon < 1, leak detection via clamp). **À rejouer** contre alphalens si migration.

**Questions bloquantes à résoudre par lecture du code alphalens** :
1. `factor_information_coefficient` utilise-t-il la taille d'échantillon brute ou corrige-t-il l'overlap des rendements forward ?
2. Existe-t-il un gate paramétrable de t-stat, ou faut-il l'ajouter en wrapper ?
3. Le format d'entrée `get_clean_factor_and_forward_returns` est-il compatible avec notre `FeatureSet` + barres OHLCV, ou faut-il un adaptateur ?

**Critères de décision** :
- **Migrer si** : `n_eff` déjà implémenté OU facilement wrappable, pas de régression sur nos 14 tests, apport réel (détection tests multiples + analyse quantile).
- **Conserver si** : API incompatible avec notre pipeline (effort d'adaptation > bénéfice), ou dépendances lourdes (statsmodels/seaborn pèsent combien ?), ou `n_eff` absent et non wrappable proprement.

**Action Lot 6** :
1. Lire `alphalens/performance.py:factor_information_coefficient` — chercher correction d'overlap ou mention de "effective sample size"
2. Lire la doc sur le format d'entrée attendu — comparer à `FeatureSet` (List[pd.DataFrame] avec colonnes `feature_*` + `symbol` + `datetime`)
3. Installer en venv isolé, rejouer nos 14 tests contre alphalens
4. Décider : migration complète, wrapper mince, ou conservation `research_engine.py`

**Action si migration refusée** :
- Ajouter **nous-mêmes** la détection de tests multiples (Bonferroni ou Holm-Bonferroni sur les 25 features) — c'est l'apport le plus critique d'alphalens pour notre cas
- Documenter la décision en ADR (raison technique, pas "on préfère notre code")

---

## 3. Données Macroéconomiques FRED & Dépôts Gold GitHub

**Date d'audit** : 2026-08-06  
**Contexte** : Intégration de features macroéconomiques (ex: Taux Réel 10 ans FRED `DFII10`, VIX, pétrole) pour alimenter la recherche de signal sur l'Or (`frxXAUUSD`).

### Recherche OSS-First (Une seule source de vérité)

1. **Extension officielle OpenBB (`openbb-fred`)** :
   - **Audit de l'existant** : `OpenBBDataProvider` (`openbb>=4.0.0`) est déjà la brique unifiée d'accès aux données du projet.
   - **Découverte** : L'extension officielle `openbb-fred` active l'accès natif aux 800 000+ séries de la St. Louis Fed via l'interface unifiée `obb.economy.fred_series(symbol='DFII10', provider='fred')`.
   - **Décision** : **ADOPTÉE**. Évite la création redondante d'un provider parallèle (`fredapi`), respectant le principe de la source de vérité unique et la Règle 4.

2. **Dépôts Gold Open Source (`backtrader-pullback-window-xauusd`, `zero-was-here/tradingbot`, `Quantitative-XAUUSD-Strategy`)** :
   - **Constat d'audit** : La plupart des dépôts spécifiques réutilisent des règles techniques triviales (EMA/ATR/RSI) sans split train/test ni correction $n_{\text{eff}}$.
   - **Décision** : **REJETÉS comme source de code** (risque de sur-ajustement), mais conservés comme **inspiration conceptuelle de features macro** (taux réels `DFII10`, régimes VIX, spread pétrole/or).

### Action
- Extension `openbb-fred` ajoutée à `pyproject.toml`.
- Méthode `fetch_macro` implémentée directement dans `OpenBBDataProvider` via `obb.economy.fred_series`.
- `DFII10` (Taux réel 10 ans US) routé via le provider OpenBB unique.

---

## 4. [Template pour futurs audits]

**Date d'audit** : YYYY-MM-DD  
**Contexte** : [quel problème/module]

### Recherche

- Lib 1 : mainteneur, statut, fonctionnalités, pertinence
- Lib 2 : idem

### Décision

**CONSTRUIRE NOUS-MÊMES** / **RÉUTILISER [lib]** / **ÉVALUER [lib]**

**Raison** :
- Performance : [si pertinent]
- Dépendance trop lourde : [si pertinent]
- Licence incompatible : [si pertinent]
- Fonctionnalité manquante : [si pertinent]
- Mainteneur unique / 12+ mois sans commit : [si pertinent]

**Action** : [étapes concrètes si réutilisation, ou justification si construction]

---

## Règles de ce Document

1. **Avant toute construction de module** (indicateur, backtester, risk, scheduler, etc.) : recherche obligatoire (3–5 requêtes web + GitHub : activité, mainteneurs, licence) AVANT d'écrire du code.
2. **Documenter même si "on code nous-mêmes"** — la raison doit être écrite (perf, deps, licence, feature manquante), pas supposée.
3. **Signal d'alerte, pas disqualification** : 12+ mois sans commit ou mainteneur unique = à surveiller, mais pas rédhibitoire.
4. **Traçabilité** : date d'audit, mainteneur, version, statut activité (actif / stale / abandonné).
