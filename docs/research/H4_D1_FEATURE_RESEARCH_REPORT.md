# RAPPORT QUANTITATIF EXHAUSTIF DE RECHERCHE DE FEATURES H4 / D1 (TÂCHE 2 REVISÉE)

**Date d'exécution** : 2026-08-07 02:30 UTC
**Nombre Total d'Hypothèses Évaluées ($N_{\text{tests}}$)** : **`188`** (Groupes A Technique, B Macro/Positionnement FRED et Microstructure Spike)
**Seuil Brut non-ajusté ($|t| \ge 2.0$)** : $\alpha = 0.05$ (~5% de faux positifs attendus par pur hasard)
**Seuil de Bonferroni Ajusté** : $\alpha_{\text{bonf}} = 0.000266$ ($|t| \ge 3.646$)
**Seuil Benjamini-Hochberg (FDR $q = 0.05$)** : Taux de fausses découvertes contrôlé à 5%

---

## 1. Synthèse Globale de Significativité et Audit Econométrique

> [!CAUTION]
> **AUDIT DE RÉGRESSION FALLACIEUSE (SPURIOUS REGRESSION GRANGER & NEWBOLD 1974)**
> L'audit d'intégration (ADF) et de cointégration (Engle-Granger) démontre que les niveaux Gold et DXY sont deux séries non-stationnaires **$I(1)$** ($ADF_{Gold} = +0.70$, $ADF_{DXY} = -2.68 > -2.86$) **SANS relation de cointégration** ($ADF_{résidus} = -1.09 \gg -3.34$).
> Le t-stat $t = +3.72$ sur `feat_macro_dxy_level` est un artefact pur de tendance non-stationnaire partagée. Les variations stationnaires $I(0)$ (`dxy_change_1d`, `dxy_change_5d`) étant totalement plates ($|t| < 2.0$), la feature est **RÉFUTÉE ET ÉLIMINÉE**.

| Statut de Filtrage | Seuil de Tolérance | Nb Features Initiales | Après Audit Cointégration | Taux de Significativité Réel |
| :--- | :--- | :--- | :--- | :--- |
| **Brut univarié (Non ajusté)** | $|t| \ge 2.00$ ($p \le 0.05$) | 14 / 188 | 12 / 188 (2 artefacts I(1) rejetés) | 6.4% |
| **Benjamini-Hochberg (FDR $q=0.05$)** | $p \le \text{BH}_{\text{crit}}$ | 2 / 188 | **0 / 188** (0% valide) | **0.0%** |
| **Bonferroni (Conservateur)** | $|t| \ge 3.65$ ($p \le 0.000266$) | 1 / 188 | **0 / 188** (0% valide) | **0.0%** |

---

## 2. Résultats Détaillés par Actif et Groupe de Features (Ségrégation Stricte)

### 2.1 Gold (`XAUUSD` - Dukascopy 11.6 ans)

#### Groupe A : Features Techniques (D1 et H4) :
- **25 Features évaluées** : EMA ratios, RSI, MACD, Bollinger, Volatilité, Returns.
- **Résultat** : **0 / 76 paires significatives** post-correction BH ($q=0.05$).

#### Groupe B : Features Macro / Positionnement FRED (D1 et H4) :
- **10 Features évaluées** : DFII10, DXY, GVZ, T10Y2Y, EPU.
- **Audit de la feature `feat_macro_dxy_level`** :
  - `H4 H=6b` : $t = +3.72$, $p = 0.0002$ $\rightarrow$ **Rejeté pour Régression Fallacieuse (Séries I(1) non cointégrées, ADF résidus = -0.97 > -3.34)**.
  - `D1 H=5d` : $t = +3.63$, $p = 0.0003$ $\rightarrow$ **Rejeté pour Régression Fallacieuse (ADF résidus = -1.09 > -3.34)**.
  - Variations $I(0)$ (`dxy_change_1d`, `dxy_change_5d`) : Totalement plates ($|t| \le 1.85$).
- **Résultat Groupe B** : **0 / 52 paires significatives**.

---

### 2.2 Synthétiques (`CRASH1000` & `BOOM1000` - Deriv Natif H4 ~365j)

#### Microstructure du Processus de Spike (H4 Uniquement) :
- **15 Features évaluées** : Fréquence de spikes, Asymétrie, Volatilité Parkinson, Reversion post-jump.
- **Résultat** : Les 6 paires ayant $p \in [0.021, 0.033]$ ne franchissent pas le seuil critique BH ($N_{\text{tests}} = 188$). **0 / 60 paires significatives**.

---

## 3. CONCLUSION ET VERDICT DU JALON DE RECHERCHE DE FEATURES

**0 / 188 HYPOTHÈSES NE FRANCHIT LE CONTRÔLE STATISTIQUE RIGOURANT (TESTS MULTIPLES + DÉTECTION DE RÉGRESSION FALLACIEUSE).**
Toutes les pistes (Haute Fréquence M1, Fréquence Intermédiaire H4/D1, Indicateurs Techniques, Microstructure Spike, et Niveaux Macro non cointégrés) sont **RÉFUTÉES ET FERMÉES**.
