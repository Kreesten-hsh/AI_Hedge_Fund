# RAPPORT D'AUDIT ÉCONOMÉTRIQUE : RÉGRESSION FALLACIEUSE DXY VS GOLD

## 1. Contexte du Test et Hypothèse d'Artefact

Suite à l'identification de la statistique $t = +3.72$ sur `feat_macro_dxy_level`, un audit économétrique d'intégration et de cointégration (Granger & Newbold 1974, Engle & Granger 1987) a été mené pour vérifier si ce t-stat est le résultat d'une tendance partagée non-stationnaire (spurious regression) ou d'un vrai signal.

## 2. Tests de Stationnarité (Augmented Dickey-Fuller)

| Série Évaluée | Nature de la Série | ADF t-stat | Seuil Critique 5% | Ordre d'Intégration |
| :--- | :--- | :--- | :--- | :--- |
| **Gold Close** | Niveau brut D1 | **+0.70** | -2.86 | **I(1) Non-Stationnaire** |
| **DXY Index (`DTWEXBGS`)** | Niveau brut D1 | **-2.68** | -2.86 | **I(1) Non-Stationnaire** |
| **Gold Return** | Variation % D1 | **-24.34** | -2.86 | **I(0) Stationnaire** |
| **DXY Change 1d** | Variation 1j D1 | **-24.23** | -2.86 | **I(0) Stationnaire** |
| **DXY Change 5d** | Variation 5j D1 | **-23.88** | -2.86 | **I(0) Stationnaire** |

## 3. Test de Cointégration d'Engle-Granger

| Timeframe | OLS Fit Spread | Résidus ADF t-stat | Seuil Critique 5% | Statut Cointégration |
| :--- | :--- | :--- | :--- | :--- |
| **D1** | $P_{Gold} = -8555.5 + 89.91 \cdot DXY$ | **-1.09** | -3.34 | **❌ NON COINTÉGRÉ (Spurious)** |
| **H4** | $P_{Gold} = -8545.5 + 89.82 \cdot DXY$ | **-0.97** | -3.34 | **❌ NON COINTÉGRÉ (Spurious)** |

## 4. Conclusion Économétrique et Rejet de `feat_macro_dxy_level`

> [!CAUTION]
> **REJET DÉFINITIF POUR RÉGRESSION FALLACIEUSE (SPURIOUS REGRESSION)**
> 1. Les séries de niveau Gold et DXY sont toutes deux **$I(1)$ non-stationnaires** ($ADF > -2.86$).
> 2. Le test de cointégration d'Engle-Granger échoue ($ADF = -1.09 > -3.34$), prouvant qu'aucune relation d'équilibre stationnaire n'existe entre les niveaux.
> 3. Les variations stationnaires $I(0)$ (`dxy_change_1d`, `dxy_change_5d`) n'affichent aucun pouvoir prédictif ($|t| < 2.0$).
> **Conclusion** : Le t-stat $t = +3.72$ sur `feat_macro_dxy_level` est un artefact d'intégration $I(1)$ sans valeur prédictive. Le score de la Tâche 2 est révisé à **0 / 188 features valides**.
