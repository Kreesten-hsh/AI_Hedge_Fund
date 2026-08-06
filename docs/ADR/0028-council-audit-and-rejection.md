# ADR 0028 — Audit Quantitatif et Rejet Scientifique du MultiAgentCouncil à Haute Fréquence (M1)

- **Statut** : REJETÉ (sur granularité M1)
- **Date** : 2026-08-06 (Version révisée avec audit comparatif côte-à-côte)
- **Contexte technique** : `src/aegis_trade/application/council/orchestrator.py`, `scripts/evaluate_council_performance.py`, `tests/application/council/test_veto_execution_liquidity.py`
- **Dépend de** : ADR 0018 (seuils dérivés du coût), ADR 0021 (coût mesuré A/R), ADR 0025 (rejet des indicateurs techniques usuels)
- **Résout** : Audit de la Priorité 1 du Backlog (Audit du Council à 8 agents)

## Contexte

Le `MultiAgentCouncil` déterministe orchestre 8 agents spécialisés (`TrendAgent`, `MomentumAgent`, `VolatilityAgent`, `LiquidityAgent`, `PatternAgent`, `NewsAgent`, `ExecutionAgent`, `PortfolioAgent`).

Jusqu'alors, ce système n'avait jamais été évalué sur l'historique M1 réel avec la même rigueur (P&L net d'allers-retours contre le péage réel) que les modèles univariés et LightGBM. Cet audit vise à mesurer si la combinaison et le consensus des agents parviennent à surmonter les coûts d'exécution (1.859 bps sur Gold, 0.745 bps sur Crash 1000).

---

## 1. Corrections Techniques, Veto & Bug Identification

1. **Correction du Veto Inopérant (`LiquidityAgent` & `ExecutionAgent`)** :
   - *Anomalie identifiée* : `VoteAggregator.aggregate()` n'accumulait que les votes `BUY` et `SELL`. Les votes `WAIT` émis par les agents de sécurité avec une haute confiance (ex: latence > 200 ms ou spread > 5.0) étaient ignorés et dilués.
   - *Fix appliqué* : `MultiAgentCouncil.evaluate()` a été corrigé pour intercepter les votes `WAIT` à confiance $\ge 0.8$ émis par `LiquidityAgent` ou `ExecutionAgent` et forcer un veto strict (`final_vote = "WAIT"`, `position_size_multiplier = 0.0`). Validé par les tests de non-régression dans `tests/application/council/test_veto_execution_liquidity.py`.

2. **Révélation du Bug `rsi`/`rsi_14` dans `MomentumAgent`** :
   - *Anomalie identifiée* : `TechnicalFeatureExtractor` produit la clé `rsi_14`. `MomentumAgent` lisait `context.features.get('rsi')` et recevait toujours `None`, le rendant silencieusement inactif (`WAIT`, conf 0.0) lors des premières versions d'évaluation.
   - *Fix appliqué* : `MomentumAgent` lit désormais `rsi_14` en fallback, réactivant 6 029 votes directionnels sur Gold et 36 076 sur Crash 1000.

