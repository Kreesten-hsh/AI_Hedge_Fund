# ADR 0030 — Audit Économétrique H4/D1 & Réfutation de la Régression Fallacieuse DXY (TÂCHE 2)

- **Statut** : REJETÉ / CLÔTURÉ (0/188 Features Validées — Réfutation Complète des Indicateurs Techniques, Microstructure Spike et Artefact DXY I(1))
- **Date** : 2026-08-07
- **Contexte technique** : `scripts/run_h4_d1_feature_research.py`, `scripts/diagnostics/audit_spurious_dxy_cointegration.py`, `docs/research/DXY_COINTEGRATION_AUDIT_REPORT.md`
- **Dépend de** : ADR 0021 (péage 1.859 bps), ADR 0027 (Macro M1), ADR 0029 (Pivot H4/D1)
- **Résout** : Tâche 2 de la Roadmap — Recherche d'Alpha & Significativité Statistique sous Contrôle Rigoureux d'Intégration et de Tests Multiples

---

## Contexte et Protocole Statistique

Dans le cadre du pivot d'horizon H4/D1 (ADR 0029), la Tâche 2 visait à évaluer la significativité statistique ($t$-statistique Newey-West HAC ajustée pour le chevauchement, Spearman IC) de **188 hypothèses indépendantes** sur Gold (`XAUUSD` Dukascopy 11.6 ans) et Synthétiques (`CRASH1000`, `BOOM1000` Deriv Natif H4).

Le protocole imposait :
1. Un contrôle des fausses découvertes via **Benjamini-Hochberg (FDR $q = 0.05$)** et **Bonferroni ($\alpha_{\text{bonf}} = 0.000266 \implies |t| \ge 3.65$)**.
2. Un audit d'intégration **Augmented Dickey-Fuller (ADF)** et de cointégration **Engle-Granger** sur les séries de niveau macro pour prévenir tout artefact de régression fallacieuse (*Spurious Regression*, Granger & Newbold 1974).

---

## 1. Audit Econométrique : La Fallacie du Niveau DXY (`feat_macro_dxy_level`)

Bien que la feature `feat_macro_dxy_level` ait initialement affiché une statistique $t = +3.72$ ($p = 0.0002$) sur Gold H4, l'audit économétrique spécialisé a révélé la signature exacte d'une **régression fallacieuse** :

1. **Test d'Intégration ADF** :
   - Gold Close D1 : $ADF = +0.70 > -2.86 \implies \mathbf{I(1) \text{ Non-Stationnaire}}$.
   - DXY Level D1 (`DTWEXBGS`) : $ADF = -2.68 > -2.86 \implies \mathbf{I(1) \text{ Non-Stationnaire}}$.
   - Gold Returns & DXY 1d Diff : $ADF = -24.34 \text{ et } -24.23 < -2.86 \implies \mathbf{I(0) \text{ Stationnaires}}$.
2. **Test de Cointégration d'Engle-Granger** :
   - D1 Résidus Spread : $ADF = -1.09 \gg -3.34$ (Seuil 5%) $\implies$ ❌ **AUCUNE COINTÉGRATION**.
   - H4 Résidus Spread : $ADF = -0.97 \gg -3.34$ (Seuil 5%) $\implies$ ❌ **AUCUNE COINTÉGRATION**.
3. **Comportement des Variations Stationnaires $I(0)$** :
   - Les variations de 1 jour (`dxy_change_1d`) et 5 jours (`dxy_change_5d`) affichent un $t$-statistique plat ($|t| < 2.0$, non significatif).

**Conclusion Économétrique** : Le $t$-statistique de $+3.72$ sur le niveau DXY n'était qu'un artefact du chevauchement de deux tendances non-stationnaires $I(1)$ indépendantes. Sans relation de cointégration, le niveau n'a aucun pouvoir prédictif. La feature est **définitivement rejetée**.

---

## 2. Synthèse Finale des 188 Hypothèses de la Tâche 2

| Famille d'Actifs & Features | Hypothèses Évaluées ($N$) | Brut ($|t| \ge 2.0$) | FDR BH ($q=0.05$) | Après Audit Cointégration | Statut Final |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Gold Groupe A (Technique D1 & H4)** | 76 | 0 | 0 | **0** | ❌ **RÉFUTÉ** |
| **Gold Groupe B (Macro FRED D1 & H4)** | 52 | 8 | 2 (DXY Level) | **0 (Rejet Spurious $I(1)$)** | ❌ **RÉFUTÉ** |
| **Synthétiques (Crash/Boom H4 Spike)** | 60 | 6 | 0 | **0 (Rejet FDR BH)** | ❌ **RÉFUTÉ** |
| **TOTAL ÉVALUÉ** | **188** | **14 (7.4%)** | **2 (1.1%)** | **0 / 188 (0.0%)** | ❌ **RÉFUTATION TOTALE** |

---

## 3. Décisions d'Architecture Scellées

1. **Fermeture Définitive de la Tâche 2 (0/188 Features Validées)** :
   - Aucune des 188 caractéristiques évaluées (Technique, Macro FRED, Microstructure Spike) n'a démontré de pouvoir prédictif réel et résistant aux tests d'intégration et de correction pour tests multiples.
2. **Consignation du Garde-Fou Économétrique** :
   - Interdiction formelle d'évaluer ou d'inclure des caractéristiques en niveau brut $I(1)$ sans test de stationnarité (ADF) et de cointégration préalable (Engle-Granger).
3. **Consolidations des Rejets du Projet** :
   - M1 Haute Fréquence (Technique, Macro, Council) : RÉFUTÉ (ADR 0025, 0027, 0028).
   - H4/D1 Pivot Fréquence (Technique, Microstructure, Macro Niveaux) : RÉFUTÉ (ADR 0030).
