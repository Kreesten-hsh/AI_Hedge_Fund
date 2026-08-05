# ADR 0025 — Coût de transaction et Tradabilité de l'Or (frxXAUUSD) : Rejet documenté de GOLD-01

- **Statut** : REJETÉ
- **Date** : 2026-08-05
- **Contexte technique** : `scripts/measure_deriv_live_round_trip.py`, `scripts/run_feature_research.py`, `data/market_data/xauusd.parquet`
- **Dépend de** : ADR 0018 (seuils dérivés du coût), ADR 0021 (protocole de mesure de coût), ADR 0024 (rejet SIG-02 et feature research)
- **Résout** : Prérequis 2 et Gate de tradabilité de GOLD-01

## Contexte

GOLD-01 vise à évaluer la tradabilité du CFD Or (`frxXAUUSD`) sur Deriv à la granularité M1. Conforme à la discipline de validation d'Aegis Quant OS et aux leçons des ADR 0018 à 0024 :
1. **Le coût réel doit être mesuré sur compte live/démo** avant tout entraînement de modèle, et ne peut pas être hérité des synthétiques (ADR 0021).
2. **Le gate de tradabilité et de puissance prédictive des features doit précéder tout modèle ML** (ADR 0024) : sans signal mesuré supérieur au coût de transaction, l'entraînement est une espérance négative garantie par construction.

## 1. Mesure du Coût de Transaction (Compte Démo Deriv `DOT93925868`)

Cinq allers-retours automatisés Multipliers (`frxXAUUSD`, stake $10, multiplicateur x100, détention 5s) ont été exécutés sur le canal authentifié PAT + OTP Deriv dès la réouverture de session du marché (22:10 UTC). 

### Résultats mesurés (médianes sur 5 allers-retours)

| Métrique | Valeur mesurée (frxXAUUSD) | Comparaison Crash 1000 | Comparaison Boom 1000 |
|---|---|---|---|
| **Péage d'exécution (commission)** | **1.859 bps** (0.01859 %) | 0.745 bps (2.5x) | 1.063 bps (1.8x) |
| **Slippage / Spread moyen** | **-0.047 bps** | N/A (prix unique) | N/A (prix unique) |
| **Coût Tout Compris (médiane)** | **1.818 bps** (0.0001818) | 0.745 bps (2.4x) | 1.063 bps (1.7x) |

**Constat** : Le coût aller-retour sur Gold est nettement plus élevé que sur les indices synthétiques. Le seuil de rentabilité minimal (`breakeven_return`) pour une position sur Gold est de **1.818 bps** (0.0001818 par A/R).

---

## 2. Recherche de Features & Pouvoir Prédictif (75 000 barres M1)

L'analyse de corrélation d'information (IC Spearman et t-stat avec correction de chevauchement $n_{\text{eff}}$) a été exécutée sur l'historique M1 complet (75 000 barres, split chronologique 70 % train / 30 % test) :

- **Horizon 5 barres** : **0 / 25 features survivent**. Aucune feature ne franchit le seuil de significativité ($|t| > 2.0$, $|t|$ max = 1.87 sur le niveau `typical_price`).
- **Horizon 10 barres** : **0 feature d'oscillateur ou de rendement ne survit** ($|t| < 0.47$ pour `log_return` et `rsi`). 6 niveaux de prix bruts (`typical_price`, `median_price`, `ema_10`, `ema_20`, `bb_middle`, `bb_lower`) franchissent marginalement $|t| \approx 2.04 - 2.11$ sur le test, mais cette Corrélation est un pur artefact de tendance/dérive du sous-jacent sur 77 jours, sans puissance prédictive de rendement et sans correction pour tests multiples.

---

## 3. Décision du Gate de Tradabilité

- **Coût A/R mesuré** : 1.818 bps.
- **Signal d'alpha exploitable** : 0.00 bps (non distinguable du bruit).
- **Verdict du Gate** : **GOLD-01 est REJETÉ**.

Conformément à la règle permanente d'Aegis Quant OS :
*« Ne PAS enchaîner sur FE-01 / entraînement si le gate rejette l'instrument. Un rejet propre avec preuve reproductible est un succès au même titre qu'un GO. »*

L'hypothèse GOLD-01 sur M1 est clôturée en statut **REJETÉ**. Aucun modèle ML ne sera entraîné sur Gold dans les conditions actuelles.
