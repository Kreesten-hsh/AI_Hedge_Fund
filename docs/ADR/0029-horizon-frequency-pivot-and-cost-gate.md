# ADR 0029 — Pivot Fréquence H4/D1 & Validation du Gate de Coût Économique

- **Statut** : ACCEPTÉ (Validé sur horizons H4 et D1)
- **Date** : 2026-08-06
- **Contexte technique** : `scripts/evaluate_horizon_cost_gate.py`, `docs/research/H4_D1_TRADABILITY_GATE_REPORT.md`, `docs/research/DUKASCOPY_GOLD_AUDIT.md`
- **Dépend de** : ADR 0021 (coût mesuré A/R 1.859 bps), ADR 0025 (rejet Tech M1), ADR 0027 (rejet Macro M1), ADR 0028 (rejet Council M1)
- **Résout** : Priorité 1 Active du Backlog — Pivot de Fréquence & Régime d'Horizon (H4/D1)

---

## Contexte et Rationale du Pivot

La haute fréquence M1 a été rigoureusement réfutée sur tous les axes d'analyse (ADR 0025, 0027, 0028). La micro-structure M1 est dominée par le bruit stochastique et des allers-retours de péage ($1.859 \text{ bps}$) qui absorbent 11 fois le mouvement moyen brut capté ($+0.165 \text{ bps}$).

Ce pivot de fréquence vers les agrégations **4-Heures (H4)** et **Quotidiennes (D1)** vise à réamortir le péage d'exécution sur des amplitudes macro-économiques et de tendance de taille largement supérieure (> 18 à 135 bps).

---

## 1. Données et Sources Validées (Ségrégation Stricte)

1. **Gold (`XAUUSD`) — Source Longue Externe (Dukascopy Swiss Forex Bank)** :
   - **Historique** : **11.6 années calendaires** (01/01/2015 au 05/08/2026) soit **4 229 barres D1** et **25 252 barres H4**.
   - **Garde-fou** : Validé par audit quantitatif ([docs/research/DUKASCOPY_GOLD_AUDIT.md](file:///mnt/WindowsData/AI_Hedge_Fund/docs/research/DUKASCOPY_GOLD_AUDIT.md)) avec corrélation ultra-haute **$r = 0.997324$** et $\text{MAE}_{\%} = 0.0310\%$ par rapport à Deriv Spot Or.

2. **Indices Synthétiques (`CRASH1000`, `BOOM1000`) — Source Natif Deriv (365 jours)** :
   - **Historique** : 366 barres D1 et 2 191 barres H4 (du 06/08/2025 au 06/08/2026).
   - **Ségrégation** : Traités de manière totalement indépendante du Gold, les synthétiques n'existant sur aucune banque externe.

---

## 2. Résultats de la Tâche 1 : Gate de Tradabilité Économique vs Péage (1.859 bps)

### A. Gold (`XAUUSD` - Dukascopy 11.6 ans)

| Timeframe | Horizon H | Mouvement Absolu Moyen | Ratio Couverture (vs 1.859 bps) | % Fenêtres > Péage | $n_{\text{eff, global}}$ | $n_{\text{eff, holdout}}$ (30% Split) | Statut Gate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **D1** | **H=1d** | **52.66 bps** | **28.3x** | **82.6%** | 4 228.0 | **1 268.0** | ✅ **PASS** |
| **D1** | **H=5d** | **135.20 bps** | **72.7x** | **98.9%** | 842.8 | **252.8** | ✅ **PASS** |
| **H4** | **H=1b (4h)** | **18.38 bps** | **9.9x** | **68.3%** | 25 251.0 | **7 575.0** | ✅ **PASS** |
| **H4** | **H=6b (24h)** | **52.41 bps** | **28.2x** | **83.2%** | 4 208.3 | **1 261.7** | ✅ **PASS** |

*Verdict Gold* : Gate économique et statistique franchi avec un confort exceptionnel ($n_{\text{eff, holdout}} > 250$ sur tous les horizons, couverture $9.9\times$ à $72.7\times$).

---

### B. Crash 1000 Index (`CRASH1000` - Deriv Natif 365j)

| Timeframe | Horizon H | Mouvement Absolu Moyen | Ratio Couverture (vs 1.859 bps) | % Fenêtres > Péage | $n_{\text{eff, global}}$ | $n_{\text{eff, holdout}}$ (30% Split) | Statut Gate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **D1** | **H=1d** | **92.20 bps** | **49.6x** | **99.7%** | 365.0 | **109.0** | ✅ **PASS** |
| **D1** | **H=5d** | **202.88 bps** | **109.1x** | **99.2%** | 70.0 | **21.0** ($<30$) | ❌ **FAIL (Échantillon)** |
| **H4** | **H=1b (4h)** | **36.61 bps** | **19.7x** | **96.6%** | 2 190.0 | **657.0** | ✅ **PASS** |
| **H4** | **H=6b (24h)** | **92.40 bps** | **49.7x** | **98.9%** | 362.5 | **108.7** | ✅ **PASS** |

---

### C. Boom 1000 Index (`BOOM1000` - Deriv Natif 365j)

| Timeframe | Horizon H | Mouvement Absolu Moyen | Ratio Couverture (vs 1.859 bps) | % Fenêtres > Péage | $n_{\text{eff, global}}$ | $n_{\text{eff, holdout}}$ (30% Split) | Statut Gate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **D1** | **H=1d** | **87.08 bps** | **46.8x** | **98.4%** | 365.0 | **109.0** | ✅ **PASS** |
| **D1** | **H=5d** | **213.61 bps** | **114.9x** | **99.7%** | 70.0 | **21.0** ($<30$) | ❌ **FAIL (Échantillon)** |
| **H4** | **H=1b (4h)** | **35.96 bps** | **19.3x** | **96.3%** | 2 190.0 | **657.0** | ✅ **PASS** |
| **H4** | **H=6b (24h)** | **90.15 bps** | **48.5%** | **98.9%** | 362.5 | **108.7** | ✅ **PASS** |

---

## 3. Décisions d'Architecture Scellées

1. **Adoption Officielle des Horizons H4 et D1** :
   - Le péage d'exécution ($1.859 \text{ bps}$) ne représente plus que **1.4 % à 10.1 % du mouvement moyen** sur H4/D1 (contre $1100\%$ sur M1).
2. **Priorisation des Timeframes par Actif** :
   - **Gold** : Tradable et éligible sur D1 ($H \in [1d, 5d]$) et H4 ($H \in [1b, 6b]$) avec validation Walk-Forward complète sur 11.6 ans.
   - **Synthétiques (Crash/Boom)** : Retenus prioritairement sur **H4 ($H \in [1b, 6b]$)** pour maintenir $n_{\text{eff, holdout}} \ge 108$ malgré l'historique natif de 1 an.
3. **Passage à la Tâche 2 (Recherche de Features H4/D1)** :
   - Autorisation d'engager la recherche de features et le calcul de la significativité statistique ($t$-stat, IC) sur H4 et D1.
