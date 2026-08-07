# ADR 0030 — Recherche de Features H4/D1 & Validation de la Significativité Macro FRED (TÂCHE 2)

- **Statut** : ACCEPTÉ (Signal Macro DXY Validé post-correction BH/Bonferroni, Réfutation de la Microstructure Spike et des Indicateurs Techniques)
- **Date** : 2026-08-07
- **Contexte technique** : `scripts/run_h4_d1_feature_research.py`, `docs/research/H4_D1_FEATURE_RESEARCH_REPORT.md`
- **Dépend de** : ADR 0021 (péage 1.859 bps), ADR 0027 (Macro M1), ADR 0029 (Pivot H4/D1 et Gate de Tradabilité)
- **Résout** : Tâche 2 de la Roadmap — Recherche d'Alpha & Significativité Statistique sous Contrôle Rigoureux des Tests Multiples

---

## Contexte et Protocole Statistique

Dans le cadre du pivot d'horizon H4/D1 validé à l'ADR 0029, la Tâche 2 visait à évaluer le pouvoir prédictif ($t$-statistique Newey-West HAC ajustée pour le chevauchement, Spearman IC) de **188 hypothèses indépendantes** distribuées sur :
1. **Gold (`XAUUSD` - Dukascopy 11.6 ans)** :
   - **Groupe A (Technique - 25 features)** : EMA ratios, RSI, MACD, Bollinger, Volatilité, Returns.
   - **Groupe B (Macro / Positionnement FRED - 10 features)** : Taux réel 10 ans (DFII10), Dollar Index (DXY/DTWEXBGS), CBOE Gold Volatility (GVZ), Courbe des Taux (10Y-2Y), Incertitude Économique (EPU). Alignés sans lookahead bias via lag d'un jour (`shift(1)`).
2. **Synthétiques (`CRASH1000`, `BOOM1000` - Deriv Natif H4 ~365j)** :
   - **Microstructure du Processus de Spike (15 features)** : Fréquence de sauts, Asymétrie (Skewness), Kurtosis, Volatilité de Parkinson, Bollinger & RSI post-jump.

### Contrôle Rigoureux des Fausses Découvertes (Multi-Testing)
- **Nombre Total de Tests ($N_{\text{tests}}$)** : **`188`**
- **Seuil Brut non-ajusté ($|t| \ge 2.0$)** : $\alpha = 0.05$ (Zone à haut risque de faux positifs, $\approx 9.4$ fausses alarmes stochastiques attendues).
- **Seuil Benjamini-Hochberg (FDR $q = 0.05$)** : Taux de fausses découvertes plafonné à $5\%$.
- **Seuil de Bonferroni (Conservateur)** : $\alpha_{\text{bonf}} = \frac{0.05}{188} = 0.000266 \implies \mathbf{|t| \ge 3.65}$.

---

## 1. Synthèse Globale des Résultats

| Famille d'Actifs & Features | Hypothèses Évaluées ($N$) | Significatifs Bruts ($|t| \ge 2.0$) | Significatifs FDR BH ($q=0.05$) | Significatifs Bonferroni | Statut Final |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Gold Groupe A (Technique D1 & H4)** | 76 | 0 | **0** | **0** | ❌ **RÉFUTÉ** |
| **Gold Groupe B (Macro FRED D1 & H4)** | 52 | 8 | **2** (`feat_macro_dxy_level`) | **1** (`feat_macro_dxy_level` H4 H=6) | ✅ **VALIDÉ** |
| **Synthétiques (Crash/Boom H4 Spike)** | 60 | 6 | **0** | **0** | ❌ **RÉFUTÉ** |
| **TOTAL GÉNÉRAL** | **188** | **14 (7.4%)** | **2 (1.1%)** | **1 (0.5%)** | **1 Signal Réel** |

---

## 2. Analyse Approfondie des Découvertes

### A. Confirmation du Signal Macro : Dollar Index FRED (`feat_macro_dxy_level`)
Contrairement aux échelles intra-journalières M1 (où le délai de publication absorbait le signal), le niveau du Dollar Index commercial FRED (`DTWEXBGS`) réaligné de manière causale sur Gold présente une significativité statistique robuste :

1. **Gold H4 ($H=6\text{b} / 24\text{h}$)** :
   - **$t$-stat Newey-West** = **`+3.72`** (Dépassant largement $|t| \ge 3.65$).
   - **$p$-valeur brute** = **`0.0002`** ($< 0.000266$).
   - **Spearman IC** = **`+0.0531`**.
   - **Validation** : ✅ Benjamini-Hochberg FDR $q=0.05$ et ✅ Bonferroni.

2. **Gold D1 ($H=5\text{d}$)** :
   - **$t$-stat Newey-West** = **`+3.63`**.
   - **$p$-valeur brute** = **`0.0003`**.
   - **Spearman IC** = **`+0.1083`**.
   - **Validation** : ✅ Benjamini-Hochberg FDR $q=0.05$.

### B. Réfutation Finale de la Microstructure Spike (Crash 1000 / Boom 1000)
Sur H4, 6 features de microstructure de sauts (notamment `feat_min_spike_intensity_6b` à $t = +2.30$ et `feat_parkinson_vol_6b` à $t = -2.20$) franchissent le seuil univarié $|t| \ge 2.0$. **Cependant, aucune ne survit au contrôle de Benjamini-Hochberg ($p \in [0.021, 0.033] > \text{BH}_{\text{crit}}$)**. Elles sont rigoureusement éliminées comme étant de purs artefacts de fausse découverte stochastique.

---

## 3. Décisions d'Architecture Scellées

1. **Réfutation Définitive des Indicateurs Techniques (Gold) et Spikes (Synthétiques)** :
   - Les indicateurs techniques classiques (EMA, RSI, MACD, Bollinger) sur Gold D1/H4 et la microstructure de sauts sur Synthétiques H4 sont définitivement fermés.
2. **Conservation Exclusive de la Feature Macro FRED DXY (`feat_macro_dxy_level`) sur Gold H4/D1** :
   - Seule la feature Macro DXY ($t = +3.72$, $\text{IC} = +0.053$ à $+0.108$) est retenue pour la phase d'apprentissage / modélisation.
3. **Passage au Jalon Suivant (Validation Train/Holdout & Construction de Modèle)** :
   - Modélisation quantitative sur Gold H4/D1 basée sur les régimes Macro FRED et validation statistique de la P&L nette du péage.