3. **Dette d'Ingénierie & Duplication (Observation distincte)** :
   - La coexistence de deux modules de Council (`src/aegis_trade/agents/council.py` LLM vs `src/aegis_trade/application/council/orchestrator.py` déterministe) constitue une dette d'ingénierie et n'était pas la cause directe des pertes de P&L.
   - Cette duplication a été **résolue** en migrant tous les appelants du chemin de décision (`AiDecisionEngine`) vers `MultiAgentCouncil` et en documentant `src/aegis_trade/agents/council.py` comme composant legacy de reporting asynchrone hors path critique ([docs/LEGACY_COUNCIL_MIGRATION.md](file:///mnt/WindowsData/AI_Hedge_Fund/docs/LEGACY_COUNCIL_MIGRATION.md)).

---

## 2. Audit Quantitatif Comparatif Côte-à-Côte (75 000 barres M1)

Afin d'éviter tout artefact de simulation (tel qu'un proxy continu de momentum faisant passer un indicateur pour la mémoire vectorielle FAISS), l'évaluation a été conduite sous deux régimes distincts dans [scripts/evaluate_council_performance.py](file:///mnt/WindowsData/AI_Hedge_Fund/scripts/evaluate_council_performance.py) :

- **Run 1 (Purifié & Réel)** : Veto strict + `MomentumAgent` réactivé (`rsi_14`), avec `PatternAgent` neutre (`memory_score = 0.0`), reflétant la réalité de production d'une mémoire FAISS non peuplée sans sur-apprentissage.
- **Run 2 (Proxy FAISS Sparse)** : `memory_score` clairsemé (~5% des barres sur chocs > 3 std) + suivi dynamique du Portfolio pour observer la réactivité de `PortfolioAgent`.

### A. État d'Activité des 8 Agents

| Agent | Rôle | Run 1 (Purifié & Réel) | Run 2 (Proxy FAISS Sparse) |
|---|---|---|---|
| **TrendAgent** | Impulsion Trend (EMA50) | **ACTIF** (24 155 votes) | **ACTIF** (24 155 votes) |
| **MomentumAgent** | Impulsion Momentum (RSI14) | **ACTIF** (6 029 votes) | **ACTIF** (6 029 votes) |
| **VolatilityAgent** | Impulsion Mean-Reversion (Bollinger) | **ACTIF** (7 755 votes) | **ACTIF** (7 755 votes) |
| **PatternAgent** | Mémoire Vectorielle FAISS | **INACTIF / STUB** (0.0 par défaut) | **ACTIF (Proxy)** (518 votes) |
| **PortfolioAgent** | Rééquilibrage d'Exposition | **INACTIF / STUB** (0 pos) | **ACTIF (Proxy)** (31 200 votes) |
| **LiquidityAgent** | Veto Sécurité Spread | **PASSIF (Veto)** | **PASSIF (Veto)** |
| **ExecutionAgent** | Veto Sécurité Latence | **PASSIF (Veto)** | **PASSIF (Veto)** |
| **NewsAgent** | Macro LLM Asynchrone | **INACTIF / STUB** (Hors path) | **INACTIF / STUB** (Hors path) |

---

### B. Résultats P&L Net Côte-à-Côte (Horizon H5 = 5 minutes)

#### 1. Sur l'Or (`frxXAUUSD` M1, Coût A/R 1.859 bps)

| Métrique | Run 1 (Purifié & Réel) | Run 2 (Proxy FAISS Sparse) |
|---|---|---|
| **Taux d'Exposition / Trade** | **36.71 %** (27 530 trades) | **51.95 %** (38 964 trades) |
| **BUY Gross / Net** | +0.165 bps / **-1.694 bps** | +0.048 bps / **-1.811 bps** |
| **BUY Win Rate** | 49.59 % | 48.68 % |
| **SELL Gross / Net** | +0.152 bps / **-1.707 bps** | -0.018 bps / **-1.877 bps** |
| **SELL Win Rate** | 51.29 % | 50.41 % |

#### 2. Sur Crash 1000 (`CRASH1000` M1, Coût A/R 0.745 bps)

| Métrique | Run 1 (Purifié & Réel) | Run 2 (Proxy FAISS Sparse) |
|---|---|---|
| **Taux d'Exposition / Trade** | **54.36 %** (40 771 trades) | **61.06 %** (45 798 trades) |
| **BUY Gross / Net** | +0.047 bps / **-0.698 bps** | +0.086 bps / **-0.659 bps** |
| **SELL Gross / Net** | -0.081 bps / **-0.826 bps** | -0.079 bps / **-0.824 bps** |

---

## 3. Conclusion & Décision

1. **Invariance du Rejet** : Dans le Run 1 purifié (36.71% d'exposition) comme dans le Run 2 (51.95% d'exposition), le P&L net du `MultiAgentCouncil` sur M1 est **structurellement négatif** (entre -1.69 bps et -1.87 bps sur Gold, et -0.66 bps à -0.83 bps sur Crash).
2. **Explication par la Fréquence et l'Amplitude** : Les signaux d'entrée actifs (`TrendAgent`, `MomentumAgent`, `VolatilityAgent`) captent un mouvement moyen brut d'à peine `+0.16 bps`, soit **11 fois moins que le coût d'aller-retour réel de 1.859 bps**.
3. **Décision Finale** : Le `MultiAgentCouncil` Déterministe à Haute Fréquence (M1) est **REJETÉ**.
4. **Feuille de Route** : Clôture formelle de l'audit et passage à la Priorité 1 : **Pivot Fréquence & Régime d'Horizon (H4 / D1)**.
