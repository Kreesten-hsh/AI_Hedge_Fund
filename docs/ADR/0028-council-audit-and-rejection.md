# ADR 0028 — Audit Scientifique du Council Multi-Agents : Rejet documenté du Council Déterministe à Haute Fréquence (M1)

- **Statut** : REJETÉ (sur granularité M1)
- **Date** : 2026-08-06
- **Contexte technique** : `src/aegis_trade/domain/council.py`, `src/aegis_trade/application/council/orchestrator.py`, `src/aegis_trade/application/council/agents/*.py`, `scratch/evaluate_council_performance.py`
- **Dépend de** : ADR 0018 (seuils dérivés du coût), ADR 0021 (coût mesuré A/R), ADR 0025 (rejet des indicateurs techniques usuels)
- **Résout** : Audit de la Priorité 1 du Backlog (Audit du Council à 8 agents)

## Contexte

Le Council multi-agents déterministe (`MultiAgentCouncil`) orchestre 8 agents spécialisés (`TrendAgent`, `MomentumAgent`, `VolatilityAgent`, `LiquidityAgent`, `PatternAgent`, `NewsAgent`, `ExecutionAgent`, `PortfolioAgent`).

Jusqu'alors, ce système n'avait jamais été évalué sur l'historique M1 réel avec la même rigueur (P&L net d'allers-retours contre le péage réel) que les modèles univariés et LightGBM. L'objectif de cet audit est de mesurer si la combinaison et le consensus des 8 agents parviennent à surmonter les coûts d'exécution (1.859 bps sur Gold, 0.745 bps sur Crash 1000).

---

## 1. Résultats de l'Audit Quantitatif (75 000 barres M1 sur Gold & Crash 1000)

L'évaluation séquentielle barre par barre du `MultiAgentCouncil` a été exécutée sur l'ensemble de l'historique M1 :

### A. Performance sur l'Or (`frxXAUUSD` M1, Coût A/R 1.859 bps)

- **Distribution des Verdicts** :
  - **BUY** : 13 516 trades (18.02 %)
  - **SELL** : 13 858 trades (18.48 %)
  - **WAIT** : 47 626 barres (63.50 %)
- **Performance P&L à 5 minutes (H5)** :
  - **Signaux BUY** : Rendement moyen BRUT = `+0.171 bps` | Rendement moyen NET = **`-1.688 bps`** | Win Rate = 49.14 %
  - **Signaux SELL** : Rendement moyen BRUT = `+0.155 bps` | Rendement moyen NET = **`-1.704 bps`** | Win Rate = 50.81 %

### B. Performance sur Crash 1000 (`CRASH1000` M1, Coût A/R 0.745 bps)

- **Distribution des Verdicts** :
  - **BUY** : 15 849 trades (21.13 %)
  - **SELL** : 9 756 trades (13.01 %)
  - **WAIT** : 49 395 barres (65.86 %)
- **Performance P&L à 5 minutes (H5)** :
  - **Signaux BUY** : Rendement moyen BRUT = `+0.144 bps` | Rendement moyen NET = **`-0.601 bps`**
  - **Signaux SELL** : Rendement moyen BRUT = `-0.072 bps` | Rendement moyen NET = **`-0.817 bps`**

---

## 2. Analyse des Causes d'Échec

1. **Dépendance aux Indicateurs Réfutés** : Les 3 seuls agents qui génèrent des signaux d'entrée actifs (`TrendAgent` via EMA50, `MomentumAgent` via RSI14, `VolatilityAgent` via Bollinger) réutilisent les règles techniques usuelles réfutées en ADR 0025.
2. **Sur-fréquence et Friction destructrice** : Le Council déclenche un trade sur plus de 36 % des barres M1 (> 27 000 trades). Le mouvement moyen capté par trade ($\approx +0.15$ bps) est **11 fois inférieur au coût d'aller-retour** sur Gold (1.859 bps).
3. **Duplication de l'Architecture** : L'audit confirme la coexistence de deux modules de Council dans le codebase (`src/aegis_trade/agents/council.py` basé sur LLM et `src/aegis_trade/application/council/orchestrator.py` déterministe).

---

## 3. Décision Finale

- **Le Council Déterministe à Haute Fréquence (M1) est REJETÉ**.
- Aucune exécution du Council déterministe ne sera déployée sur des granularités M1/M5 sans révision fondamentale de la famille de signaux d'entrée.
- **Passage à la Priorité 2 du Backlog** : Évaluation du changement de régime de fréquence vers des échelles de temps plus basses (**H4 / D1**) privilégiant des signaux à forte conviction et faible fréquence de rotation.
