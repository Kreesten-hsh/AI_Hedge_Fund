# RAPPORT QUANTITATIF DE RECHERCHE DE FEATURES H4 / D1 (TÂCHE 2)

**Date d'exécution** : 2026-08-07 01:06 UTC
**Nombre Total d'Hypothèses Évaluées ($N_{\text{tests}}$)** : **`128`**
**Seuil Brut non-ajusté ($|t| \ge 2.0$)** : $\alpha = 0.05$ (~5% de faux positifs attendus par pur hasard)
**Seuil de Bonferroni Ajusté** : $\alpha_{\text{bonf}} = 0.000391$ ($|t| \ge 3.546$)
**Seuil Benjamini-Hochberg (FDR $q = 0.05$)** : Taux de fausses découvertes contrôlé à 5%

## 1. Synthèse Globale de Significativité

| Statut de Filtrage | Seuil de Tolérance | Nb Features Significatives | Taux de Significativité |
| :--- | :--- | :--- | :--- |
| **Brut univarié (Non ajusté)** | $|t| \ge 2.00$ ($p \le 0.05$) | 4 / 128 | 3.1% |
| **Benjamini-Hochberg (FDR $q=0.05$)** | $p \le \text{BH}_{\text{crit}}$ | **0 / 128** | **0.0%** |
| **Bonferroni (Conservateur)** | $|t| \ge 3.55$ ($p \le 0.000391$) | **0 / 128** | **0.0%** |

## 2. Résultats Détaillés par Actif (Ségrégation Stricte)

### 2.1 Gold (`XAUUSD` - Dukascopy 11.6 ans)

#### A. Features Techniques (D1 et H4) :

