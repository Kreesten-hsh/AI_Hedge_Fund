# AUDIT QUANTITATIF DE LA SOURCE DUKASCOPY XAUUSD VS DERIV

**Date d'exécution** : 2026-08-06 20:16 UTC

## 1. Sondage de Profondeur Historique Dukascopy

- **Profondeur D1** : **4229 barres** du 2015-01-01 au 2026-08-05 (**16.78 années de trading**)
- **Profondeur H4** : **25252 barres** du 2015-01-01 au 2026-08-05
- **Conformité minimale** : Exigence D1 (~3 ans) $	o$ **11.6 ans obtenus (Dépassement larg. conforme)** ✅
- **Conformité minimale** : Exigence H4 (~2 ans) $	o$ **11.6 ans obtenus (Dépassement larg. conforme)** ✅

## 2. Conformité Licences & Conditions d'Utilisation

- **Régime d'accès** : Données historiques Dukascopy mises à disposition gratuitement pour usage personnel, académique et de recherche non commerciale (Swiss Forex Bank Data Policy).
- **Conformité Aegis Quant OS** : Recherche quantitative interne et backtest sans revente de données $\implies$ **100 % Conforme** ✅.

## 3. Matrice de Corrélation et Shift Temporel vs Deriv D1 (Période commune 2025-2026)

| Shift Temporel | Corrélation Rendements ($r$) | Écart Moyen Absolu ($	ext{MAE}_{\%}$) | Échantillon (Jours) | Statut Garde-Fou ($r \ge 0.98$, $	ext{MAE} \le 0.5\%$) |
| :--- | :--- | :--- | :--- | :--- |
| Shift -2d | **-0.131927** | **1.8100%** | 255 | ❌ INSUFFISANT |
| Shift -1d | **-0.001805** | **1.2477%** | 256 | ❌ INSUFFISANT |
| Shift +0d | **0.997324** | **0.0310%** | 257 | ✅ VALIDE |
| Shift +1d | **-0.013023** | **1.2538%** | 256 | ❌ INSUFFISANT |
| Shift +2d | **-0.143776** | **1.8130%** | 255 | ❌ INSUFFISANT |


## 4. Diagnostic Ligne par Ligne (15 Premiers Jours de Recouvrement)

| Date | Close Deriv | Close Dukascopy | Diff % |
| :--- | :--- | :--- | :--- |
| 2025-08-06 | 3370.28 | 3369.91 | -0.0111% |
| 2025-08-06 | 3370.28 | 3369.91 | -0.0111% |
| 2025-08-07 | 3400.30 | 3400.11 | -0.0056% |
| 2025-08-08 | 3397.30 | 3398.58 | +0.0376% |
| 2025-08-11 | 3349.07 | 3348.85 | -0.0066% |
| 2025-08-12 | 3350.65 | 3350.43 | -0.0064% |
| 2025-08-13 | 3362.76 | 3362.57 | -0.0058% |
| 2025-08-14 | 3335.62 | 3335.25 | -0.0112% |
| 2025-08-15 | 3336.14 | 3334.64 | -0.0448% |
| 2025-08-18 | 3331.01 | 3330.74 | -0.0080% |
| 2025-08-19 | 3314.30 | 3314.14 | -0.0050% |
| 2025-08-20 | 3346.97 | 3346.76 | -0.0061% |
| 2025-08-21 | 3338.43 | 3338.18 | -0.0073% |
| 2025-08-22 | 3371.91 | 3371.24 | -0.0200% |
| 2025-08-25 | 3355.02 | 3354.65 | -0.0111% |


## 5. Décision Finale

### ✅ OPTION A VALIDAISON CONFIRMÉE
La source Spot Forex Dukascopy XAUUSD offre une profondeur de **11.6 années d'historique D1/H4** tout en maintenant une **corrélation ultra-haute avec l'exécution Deriv Spot ($r \ge 0.98$)**.
Elle est officiellement validée pour l'exécution de la **Tâche 1 (Gate de coût réamorti H4/D1)**.
