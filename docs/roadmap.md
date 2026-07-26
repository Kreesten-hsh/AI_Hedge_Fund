# Roadmap Aegis Trade

## Phase 0 — Vision, architecture, roadmap
Vision, architecture, roadmap. Aucune ligne de code.
**Critère de passage à la phase suivante :** les 3 documents (vision.md, architecture.md, roadmap.md) sont relus et validés par l'utilisateur humain.

## Phase 1 — Market Data
DataProvider abstrait, connecteur MT5 réel, récupération d'historique, nettoyage des données.
**Critère de passage à la phase suivante :** DataProvider retourne des données réelles vérifiables (pas de placeholder) pour au moins 3 symboles différents, couvrant au moins 6 mois d'historique.

## Phase 2 — Quant Lab
Implémentation des 3 baselines, backtester durci (coûts, slippage, marge réalistes), walk-forward validation.
**Critère de passage à la phase suivante :** les 3 baselines ont un résultat backtesté documenté (Sharpe, Sortino, Max Drawdown, Calmar, Profit Factor) sur au moins 2 périodes de marché différentes (ex. tendance et range).

## Phase 3 — Research Council en mode RAPPORT SEUL
Agents LLM alimentés par de vraies données (Phase 1). Aucune exécution possible.
**Critère de passage à la phase suivante :** sur un échantillon d'au moins 30 analyses, le consensus du Research Council bat au moins une des 3 baselines sur les métriques principales. Sinon, retour en Phase 2 pour retravailler le signal — pas de passage en Phase 4 par défaut.

## Phase 4 — Risk Engine + Portfolio Engine + Execution réelle
Compte démo MT5, capital 50$. Le Research Council obtient enfin la capacité de déclencher des trades, toujours sous contrôle du Risk Engine.
**Critère de passage à la phase suivante :** au moins 4 semaines de paper trading démo sans incident (aucun dépassement de limite de risque), avec un journal d'audit complet.

## Phase 5 — Learning Engine
Analyse de l'historique réel de trades produit en Phase 4.
**Critère de passage à la phase suivante :** au moins 50 trades réels en historique pour avoir une base statistique minimale.

## Phase 6 — Reflection Engine
Post-mortem quotidien automatisé.
**Critère de passage à la phase suivante :** Génération sans erreur de 5 rapports post-mortem quotidiens.

## Phase 7 — Strategy Generator
Propositions de variantes de stratégie par l'IA.
**Critère de passage à la phase suivante :** Les variantes proposées par l'IA sont validées avec succès par le Quant Lab (Phase 2).

## Phase 8 — Meta Agent
Toujours en dernier, note et arbitre les autres agents.
**Critère de passage à la phase suivante :** sur au moins 3 mois de fonctionnement en parallèle, le système avec Meta Agent actif égale ou dépasse le système sans Meta Agent sur les métriques principales (vision.md section 2), sans dégradation du max drawdown. Cette phase est la dernière : il n'y a pas de phase suivante, seulement une revue périodique.
