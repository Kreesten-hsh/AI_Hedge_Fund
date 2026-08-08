# RAPPORT QUANTITATIF DE RECHERCHE DE FEATURES DE POSITIONNEMENT COT (CODE 088691)

## 1. Preuve du Filtre CFTC COT Exact et Alignement Causal

- **Colonne CFTC Utilisée** : `CFTC Contract Market Code`
- **Code Contrat Filtré** : **`088691`** (COMEX Gold 100 oz Standard)
- **Historique Traité** : **`604` semaines** de 2015 à 2026
- **Unicité des Semaines** : **`604` dates uniques** (Doublons : `0`)
- **Lag Causal Strict** : Mardi position $\rightarrow$ Utilisable Lundi 00:00 UTC (lag 6 jours / 3 jours ouvrés, ZERO lookahead bias)

### Échantillon de 3 lignes brutes après filtrage :

| Date Mardi | Net Speculative Position | NonCommercial Long | NonCommercial Short |
| :--- | :--- | :--- | :--- |
| 2015-01-06 | **122,178** | 187,705 | 65,527 |
| 2015-01-13 | **130,226** | 192,959 | 62,733 |
| 2015-01-20 | **162,455** | 223,257 | 60,802 |


## 2. Documentation Transparente du Blocage Technique GLD ETF Holdings

> [!WARNING]
> **BLOCAGE TECHNIQUE RÉEL DU TÉLÉCHARGEMENT SPDR ET WORLD GOLD COUNCIL**
> 1. **SPDR Official CSV URL** (`https://www.spdrgoldshares.com/assets/dynamic/GLD/GLD_US_archive_EN.csv`) : Le serveur SPDR renvoie un document **`%PDF-1.5`** déguisé avec une extension `.csv`, bloquant le parsing des avoirs physiques.
> 2. **World Gold Council URL** (`https://www.gold.org/download/file/21037/ETF_Flows_...xlsx`) : Le serveur renvoie une page HTML **`Access denied`** (Cloudflare anti-bot blocking).
> 3. Conformément aux consignes, aucun volume de trading n'a été utilisé comme substitut silencieux. Les flux d'avoirs physiques GLD sont documentés comme **non accessibles sans session navigateur interactive**.

## 3. Audit de Stationnarité ADF Préalable (Règle ADR 0030)

| Feature Name | Description | Nature de la Série | ADF t-stat | Statut Économétrique |
| :--- | :--- | :--- | :--- | :--- |
| `feat_pos_cot_net_spec_level` | Positionnement COT 088691 | I(0) Stationnaire | **-3.13** | ✅ Valide pour test |
| `feat_pos_cot_net_spec_change_1w` | Positionnement COT 088691 | I(0) Stationnaire | **-24.91** | ✅ Valide pour test |
| `feat_pos_cot_net_spec_change_4w` | Positionnement COT 088691 | I(0) Stationnaire | **-10.25** | ✅ Valide pour test |
| `feat_pos_cot_spec_ratio_level` | Positionnement COT 088691 | I(0) Stationnaire | **-3.22** | ✅ Valide pour test |


## 4. Résultats des Tests de Significativité ($N=16$ Paires)

**Seuil de Bonferroni Ajusté sur la Famille COT ($N=16$)** : $\alpha = 0.003125$ ($|t| \ge 2.955$)

| Timeframe | Horizon H | Feature Name | Spearman IC | t-stat Newey-West | p-valeur brute | BH (q=0.05) | Bonferroni |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| D1 | H=5 | `feat_pos_cot_spec_ratio_level` | +0.0198 | **+0.13** | 0.8941 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_pos_cot_spec_ratio_level` | +0.0218 | **-0.11** | 0.9105 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_pos_cot_spec_ratio_level` | +0.0214 | **-0.05** | 0.9625 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_pos_cot_spec_ratio_level` | +0.0207 | **-0.04** | 0.9710 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_pos_cot_net_spec_change_4w` | -0.0436 | **-0.02** | 0.9857 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_pos_cot_net_spec_change_1w` | -0.0310 | **-0.02** | 0.9880 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_pos_cot_net_spec_change_1w` | -0.0269 | **-0.01** | 0.9895 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_pos_cot_net_spec_change_1w` | -0.0093 | **-0.01** | 0.9923 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_pos_cot_net_spec_change_4w` | -0.0312 | **-0.01** | 0.9957 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_pos_cot_net_spec_change_4w` | -0.0347 | **-0.01** | 0.9958 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_pos_cot_net_spec_change_1w` | -0.0076 | **-0.00** | 0.9980 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=5 | `feat_pos_cot_net_spec_level` | +0.0225 | **+0.00** | 0.9990 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_pos_cot_net_spec_change_4w` | -0.0092 | **-0.00** | 0.9993 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=6 | `feat_pos_cot_net_spec_level` | +0.0213 | **-0.00** | 0.9998 | ❌ NOT SIG | ❌ NOT SIG |
| D1 | H=1 | `feat_pos_cot_net_spec_level` | +0.0221 | **-0.00** | 0.9999 | ❌ NOT SIG | ❌ NOT SIG |
| H4 | H=1 | `feat_pos_cot_net_spec_level` | +0.0200 | **-0.00** | 1.0000 | ❌ NOT SIG | ❌ NOT SIG |


## 5. CONCLUSION ET VERDICT DU POSITIONNEMENT COT

**0 feature sur les 16 paires évaluées dans la famille CFTC COT 088691 ne franchit la correction pour tests multiples Benjamini-Hochberg FDR q=0.05**.
