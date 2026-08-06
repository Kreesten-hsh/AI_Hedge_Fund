# ADR 0027 — Évaluation de la Famille de Features Macroéconomiques (FRED DFII10, DXY) sur l'Or M1 : Rejet documenté à haute fréquence

- **Statut** : REJETÉ (à haute fréquence M1/M5)
- **Date** : 2026-08-06
- **Contexte technique** : `scripts/build_gold_macro_dataset.py`, `scripts/run_macro_feature_research.py`, `data/market_data/xauusd_macro.parquet`, `docs/measures/sig-02/features_gold_macro.json`
- **Dépend de** : ADR 0025 (rejet des features techniques simples), ADR 0026 (intégration FRED DFII10 via OpenBB)
- **Résout** : Étape 1 de la trajectoire GOLD-MACRO

## Contexte

Après l'invalidation des 25 indicateurs techniques usuels sur Gold M1 (ADR 0025), cette expérimentation avait pour objectif de tester une famille de variables fondamentales explicatives : le **Taux Réel 10 ans US (`DFII10` - TIPS)** et le **Dollar Index (`DXY`)**.

Un pipeline d'alignement temporel causal (sans look-ahead bias) a été construit ([scripts/build_gold_macro_dataset.py](file:///mnt/WindowsData/AI_Hedge_Fund/scripts/build_gold_macro_dataset.py)) pour associer les séries FRED aux 75 000 barres M1 de Gold.

---

## 1. Résultats de l'Alpha Research Macro

L'analyse de corrélation de rang Spearman ($n_{\text{eff}}$, $t$-stat corrigé de chevauchement sur split 70% train / 30% test) a été conduite sur les horizons $H \in [5, 10, 15, 30, 60, 120, 240]$ barres M1 :

| Feature Candidate | Horizon (min) | IC Train | IC Test | $t$-stat Test ($n_{\text{eff}}$) | Verdict Significativité ($|t| > 2.0$) |
|---|---|---|---|---|---|
| `feature_macro_dfii10_change_5d` | H120 (2h) | -0.0811 | -0.1409 | -1.93 ($n_{\text{eff}}=186$) | **NON SURVÉCU** |
| `feature_macro_dfii10_change_5d` | H240 (4h) | -0.0920 | -0.1816 | -1.75 ($n_{\text{eff}}=92$) | **NON SURVÉCU** |
| `feature_macro_dxy_change_1d` | H240 (4h) | +0.0015 | +0.1325 | +1.27 ($n_{\text{eff}}=92$) | **NON SURVÉCU** |
| `macro_dxy` | H120 (2h) | -0.0069 | -0.0853 | -1.16 ($n_{\text{eff}}=186$) | **NON SURVÉCU** |
| `macro_dfii10` | H120 (2h) | -0.0428 | +0.0179 | +0.24 ($n_{\text{eff}}=186$) | **NON SURVÉCU** |

**VERDICT GLOBAL** : **0 / 6 features macro ne franchit le seuil de significativité ($|t| > 2.0$)** sur les horizons intraday M1/M5.

---

## 2. Enseignements Scientifiques

1. **Incompatibilité de Fréquence** : Les séries macro FRED (`DFII10`) sont publiées à fréquence quotidienne. Diffusées sur des fenêtres glissantes M1 (5 min à 4 heures), elles ne contiennent pas de dynamique d'impulsion intraday suffisante pour prédire la direction barre à barre sur du M1.
2. **Confirmation de l'analyse** : L'échec des features macro à haute fréquence M1 confirme que le bruit microstructurel domine la variation minute par minute, et qu'un éventuel edge fondé sur les taux réels s'exprime sur des échelles de temps plus basses (H4 / Quotidien).

---

## 3. Transition vers la Priorité 2

Conformément à la feuille de route validée :
1. **Étape GOLD-MACRO M1** : Clôturée en **REJETÉ** (ADR 0027).
2. **Prochaine étape (Priorité 2)** : Audit scientifique rigoureux du **Council à 8 agents** (`domain/council.py`).
