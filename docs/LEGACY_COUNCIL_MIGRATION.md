# Migration et Clarification des Moteurs de Council

- **Date** : 2026-08-06
- **Statut** : MIGRATION COMPLÉTÉE
- **Contexte** : Levée de l'ambiguïté de coexistence des deux moteurs de Council.

---

## 1. Moteur Déterministe Officiel (Chemin Critique & Backtest)

- **Emplacement** : `src/aegis_trade/application/council/orchestrator.py` (`MultiAgentCouncil`)
- **Agents** : 8 agents déterministes dans `src/aegis_trade/application/council/agents/*.py`.
- **Statut** : C'est le **seul et unique moteur de décision** utilisé dans le chemin de décision réel :
  - Invoqué par `AiDecisionEngine` (`src/aegis_trade/engine/ai_decision_engine.py`).
  - Invoqué par le Paper Trading Orchestrator (`src/aegis_trade/application/paper_trading/orchestrator.py`).

---

## 2. Moteur Legacy LLM (Reporting Asynchrone Hors Path Critique)

- **Emplacement** : `src/aegis_trade/agents/council.py` (`CouncilOrchestrator`)
- **Statut** : Module legacy d'analyse fondamentale textuelle via LLM.
- **Règle de Gouvernance** :
  - **Aucun import** dans `src/` n'est autorisé depuis `aegis_trade.agents.council`.
  - Réservé exclusivement à de la génération de rapports de synthèse hors-ligne ou asynchrones sans aucun impact sur le pass-through des ordres et du moteur de risque.
