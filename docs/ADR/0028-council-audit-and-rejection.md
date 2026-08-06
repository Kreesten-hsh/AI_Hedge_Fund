# ADR 0028 — Audit Quantitatif et Rejet Scientifique du MultiAgentCouncil à Haute Fréquence (M1)

- **Statut** : REJETÉ (sur granularité M1)
- **Date** : 2026-08-06 (Amendé suite à l'audit dynamique à 5 agents actifs)
- **Contexte technique** : `src/aegis_trade/application/council/orchestrator.py`, `scripts/evaluate_council_performance.py`, `tests/application/council/test_veto_execution_liquidity.py`
- **Dépend de** : ADR 0018 (seuils dérivés du coût), ADR 0021 (coût mesuré A/R), ADR 0025 (rejet des indicateurs techniques usuels)
- **Résout** : Audit de la Priorité 1 du Backlog (Audit du Council à 8 agents)

## Contexte

Le `MultiAgentCouncil` déterministe orchestre 8 agents spécialisés (`TrendAgent`, `MomentumAgent`, `VolatilityAgent`, `LiquidityAgent`, `PatternAgent`, `NewsAgent`, `ExecutionAgent`, `PortfolioAgent`).

Jusqu'alors, ce système n'avait jamais été évalué sur l'historique M1 réel avec la même rigueur (P&L net d'allers-retours contre le péage réel) que les modèles univariés et LightGBM. Cet audit vise à mesurer si la combinaison et le consensus des agents parviennent à surmonter les coûts d'exécution (1.859 bps sur Gold, 0.745 bps sur Crash 1000).

---

## 1. Corrections d'Architecture et de Veto (Tâches 1 & 2)

1. **Correction du Veto Inopérant (`LiquidityAgent` & `ExecutionAgent`)** :
   - *Anomalie identifiée* : `VoteAggregator.aggregate()` n'accumulait que les votes `BUY` et `SELL`. Les votes `WAIT` émis par les agents de sécurité avec une haute confiance (ex: latence > 200 ms ou spread > 5.0) étaient ignorés et dilués.
   - *Fix appliqué* : `MultiAgentCouncil.evaluate()` a été corrigé pour intercepter les votes `WAIT` à confiance $\ge 0.8$ émis par `LiquidityAgent` ou `ExecutionAgent` et forcer un veto strict (`final_vote = "WAIT"`, `position_size_multiplier = 0.0`). Validé par les tests de non-régression dans `tests/application/council/test_veto_execution_liquidity.py`.

2. **Dette d'Ingénierie & Duplication (Observation distincte)** :
   - La coexistence de deux modules de Council (`src/aegis_trade/agents/council.py` LLM vs `src/aegis_trade/application/council/orchestrator.py` déterministe) constitue une dette d'ingénierie et n'était pas la cause directe des pertes de P&L.
   - Cette duplication a été **résolue** en migrant tous les appelants du chemin de décision (`AiDecisionEngine`) vers `MultiAgentCouncil` et en documentant `src/aegis_trade/agents/council.py` comme composant legacy de reporting asynchrone hors path critique ([docs/LEGACY_COUNCIL_MIGRATION.md](file:///mnt/WindowsData/AI_Hedge_Fund/docs/LEGACY_COUNCIL_MIGRATION.md)).

---

## 2. Résultats de l'Audit Quantitatif Dynamique (5 Agents Actifs sur 8)

Un harnais d'audit dynamique ([scripts/evaluate_council_performance.py](file:///mnt/WindowsData/AI_Hedge_Fund/scripts/evaluate_council_performance.py)) a été conçu pour exercer la totalité du spectre d'agents opérationnels sur 75 000 barres M1 en simulant :
- Une mémoire FAISS dynamique pour alimenter `PatternAgent`.
- Le suivi des positions et de l'équité dans le `Portfolio` pour déclencher les votes de rééquilibrage de `PortfolioAgent`.

### A. État d'Activité des 8 Agents

| Agent | Rôle | Statut dans l'Audit | Votes Directionnels (BUY/SELL) |
|---|---|---|---|
| **TrendAgent** | Impulsion Trend (EMA50) | **ACTIF** | 24 155 (Gold) / 24 494 (Crash) |
| **MomentumAgent** | Impulsion Momentum (RSI14) | **ACTIF** | 6 029 (Gold) / 36 076 (Crash) |
| **VolatilityAgent** | Impulsion Mean-Reversion (Bollinger) | **ACTIF** | 7 755 (Gold) / 3 736 (Crash) |
| **PatternAgent** | Mémoire Vectorielle FAISS | **ACTIF** | 74 871 (Gold) / 74 993 (Crash) |
| **PortfolioAgent** | Rééquilibrage d'Exposition | **ACTIF** | 59 756 (Gold) / 56 804 (Crash) |
| **LiquidityAgent** | Veto Sécurité Spread | **PASSIF (Veto)** | 0 (Intervient uniquement en veto) |
| **ExecutionAgent** | Veto Sécurité Latence | **PASSIF (Veto)** | 0 (Intervient uniquement en veto) |
| **NewsAgent** | Macro LLM Asynchrone | **INACTIF / STUB** | 0 (Stub LLM hors path critique) |

**Bilan d'Activité** : **5 / 8 agents ont émis des votes directionnels actifs** (les 3 agents de filtres/vetos/stubs restant neutres par design).

---

### B. Performance Économique et P&L Net (H5 = 5 minutes)

#### 1. Sur l'Or (`frxXAUUSD` M1, Coût A/R 1.859 bps)
- **Distribution des Verdicts** : BUY = 48.87 % | SELL = 48.86 % | WAIT/VETOS = 2.26 %
- **Signaux BUY (n=36 655)** : Rendement moyen BRUT = `-0.054 bps` | Rendement moyen NET = **`-1.913 bps`** | Win Rate = 48.49 %
- **Signaux SELL (n=36 644)** : Rendement moyen BRUT = `+0.023 bps` | Rendement moyen NET = **`-1.836 bps`** | Win Rate = 50.76 %

#### 2. Sur Crash 1000 (`CRASH1000` M1, Coût A/R 0.745 bps)
- **Distribution des Verdicts** : BUY = 34.08 % | SELL = 58.53 % | WAIT/VETOS = 7.40 %
- **Signaux BUY (n=25 557)** : Rendement moyen BRUT = `-0.085 bps` | Rendement moyen NET = **`-0.830 bps`** | Win Rate = 77.52 %
- **Signaux SELL (n=43 889)** : Rendement moyen BRUT = `+0.013 bps` | Rendement moyen NET = **`-0.732 bps`** | Win Rate = 21.65 %

---

## 3. Décision Finale

- **Le `MultiAgentCouncil` Déterministe à Haute Fréquence (M1) est REJETÉ**.
- Malgré la mise en place du veto strict et l'activation des 5 agents de stratégie (Trend, Momentum, Volatility, Pattern, Portfolio), le consensus génère un volume d'allers-retours massif (~97 % du temps) à rendement brut nul ($\approx 0.00$ bps), se traduisant par un P&L net négatif égal aux frais de transaction.
- **Passage à la Priorité 1 du Backlog** : Évaluation du changement de régime de fréquence vers des échelles de temps plus basses (**H4 / D1**) privilégiant des signaux à forte conviction et faible fréquence de rotation.
