# ADR 0024 — Campagne SIG-02 rejetée : l'étape « Recherche de features » avait été sautée

- **Statut** : ACCEPTÉ
- **Date** : 2026-08-04
- **Contexte technique** : `scripts/train_qlib_model.py`, `scripts/diagnose_pnl_decomposition.py`, `scripts/run_feature_research.py`, `src/aegis_trade/infrastructure/research/research_engine.py`
- **Dépend de** : ADR 0018, ADR 0020, ADR 0021, ADR 0023
- **Résout** : SIG-02

---

## 1. Contexte et résultats initiaux de SIG-02

La campagne SIG-02 avait pour objectif d'évaluer l'exploitabilité d'un modèle d'apprentissage supervisé (LightGBM) entraîné sur des features techniques pour prédire la direction du rendement futur sur les indices synthétiques Deriv **Crash 1000** (horizon 5 barres M1) et **Boom 1000** (horizon 10 barres M1).

Les deux entraînements (300 arbres, 75 000 barres M1, split chronologique 70/30, seuils d'entrée dérivés du modèle de coût institutionnel selon l'ADR 0018) ont donné un **score de 0/100** dans les deux cas, avec les 4 campagnes de validation en échec.

### 1.1 Tableau comparatif des deux entraînements

| Métrique / Paramètre | Crash 1000 | Boom 1000 |
|---|---|---|
| Timeframe / Horizon | M1 / 5 barres | M1 / 10 barres |
| `--commission-rate` | 0.00003725 | 0.00005315 |
| Coût A/R | 0.745 bps | 1.063 bps |
| Seuil d'entrée (`MLStrategy`) | 0.000074 | 0.000106 |
| Lignes étiquetées (train) | 52 495 | 52 490 |
| RMSE / MAE (train) | 5.72e-4 / 3.90e-4 | 7.75e-4 / 6.04e-4 |
| **Score global** | **0 / 100** | **0 / 100** |

### 1.2 Métriques de validation Crash 1000 h5

- **Hold-out** : Sharpe −0.4616, Rendement net −14.9721 %, Max Drawdown 15.08 %
- **Walk-forward** : Sharpe −0.4657, Win Rate 30.27 %, Rendement net −14.9868 %, Max DD 4.94 %
- **Monte-Carlo** : Ruine 0.0 %, Rendement médian −15.0178 %, **Loss Probability 1.00**, Expected Shortfall −21.637 %
- **Benchmark** : Alpha −0.1146, Beta 0.537, Benchmark Sharpe −0.0851, Benchmark Return −3.51 %
- **Rendements par fold (Walk-Forward)** : −3.7896 % / −4.3147 % / −2.2861 % / −4.2583 % / −1.2898 %
- **Exécutions totales** : 3 618 exécutions (~1 809 allers-retours)

### 1.3 Métriques de validation Boom 1000 h10

- **Hold-out** : Sharpe −0.6662, Rendement net −16.8739 %, Max Drawdown 17.18 %
- **Walk-forward** : Sharpe −0.6753, Win Rate 25.82 %, Rendement net −16.8786 %, Max DD 5.34 %
- **Monte-Carlo** : Ruine 0.0 %, Rendement médian −17.1027 %, **Loss Probability 1.00**, Expected Shortfall −22.6206 %
- **Benchmark** : Alpha −0.159, Beta 0.0198, Benchmark Sharpe −0.0226, Benchmark Return −0.97 %
- **Rendements par fold (Walk-Forward)** : −4.0796 % / −3.1506 % / −2.9337 % / −5.2013 % / −2.7624 %
- **Exécutions totales** : 3 843 exécutions (~1 921 allers-retours)

---

## 2. Étape 1 — Décomposition du P&L (Brut vs Coût)