| Timeframe | Horizon H | Feature Name | Spearman IC | t-stat Newey-West | p-valeur brute | BH (q=0.05) | Bonferroni |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| H4 | H=1 | `feat_bollinger_pband` | -0.0077 | **+1.81** | 0.0706 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_rsi_28` | +0.0138 | **+1.70** | 0.0896 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_bollinger_pband` | -0.0049 | **+1.24** | 0.2161 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_return_2d` | -0.0308 | **-1.20** | 0.2316 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_return_2d` | -0.0177 | **-1.10** | 0.2705 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_macd_hist` | +0.0022 | **-1.08** | 0.2821 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_rsi_28` | +0.0004 | **+1.04** | 0.2995 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_return_10d` | +0.0165 | **-1.02** | 0.3096 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_return_1d` | +0.0043 | **-0.99** | 0.3209 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_bollinger_wband` | +0.0307 | **+0.98** | 0.3275 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_ema_10_ratio` | -0.0074 | **-0.97** | 0.3320 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_return_5d` | -0.0029 | **-0.95** | 0.3422 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_macd_hist` | +0.0038 | **-0.93** | 0.3529 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_return_10d` | -0.0125 | **-0.92** | 0.3598 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_ema_20_ratio` | -0.0090 | **-0.87** | 0.3838 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_volatility_20` | -0.0046 | **-0.86** | 0.3903 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_volatility_20` | +0.0072 | **-0.81** | 0.4156 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_ema_cross_10_50` | +0.0038 | **-0.81** | 0.4161 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_return_3d` | -0.0122 | **+0.81** | 0.4170 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_return_3d` | -0.0190 | **-0.80** | 0.4236 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_return_10d` | +0.0047 | **-0.80** | 0.4251 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_bollinger_pband` | +0.0279 | **+0.78** | 0.4346 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_high_low_ratio` | -0.0140 | **-0.77** | 0.4391 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_close_open_ratio` | +0.0066 | **-0.77** | 0.4402 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_ema_10_ratio` | +0.0218 | **-0.75** | 0.4538 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_ema_20_ratio` | +0.0153 | **-0.74** | 0.4616 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_rsi_14` | +0.0046 | **+0.73** | 0.4651 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_return_1d` | -0.0365 | **-0.73** | 0.4673 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_volatility_50` | -0.0176 | **-0.73** | 0.4677 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_rsi_14` | +0.0218 | **+0.72** | 0.4691 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_ema_50_ratio` | +0.0024 | **-0.68** | 0.4937 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_macd_hist` | -0.0267 | **-0.67** | 0.5008 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_return_2d` | +0.0115 | **-0.65** | 0.5158 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_volatility_50` | -0.0106 | **-0.63** | 0.5275 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_return_2d` | -0.0100 | **+0.63** | 0.5307 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_ema_50_ratio` | +0.0013 | **-0.60** | 0.5512 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_ema_200_ratio` | +0.0066 | **-0.59** | 0.5532 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_ema_cross_10_50` | +0.0045 | **-0.58** | 0.5647 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_return_5d` | -0.0121 | **+0.57** | 0.5656 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_bollinger_wband` | +0.0052 | **-0.57** | 0.5672 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_bollinger_pband` | -0.0003 | **+0.56** | 0.5746 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_ema_50_ratio` | -0.0023 | **-0.54** | 0.5870 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_close_open_ratio` | -0.0318 | **-0.54** | 0.5903 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_ema_200_ratio` | +0.0051 | **-0.54** | 0.5922 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_ema_20_ratio` | -0.0071 | **-0.53** | 0.5987 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_return_5d` | +0.0245 | **-0.49** | 0.6276 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_ema_20_ratio` | -0.0094 | **-0.46** | 0.6478 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_bollinger_wband` | -0.0020 | **-0.45** | 0.6511 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_rsi_14` | -0.0069 | **+0.45** | 0.6539 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_close_open_ratio` | -0.0061 | **-0.43** | 0.6666 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_return_1d` | -0.0063 | **-0.43** | 0.6686 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_ema_50_ratio` | +0.0283 | **-0.42** | 0.6762 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_return_5d` | -0.0125 | **+0.42** | 0.6764 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_return_1d` | -0.0074 | **+0.39** | 0.6965 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_high_low_ratio` | +0.0124 | **-0.39** | 0.6999 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_high_low_ratio` | +0.0031 | **-0.38** | 0.7010 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_volatility_20` | -0.0000 | **+0.38** | 0.7051 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_return_3d` | +0.0168 | **-0.35** | 0.7251 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_bollinger_wband` | +0.0060 | **+0.35** | 0.7277 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_ema_10_ratio` | -0.0154 | **-0.35** | 0.7289 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_close_open_ratio` | -0.0066 | **+0.34** | 0.7363 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_rsi_28` | -0.0027 | **-0.30** | 0.7668 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_return_10d` | -0.0048 | **-0.28** | 0.7776 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_ema_cross_10_50` | +0.0103 | **-0.26** | 0.7949 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_return_3d` | -0.0195 | **-0.25** | 0.8008 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_rsi_14` | -0.0099 | **+0.25** | 0.8036 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_macd_hist` | -0.0128 | **+0.22** | 0.8228 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_ema_200_ratio` | +0.0158 | **-0.19** | 0.8494 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_high_low_ratio` | +0.0125 | **+0.16** | 0.8749 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_ema_cross_10_50` | +0.0305 | **-0.13** | 0.8928 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_ema_10_ratio` | -0.0129 | **-0.10** | 0.9236 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_rsi_28` | -0.0014 | **+0.10** | 0.9238 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_volatility_50` | -0.0002 | **+0.08** | 0.9385 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_ema_200_ratio` | +0.0385 | **+0.08** | 0.9389 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_volatility_20` | -0.0082 | **-0.04** | 0.9658 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_volatility_50` | +0.0061 | **+0.01** | 0.9938 | ❌ NOT SIG | ❌ NOT SIG |


### 2.2 Synthétiques (`CRASH1000` & `BOOM1000` - Deriv Natif H4 ~365j)

#### Microstructure du Processus de Spike (H4 Uniquement) :

| Actif | Horizon H | Feature Name | Spearman IC | t-stat Newey-West | p-valeur brute | BH (q=0.05) | Bonferroni |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Crash 1000 | H=1 | `feat_min_spike_intensity_6b` | +0.0431 | **+2.30** | 0.0213 | ❌ NOT SIG | ❌ NOT SIG |
| Crash 1000 | H=1 | `feat_parkinson_vol_6b` | -0.0422 | **-2.20** | 0.0276 | ❌ NOT SIG | ❌ NOT SIG |
| Boom 1000 | H=1 | `feat_min_spike_intensity_6b` | +0.0393 | **+2.16** | 0.0311 | ❌ NOT SIG | ❌ NOT SIG |
| Crash 1000 | H=6 | `feat_spike_freq_6b` | -0.0719 | **-2.13** | 0.0332 | ❌ NOT SIG | ❌ NOT SIG |
| Crash 1000 | H=6 | `feat_min_spike_intensity_6b` | +0.0632 | **+1.99** | 0.0467 | ❌ NOT SIG | ❌ NOT SIG |
| Crash 1000 | H=1 | `feat_realized_vol_6b` | -0.0337 | **-1.87** | 0.0617 | ❌ NOT SIG | ❌ NOT SIG |
| Crash 1000 | H=1 | `feat_return_1b` | +0.0503 | **+1.84** | 0.0657 | ❌ NOT SIG | ❌ NOT SIG |
| Boom 1000 | H=6 | `feat_bollinger_pband` | +0.0649 | **+1.81** | 0.0708 | ❌ NOT SIG | ❌ NOT SIG |
| Boom 1000 | H=1 | `feat_bollinger_pband` | +0.0180 | **+1.50** | 0.1325 | ❌ NOT SIG | ❌ NOT SIG |
| Boom 1000 | H=6 | `feat_return_1b` | +0.0236 | **+1.33** | 0.1842 | ❌ NOT SIG | ❌ NOT SIG |
| Boom 1000 | H=1 | `feat_spike_freq_6b` | +0.0306 | **+1.33** | 0.1848 | ❌ NOT SIG | ❌ NOT SIG |
| Crash 1000 | H=1 | `feat_spike_freq_6b` | -0.0290 | **-1.30** | 0.1951 | ❌ NOT SIG | ❌ NOT SIG |
| Boom 1000 | H=6 | `feat_rsi_14` | +0.0691 | **+1.27** | 0.2032 | ❌ NOT SIG | ❌ NOT SIG |
| Crash 1000 | H=6 | `feat_parkinson_vol_6b` | -0.0437 | **-1.26** | 0.2080 | ❌ NOT SIG | ❌ NOT SIG |
| Boom 1000 | H=6 | `feat_min_spike_intensity_6b` | +0.0656 | **+1.21** | 0.2258 | ❌ NOT SIG | ❌ NOT SIG |
| Boom 1000 | H=6 | `feat_spike_freq_6b` | +0.0375 | **+1.13** | 0.2587 | ❌ NOT SIG | ❌ NOT SIG |
| Crash 1000 | H=6 | `feat_return_skew_12b` | +0.0234 | **+1.12** | 0.2633 | ❌ NOT SIG | ❌ NOT SIG |
| Boom 1000 | H=1 | `feat_rsi_14` | +0.0206 | **+1.09** | 0.2745 | ❌ NOT SIG | ❌ NOT SIG |
| Crash 1000 | H=6 | `feat_kurtosis_24b` | -0.0305 | **-1.06** | 0.2880 | ❌ NOT SIG | ❌ NOT SIG |
| Crash 1000 | H=6 | `feat_return_3b` | +0.0337 | **+0.98** | 0.3282 | ❌ NOT SIG | ❌ NOT SIG |
| Crash 1000 | H=1 | `feat_return_3b` | +0.0305 | **+0.90** | 0.3659 | ❌ NOT SIG | ❌ NOT SIG |
| Boom 1000 | H=6 | `feat_spike_freq_24b` | +0.0313 | **+0.90** | 0.3660 | ❌ NOT SIG | ❌ NOT SIG |
| Crash 1000 | H=6 | `feat_spike_freq_24b` | -0.0451 | **-0.90** | 0.3677 | ❌ NOT SIG | ❌ NOT SIG |
| Crash 1000 | H=6 | `feat_return_1b` | +0.0134 | **+0.87** | 0.3833 | ❌ NOT SIG | ❌ NOT SIG |
| Crash 1000 | H=6 | `feat_realized_vol_6b` | -0.0247 | **-0.85** | 0.3930 | ❌ NOT SIG | ❌ NOT SIG |
| Crash 1000 | H=1 | `feat_max_spike_intensity_6b` | -0.0176 | **-0.84** | 0.4005 | ❌ NOT SIG | ❌ NOT SIG |
| Boom 1000 | H=1 | `feat_spike_freq_24b` | +0.0209 | **+0.82** | 0.4115 | ❌ NOT SIG | ❌ NOT SIG |
| Boom 1000 | H=6 | `feat_return_skew_12b` | -0.0129 | **-0.80** | 0.4212 | ❌ NOT SIG | ❌ NOT SIG |
| Crash 1000 | H=1 | `feat_bollinger_pband` | +0.0215 | **+0.75** | 0.4557 | ❌ NOT SIG | ❌ NOT SIG |
| Boom 1000 | H=6 | `feat_return_3b` | +0.0161 | **+0.66** | 0.5087 | ❌ NOT SIG | ❌ NOT SIG |
| Boom 1000 | H=1 | `feat_kurtosis_24b` | +0.0223 | **+0.66** | 0.5112 | ❌ NOT SIG | ❌ NOT SIG |
| Crash 1000 | H=6 | `feat_max_spike_intensity_6b` | +0.0137 | **+0.65** | 0.5146 | ❌ NOT SIG | ❌ NOT SIG |
| Crash 1000 | H=6 | `feat_return_skew_24b` | +0.0369 | **+0.64** | 0.5208 | ❌ NOT SIG | ❌ NOT SIG |
| Boom 1000 | H=6 | `feat_kurtosis_24b` | +0.0390 | **+0.62** | 0.5326 | ❌ NOT SIG | ❌ NOT SIG |
| Boom 1000 | H=1 | `feat_max_spike_intensity_6b` | -0.0040 | **+0.61** | 0.5395 | ❌ NOT SIG | ❌ NOT SIG |
| Crash 1000 | H=1 | `feat_return_skew_24b` | +0.0192 | **+0.60** | 0.5474 | ❌ NOT SIG | ❌ NOT SIG |
| Crash 1000 | H=1 | `feat_rsi_14` | +0.0047 | **+0.58** | 0.5629 | ❌ NOT SIG | ❌ NOT SIG |
| Crash 1000 | H=1 | `feat_return_skew_12b` | +0.0091 | **+0.54** | 0.5878 | ❌ NOT SIG | ❌ NOT SIG |
| Crash 1000 | H=1 | `feat_spike_freq_24b` | -0.0056 | **-0.48** | 0.6338 | ❌ NOT SIG | ❌ NOT SIG |
| Boom 1000 | H=6 | `feat_realized_vol_6b` | -0.0093 | **-0.37** | 0.7087 | ❌ NOT SIG | ❌ NOT SIG |
| Boom 1000 | H=6 | `feat_parkinson_vol_6b` | +0.0092 | **+0.29** | 0.7719 | ❌ NOT SIG | ❌ NOT SIG |
| Boom 1000 | H=6 | `feat_max_spike_intensity_6b` | -0.0096 | **-0.26** | 0.7967 | ❌ NOT SIG | ❌ NOT SIG |
| Boom 1000 | H=1 | `feat_realized_vol_6b` | +0.0036 | **-0.25** | 0.8028 | ❌ NOT SIG | ❌ NOT SIG |
| Crash 1000 | H=6 | `feat_rsi_14` | -0.0130 | **+0.25** | 0.8059 | ❌ NOT SIG | ❌ NOT SIG |
| Crash 1000 | H=6 | `feat_bollinger_pband` | +0.0039 | **+0.24** | 0.8124 | ❌ NOT SIG | ❌ NOT SIG |
| Boom 1000 | H=6 | `feat_return_skew_24b` | +0.0130 | **+0.21** | 0.8354 | ❌ NOT SIG | ❌ NOT SIG |
| Boom 1000 | H=1 | `feat_return_skew_12b` | -0.0034 | **-0.20** | 0.8396 | ❌ NOT SIG | ❌ NOT SIG |
| Boom 1000 | H=1 | `feat_return_skew_24b` | +0.0013 | **+0.16** | 0.8690 | ❌ NOT SIG | ❌ NOT SIG |
| Boom 1000 | H=1 | `feat_return_1b` | -0.0069 | **+0.16** | 0.8746 | ❌ NOT SIG | ❌ NOT SIG |
| Crash 1000 | H=1 | `feat_kurtosis_24b` | -0.0154 | **-0.13** | 0.8956 | ❌ NOT SIG | ❌ NOT SIG |
| Boom 1000 | H=1 | `feat_parkinson_vol_6b` | +0.0016 | **+0.10** | 0.9217 | ❌ NOT SIG | ❌ NOT SIG |
| Boom 1000 | H=1 | `feat_return_3b` | +0.0005 | **+0.06** | 0.9511 | ❌ NOT SIG | ❌ NOT SIG |


## 3. CONCLUSION ET DÉCISION DU JALON DE RECHERCHE DE FEATURES

**0 feature ne franchit la correction pour tests multiples Benjamini-Hochberg / Bonferroni avec significativité à q=0.05**.
