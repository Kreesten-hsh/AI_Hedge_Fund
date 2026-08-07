# ADR 0030 — Audit Économétrique H4/D1, Cointégration & Clôture de la Recherche d'Alpha (TÂCHE 2)

- **Statut** : REJETÉ / CLÔTURÉ (0/204 Features Validées — Réfutation Complète des Indicateurs Techniques, Microstructure Spike, Artefact DXY I(1) et Positionnement CFTC COT 088691)
- **Date** : 2026-08-07
- **Contexte technique** : `scripts/run_h4_d1_feature_research.py`, `scripts/run_positioning_feature_research.py`, `docs/research/POSITIONING_FEATURE_RESEARCH_REPORT.md`
- **Dépend de** : ADR 0021 (péage 1.859 bps), ADR 0027 (Macro M1), ADR 0029 (Pivot H4/D1)
- **Résout** : Tâche 2 de la Roadmap — Recherche d'Alpha & Significativité Statistique sous Contrôle Rigoureux d'Intégration, Cointégration et Tests Multiples

---

## Contexte et Protocole Statistique

Dans le cadre de la Tâche 2, l'ensemble des pistes d'hypothèses sur Gold (`XAUUSD` Dukascopy 11.6 ans) et Synthétiques (`CRASH1000`, `BOOM1000` Deriv Natif H4) ont été évaluées de manière exhaustive sous contrôle statistique rigoureux :
1. **Contrôle des Tests Multiples** : **Benjamini-Hochberg (FDR $q = 0.05$)** et **Bonferroni ajusté** par famille d'hypothèses.
2. **Garde-Fou Économétrique ADR 0030** : Audit d'intégration **Augmented Dickey-Fuller (ADF)** et test de cointégration **Engle-Granger** sur chaque niveau brut avant évaluation, éliminant tout artefact de régression fallacieuse (*Spurious Regression*, Granger & Newbold 1974).
3. **Alignement Causal Stricte & Filtrage Exact CFTC** : Données COT filtrées sur le code de contrat exact **`CFTC Contract Market Code == '088691'`** (COMEX Gold 100 oz Standard). Positions arrêtées le mardi décalées de 6 jours calendaires (utilisables le Lundi suivant 00:00 UTC), éliminant tout lookahead bias.

---

## 1. Synthèse Globale Exhaustive des 204 Hypothèses Évaluées

| Famille d'Actifs & Features | Hypothèses Évaluées ($N$) | Brut ($|t| \ge 2.0$) | Post-Correction FDR BH ($q=0.05$) | Post-Audit Cointégration / ADF | Statut Final |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Gold Groupe A (Technique D1 & H4)** | 76 | 0 | 0 | **0** | ❌ **RÉFUTÉ** |
| **Gold Groupe B (Macro FRED D1 & H4)** | 52 | 8 | 2 (DXY Level) | **0 (Rejet Spurious $I(1)$)** | ❌ **RÉFUTÉ** |
| **Gold Groupe C (Positionnement COT 088691)** | 16 | 0 | 0 | **0 ($I(0)$ non significatif)** | ❌ **RÉFUTÉ** |
| **Synthétiques (Crash/Boom H4 Spike)** | 60 | 6 | 0 | **0 (Rejet FDR BH)** | ❌ **RÉFUTÉ** |
| **TOTAL ÉVALUÉ** | **204** | **14 (6.9%)** | **2 (1.0%)** | **0 / 204 (0.0%)** | ❌ **RÉFUTATION TOTALE** |

---

## 2. Analyse Approfondie par Famille d'Hypothèses

### A. Positionnement CFTC COT Exact (`088691` COMEX Gold)
- **CFTC COT (604 semaines uniques 2015-2026, 0 doublon)** :
  - `cot_net_spec_level` ($ADF = -3.13 < -2.86 \implies I(0)$ Stationnaire).
  - Spearman IC $\in [-0.043, +0.022]$, $t$-stats Newey-West HAC $\le 0.13$ ($p \ge 0.89$).
  - **Verdict** : **0 / 16 paires significatives**. Le positionnement des spéculateurs à 3 jours ouvrés de délai ne possède aucun pouvoir prédictif sur les retours Gold D1/H4.

### B. Documentation du Blocage Technique GLD ETF Physical Holdings
- **SPDR Official CSV URL** (`GLD_US_archive_EN.csv`) : Renvoie un document `%PDF-1.5` déguisé en `.csv`.
- **World Gold Council URL** (`ETF_Flows_...xlsx`) : Renvoie une page HTML `Access denied` (Cloudflare WAF anti-bot blocking).
- Conformément aux directives, aucun volume de trading n'a été utilisé comme substitut silencieux.

### C. Audit Econométrique DXY Level (`feat_macro_dxy_level`)
- **DXY Level D1 & H4** : $ADF = -2.68 > -2.86 \implies I(1)$ Non-Stationnaire.
- **Cointégration Engle-Granger vs Gold** : $ADF_{\text{résidus}} = -1.09 \gg -3.34 \implies$ ❌ **Non Cointégré**.
- **Verdict** : Le $t$-statistique $+3.72$ était un artefact pur de tendance non-stationnaire partagée (Granger-Newbold 1974). Réévalué à **0 signal**.

---

## 3. Décisions d'Architecture et Conclusion du Projet

1. **Clôture et Réfutation Intégrale de la Tâche 2 (0 / 204 Features Validées)** :
   - **0 alpha statistique** n'a été découvert sur l'ensemble de l'espace de recherche (HF M1, IF H4/D1, Technique, Macro FRED, Microstructure Spike et Positionnement CFTC COT 088691).
2. **Consolidation Scientifique des Rejets du Système Aegis Quant OS** :
   - **High-Frequency M1** : Réfuté par la microstructure et le péage d'exécution (ADR 0025, 0027, 0028).
   - **Intermediate-Frequency H4/D1** : Réfuté par l'absence de pouvoir prédictif post-correction des fausses découvertes et de stationnarité (ADR 0029, 0030).