Pour isoler la cause de cet échec net (−14.97 % et −16.87 %), l'outil `scripts/diagnose_pnl_decomposition.py` a séparé le P&L en deux termes :
1. **Terme BRUT** : P&L de marché avant prélèvement du péage (mesure de l'edge directionnel).
2. **Terme COÛT** : Péage cumulé prélevé par le courtier (`turnover * commission_rate`).

Deux exécutions complémentaires ont été mesurées : `actual` (coût réel) et `frictionless` (péage broker nul avec le même seuil d'entrée dérivé du coût réel).

### 2.1 Résultats mesurés de la décomposition P&L

| Métrique | Crash 1000 h5 | Boom 1000 h10 |
|---|---|---|
| `--commission-rate` | 0.00003725 | 0.00005315 |
| Coût A/R | 0.745 bps | 1.063 bps |
| Seuil d'entrée | 0.000074 | 0.000106 |
| Exécutions | 3 618 | 3 843 |
| Turnover cumulé | 339 781 042.71 $ | 344 843 999.62 $ |
| **Coût cumulé** | **12 656.84 $ (+12.6568 %)** | **18 328.46 $ (+18.3285 %)** |
| **P&L BRUT** | **−2 315.29 $ (−2.3153 %)** | **+1 461.24 $ (+1.4612 %)** |
| Brut par exécution | −0.0681 bps | +0.0424 bps |
| **t du brut (Student)** | **−0.71** | **+0.54** |
| Net réalisé | −14 972.13 $ (−14.9721 %) | −16 867.22 $ (−16.8672 %) |
| Brut frictionless | −2 409.36 $ (−2.4094 %), t = −0.68 | +1 682.90 $ (+1.6829 %), t = +0.56 |
| Écart de réconciliation comptable | 1.89e-10 / 2.04e-10 | 1.46e-11 / 1.31e-10 |

### 2.2 Analyse et invariance d'échelle

- **Crash 1000** : Brut négatif (−2 315.29 $). Le modèle perd de l'argent avant même de payer la moindre commission. L'absence d'edge est totale.
- **Boom 1000** : Brut positif en valeur absolue (+1 461.24 $), mais avec un **`t = +0.54`**, largement en dessous du seuil de significativité (`|t| > 2.0`). Ce brut positif est un bruit favorable statistiquement **indistinguable de zéro**.
- **Invariance d'échelle** : Augmenter la taille des positions (le levier ou le fractionnement du sizer) est **sans effet** sur la rentabilité net. Le brut et le coût sont tous deux rigoureusement linéaires en notionnel ; leur ratio est invariant à l'échelle.

---

## 3. Étape 2 — Audit et mesure de l'Alpha Research

### 3.1 Audit du rapport historique (`ic_mean = 0.9645`)

L'audit préalable du rapport `data/reports/alpha_research_BTCUSD_20260727_012740.json` (qui rapportait un `ic_mean` de 0.9645 pour `macd_signal`) a démontré une **fuite de cible (target leak)** dans le script de génération de données de démonstration `scripts/generate_dummy_features.py`. Ce dernier écrivait le rendement du lendemain plus un bruit $N(0, 0.005)$ dans la colonne `macd_signal` ($\text{corr} = 0.02 / \sqrt(0.02^2 + 0.005^2) \approx 0.9701$). Le moteur de recherche lui-même n'était pas vicié par une fausse formule, mais il présentait trois défauts structurels majeurs qui ont été corrigés :

1. **Substitution Pearson/Spearman** : Le moteur calculait la corrélation de Pearson tout en l'intitulant Spearman. Sur des distributions de rendements à queues épaisses, Pearson interprète des valeurs extrêmes isolées comme un signal fort.
2. **Absence de test de significativité** : L'IC était rapporté sans intervalle de confiance ni budget d'échantillon.
3. **Ignorance du chevauchement temporel (Forward Overlap)** : Les rendements forward sur $N$ barres se chevauchent sur $N-1$ barres. Évaluer le $t$-statistique sur l'échantillon brut $N_{raw}$ gonflait le $t$ d'un facteur $\sqrt{N}$. Le moteur utilise désormais l'échantillon effectif non-chevauchant $N_{eff} = N_{raw} // N$.

### 3.2 Résultats de la recherche de features sur Crash 1000 et Boom 1000

L'évaluation de l'Information Coefficient (IC Spearman) sur les 25 features réelles, mesurée séparément sur l'échantillon d'apprentissage (Train 70 %) et l'échantillon de test (Test 30 %), donne le résultat suivant :

**Résultat : 0 / 25 features survivent au test de significativité et de cohérence de signe.**

- **Horizon 5 & 10 barres (Crash 1000 & Boom 1000)** : Le `|t|` maximum observé hors échantillon sur l'ensemble des 25 features est de **1.87** (obtenu par `typical_price` sur Boom h10), sous le seuil critique de $|t| > 2.0$.
- **Effet de dérive sur les niveaux** : Les features trustant le haut des classements in-sample sont systématiquement des **niveaux de prix** (`ema_*`, `bb_*`, `typical_price`). Ces features se corrèlent à la tendance globale sur le Train mais s'effondrent ou s'inversent hors échantillon, confirmant leur nature d'artefacts de non-stationnarité.
- **Constat sur le volume Deriv** : Les colonnes de volume de Crash 1000 et Boom 1000 sont uniformément égales à `0.0` (`nunique = 1`). En conséquence, les 3 features dépendantes du volume (`rel_volume`, `vwap`, `volume_sma_20`) ont rapporté des observations effectives nuls ($N_{eff} = 0$) ou un IC strictly nul. Ces 3 features ne portaient aucune information.

---

## 4. Cause racine : L'étape « Recherche de features » avait été sautée

### 4.1 Rupture du protocole institutionnel

La cause fondamentale des échecs de SIG-01 et SIG-02 est le **non-respect de la séquence de validation du pipeline AEGIS QUANT OS** (`CLAUDE.md`) :

$$\text{Dataset} \rightarrow \text{Backtester} \rightarrow \text{Baseline} \rightarrow \mathbf{\text{Recherche de features (SAUTÉE)}} \rightarrow \text{Validation Train} \rightarrow \text{Validation Holdout} \rightarrow \dots$$

Les ADR 0018 à 0023 ont modélisé et optimisé le terme **coût** de l'inégalité $\text{Edge} > \text{Coût}$ avec une grande rigueur scientifique. Cependant, le terme **signal** ($\text{Edge}$) n'avait jamais été mesuré. Un modèle complexe (LightGBM) a été directement entraîné sur un panier de 23 features dont le pouvoir prédictif individuel était nul.

Les deux mesures empiriques indépendantes réalisées lors de ce diagnostic (la décomposition du P&L du backtest et l'analyse d'IC Spearman sur les features) convergent vers le même constat : **aucune des 23 features techniques testées ne présente de relation prédictive mesurable avec le rendement futur aux horizons 5 et 10 barres sur ces séries.**

### 4.2 Cadrage précis du rejet (Ce que l'ADR ne dit PAS)

Cet ADR **ne conclut pas** qu'il est impossible d'obtenir un edge sur les instruments Crash 1000 ou Boom 1000. Il rejette spécifiquement l'hypothèse $H_0$ formulée dans SIG-02 :
> *« Les 23 features techniques actuelles permettent à un modèle d'arbre de décision de prédire la direction du prix à des horizons de 5 à 10 barres M1 de manière supérieure au coût de transaction. »*

Cette hypothèse est formellement **réfutée**.

---

## 5. Audit des validateurs et dette technique (DEBT-03)

L'investigation sur la parfaite identité des rendements rapportés par `HoldOutValidator` et `BenchmarkValidator` (−14.9721 % sur Crash) a mis en évidence le comportement réel de la suite de validation (`scripts/train_qlib_model.py:210`) :
- `train_qlib_model.py` passe le même dataset de test `ListDataFeed(test_sets)` à l'ensemble des validateurs.
- `HoldOutValidator` n'isole aucun sous-segment complémentaire : la clé metadata `details: {'ratio': 0.2}` est décorative.
- `WalkForwardValidator` découpe le segment de test en 5 blocs chronologiques **sans réentraîner le modèle** à chaque étape (mesure de la stabilité temporelle du modèle figé, et non d'un vrai walk-forward adaptatif).

### Décision sur la dette DEBT-03
Les chiffres présentés dans les rapports de validation sont **statistiquement valides et strictement hors échantillon** (le segment de test de 22 500 barres n'a pas servi au fitting). Cependant, le nom des validateurs induit en erreur sur le protocole sous-jacent. 
La dette **DEBT-03** est inscrite au backlog pour réaligner les implémentations de `HoldOutValidator` et `WalkForwardValidator` avec leur dénomination exacte.

---

## 6. Décisions et conséquences

1. **Campagne SIG-02 fermée et REJETÉE**. Aucun réentraînement ni ajustement de hyperparamètres n'est autorisé sur ce panier de features.
2. **KRO-01 (Kronos / Modèle d'ordre supérieur) maintenu SUSPENDU**. Entraîner un modèle plus complexe sur des features au pouvoir prédictif nul est une violation directe de l'ADR 0019.
3. **Mission FE-01 (Recherche de features) créée comme jalon BLOQUANT**. Aucune future campagne de signal ne pourra faire l'objet d'un entraînement de modèle sans qu'une étape d'Alpha Research préalable n'ait validé l'existence d'IC significatifs ($|t| > 2.0$) sur l'échantillon d'apprentissage et de test.
