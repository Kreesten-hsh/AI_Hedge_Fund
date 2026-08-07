# RAPPORT QUANTITATIF DE RECHERCHE DE FEATURES DE POSITIONNEMENT (CFTC COT & GLD ETF)

**Nombre Total d'Hypothèses Évaluées dans la Famille ($N_{\text{pos}}$)** : **`28`**
**Seuil de Bonferroni Ajusté sur la Famille** : $\alpha = 0.001786$ ($|t| \ge 3.124$)
**Seuil Benjamini-Hochberg (FDR $q=0.05$)** : Taux de fausses découvertes contrôlé à 5%

## 1. Audit de Stationnarité ADF Préalable (Règle ADR 0030)

| Feature Name | Description | Nature de la Série | ADF t-stat | Engle-Granger ADF | Statut Économétrique |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `feat_pos_cot_net_spec_level` | Positionnement / Flux | I(0) Stationnaire | **-11.68** | +0.00 | **N/A** |
| `feat_pos_cot_net_spec_change_1w` | Positionnement / Flux | I(0) Stationnaire | **-42.91** | +0.00 | **N/A** |
| `feat_pos_cot_net_spec_change_4w` | Positionnement / Flux | I(0) Stationnaire | **-19.73** | +0.00 | **N/A** |
| `feat_pos_cot_spec_ratio_level` | Positionnement / Flux | I(0) Stationnaire | **-13.84** | +0.00 | **N/A** |
| `feat_pos_gld_volume_level` | Positionnement / Flux | I(0) Stationnaire | **-11.66** | +0.00 | **N/A** |
| `feat_pos_gld_volume_change_1d` | Positionnement / Flux | I(0) Stationnaire | **-34.74** | +0.00 | **N/A** |
| `feat_pos_gld_volume_change_5d` | Positionnement / Flux | I(0) Stationnaire | **-38.62** | +0.00 | **N/A** |


## 2. Résultats des Tests de Significativité (Newey-West & Spearman IC)

| Timeframe | Horizon H | Feature Name | Spearman IC | t-stat Newey-West | p-valeur brute | BH (q=0.05) | Bonferroni |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| D1 | H=1 | `feat_pos_cot_spec_ratio_level` | +0.0009 | **-0.48** | 0.6333 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_pos_cot_spec_ratio_level` | -0.0149 | **-0.44** | 0.6634 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_pos_cot_spec_ratio_level` | +0.0112 | **-0.40** | 0.6860 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_pos_cot_spec_ratio_level` | +0.0035 | **-0.37** | 0.7118 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_pos_cot_net_spec_level` | -0.0061 | **-0.00** | 0.9970 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_pos_cot_net_spec_change_1w` | +0.0124 | **+0.00** | 0.9978 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_pos_cot_net_spec_change_1w` | -0.0137 | **+0.00** | 0.9991 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_pos_cot_net_spec_change_1w` | -0.0112 | **+0.00** | 0.9992 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_pos_cot_net_spec_level` | +0.0060 | **-0.00** | 0.9994 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_pos_cot_net_spec_level` | +0.0068 | **-0.00** | 0.9995 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_pos_cot_net_spec_change_4w` | -0.0233 | **+0.00** | 0.9997 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_pos_cot_net_spec_change_1w` | -0.0010 | **+0.00** | 0.9998 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_pos_cot_net_spec_change_4w` | -0.0207 | **-0.00** | 0.9998 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_pos_cot_net_spec_change_4w` | -0.0171 | **-0.00** | 0.9999 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_pos_cot_net_spec_level` | +0.0114 | **-0.00** | 0.9999 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_pos_cot_net_spec_change_4w` | +0.0003 | **+0.00** | 1.0000 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_pos_gld_volume_change_1d` | -0.0183 | **-0.00** | 1.0000 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_pos_gld_volume_change_1d` | -0.0141 | **-0.00** | 1.0000 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_pos_gld_volume_change_5d` | +0.0052 | **-0.00** | 1.0000 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_pos_gld_volume_level` | +0.0260 | **+0.00** | 1.0000 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_pos_gld_volume_change_5d` | +0.0138 | **-0.00** | 1.0000 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_pos_gld_volume_change_1d` | -0.0114 | **-0.00** | 1.0000 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_pos_gld_volume_change_5d` | -0.0041 | **-0.00** | 1.0000 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_pos_gld_volume_change_1d` | -0.0074 | **-0.00** | 1.0000 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_pos_gld_volume_change_5d` | +0.0026 | **-0.00** | 1.0000 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_pos_gld_volume_level` | +0.0172 | **-0.00** | 1.0000 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_pos_gld_volume_level` | +0.0132 | **-0.00** | 1.0000 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_pos_gld_volume_level` | +0.0166 | **-0.00** | 1.0000 | ❌ NOT SIG | ❌ NOT SIG |


## 3. CONCLUSION ET DÉCISION FINAL DE LA DERNIÈRE PISTE NON FALSIFIÉE

**0 feature de positionnement (CFTC COT Net Speculative Position & GLD ETF Flows) ne franchit la correction pour tests multiples Benjamini-Hochberg FDR q=0.05 ou le filtre de régression fallacieuse**.
