# ADR 0025 — Coût de transaction, Gate de Tradabilité et Alpha Research de l'Or (frxXAUUSD) : Rejet documenté de GOLD-01

- **Statut** : REJETÉ
- **Date** : 2026-08-05
- **Contexte technique** : `src/aegis_trade/domain/tradability.py`, `scripts/measure_deriv_live_round_trip.py`, `scripts/run_feature_research.py`, `data/market_data/xauusd.parquet`
- **Dépend de** : ADR 0018 (seuils dérivés du coût), ADR 0019 (hypothèse 1-barre réfutée), ADR 0021 (protocole de mesure de coût), ADR 0024 (rejet SIG-02 et feature research)
- **Résout** : Prérequis 2 et Gate de tradabilité de GOLD-01

## Contexte

GOLD-01 vise à évaluer la tradabilité du CFD Or (`frxXAUUSD`) sur Deriv à la granularité M1. Conforme à la discipline de validation d'Aegis Quant OS et aux leçons des ADR 0018 à 0024 :
1. **Le coût réel doit être mesuré sur compte live/démo** avant tout entraînement de modèle, et ne peut pas être hérité des synthétiques (ADR 0021).
2. **Le vrai gate de tradabilité économique (`domain/tradability.py`)** doit évaluer le budget aller-retour finançable (`max_viable_round_trip_cost`, `tradable_window_ratio`) sur une gamme d'horizons avant d'analyser la puissance prédictive des features (`run_feature_research.py`).

---

## 1. Mesure du Coût de Transaction (Compte Démo Deriv `DOT93925868`)

Cinq allers-retours automatisés Multipliers (`frxXAUUSD`, stake $10, multiplicateur x100, détention 5s) ont été exécutés sur le canal authentifié PAT + OTP Deriv à la réouverture de session du marché (22:10 UTC).

### Résultats mesurés (médianes sur 5 allers-retours)

| Métrique | Valeur mesurée (frxXAUUSD) | Comparaison Crash 1000 | Comparaison Boom 1000 |
|---|---|---|---|
| **Péage d'exécution (commission)** | **1.859 bps** (0.01859 %) | 0.745 bps (2.5x) | 1.063 bps (1.8x) |
| **Slippage / Spread moyen** | **-0.047 bps** | N/A (prix unique) | N/A (prix unique) |
| **Coût Tout Compris (médiane)** | **1.859 bps** (0.0001859) | 0.745 bps (2.5x) | 1.063 bps (1.8x) |

**Constat** : Le coût aller-retour sur Gold est de **1.859 bps** (0.0001859 par A/R).

---

## 2. Évaluation du Vrai Gate de Tradabilité (`domain/tradability.py`)

Les fonctions du domaine pur `domain/tradability.py` (`max_viable_round_trip_cost`, `tradable_window_ratio`, `is_horizon_tradable`) ont été exécutées sur l'ensemble de l'historique M1 Gold (75 000 barres, 2026-05-20 à 2026-08-05) pour une gamme d'horizons glissants $H \in [1, 5, 10, 15, 30, 60, 120, 240]$ barres :

| Horizon (M1) | Max Viable Cost @ 50% ratio | Ratio de fenêtres tradables @ 1.859 bps | Verdict Gate Tradabilité (`min_ratio=50%`) |
|---|---|---|---|
| **H1** | 1.849 bps | 49.82 % | **FAUX** (Réfuté à 1 min) |
| **H5** | 4.256 bps | 75.61 % | **VRAI** |
| **H10** | 6.018 bps | 82.64 % | **VRAI** |
| **H15** | 7.365 bps | 85.80 % | **VRAI** |
| **H30** | 10.451 bps | 89.97 % | **VRAI** |
| **H60** | 14.774 bps | 92.50 % | **VRAI** |
| **H120** | 22.309 bps | 95.34 % | **VRAI** |

**Enseignement du Gate de Tradabilité** :
Contrairement à la conjecture initiale, **l'obstacle sur Gold n'est pas une amplitude insuffisante de mouvement**. L'Or M1 présente une volatilité et un parcours suffisants pour que 75.6 % à 95.3 % des fenêtres de 5 à 120 barres couvrent largement le coût aller-retour de 1.859 bps. **Le Gate de Tradabilité est donc PASSÉ avec succès à partir de H5**.

---

## 3. Recherche de Features & Alpha Research (FE-01) sur les Horizons Économiquement Tradables

La suite `run_feature_research.py` (IC Spearman avec correction $n_{\text{eff}}$ et split 70% train / 30% test) a été exécutée sur la plage des horizons tradables ($H \in [5, 10, 15, 30, 60, 120]$) :

- **Oscillateurs & Indicateurs de Momentum/Rendement** (`rsi_14`, `macd`, `macd_hist`, `return_1d`, `log_return`, `return_5d`, `return_10d`, `ema_distance`) :
  - **0 / 25 features de rendement/oscillateur ne franchit le seuil $|t| > 2.0$** sur le test, quel que soit l'horizon ($H=5: |t| \le 1.31$, $H=10: |t| \le 0.47$, $H=15: |t| \le 0.33$, $H=30: |t| \le 0.14$, $H=60: |t| \le 0.41$, $H=120: |t| \le 0.35$).
- **Features de niveau bruts non stationnaires** (`typical_price`, `median_price`, `ema_10`, `bb_lower`) :
  - Affichent des $|t| \approx 2.0 - 2.11$ purement imputables à la dérive séculaire du cours de l'Or sur 77 jours, sans puissance prédictive d'alpha ou de rendement.

---

## 4. Synthèse et Décision Finale

1. **Le Gate de Tradabilité est PASSÉ** : L'instrument Gold possède le budget d'amplitude nécessaire pour absorber ses 1.859 bps de frais dès l'horizon 5 minutes.
2. **La Recherche de Features est ÉCHUÉE** : L'ensemble des 25 features techniques de base ne contient aucun signal d'alpha exploitable sur Gold M1.

**VERDICT FINALE** : **GOLD-01 est REJETÉ**.

Aucun modèle ML ne sera entraîné avec le set de features actuel. Tout développement ultérieur sur Gold exigera de nouvelles familles de features (ex: order flow, volatilité micro-structurelle, spread de corrélations).
