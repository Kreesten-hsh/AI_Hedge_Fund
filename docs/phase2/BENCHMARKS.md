# Benchmarks et Objectifs Qualitatifs

Aegis Quant OS est évalué selon un ensemble strict de métriques quantitatives. Chaque nouvelle itération de l'IA (ou chaque nouveau modèle) **doit** battre la version précédente sur ces critères pour être déployée en production.

## 1. Métriques de Performance et Risque
- **Sharpe Ratio** : Objectif > 1.5
- **Sortino Ratio** : Objectif > 2.0 (Pénalisation de la volatilité négative uniquement)
- **Win Rate** : Objectif > 85% (Micro-scalping)
- **Average Win / Average Loss (Risk/Reward)** : Même si ce ratio est inférieur à 1 (typique en scalping), il doit être stable.
- **Max Drawdown** : Objectif < 5% (Tolérance zéro à la ruine)
- **Recovery Factor** : Temps nécessaire pour effacer un drawdown. Objectif < 48 heures.

## 2. Métriques Opérationnelles et Techniques
- **Latency (Tick-to-Trade)** : Temps d'exécution entre l'arrivée du tick, la recherche FAISS, et l'envoi de l'ordre. Objectif < 20 ms.
- **Trades/day** : Fréquence d'exécution (scalping modéré). Objectif : ~100 à 200 trades par jour pour garantir la consistance statistique sans forcer de gros leviers.
- **Slippage moyen** : Écart entre le prix théorique et le prix exécuté. Objectif < 0.5 pip.
- **Spread Cumulé (Coût de Transaction)** : Coût total payé en spread chaque jour. Doit rester strictement inférieur aux gains bruts sur la journée pour garantir la profitabilité nette.

## 3. Métriques Système (Observability)
- **CPU Usage** : Objectif < 60% d'utilisation sur la machine hôte.
- **RAM Usage** : Fuites mémoires interdites (Objectif < 4GB constants hors modèles ML isolés).
- **Vector DB Query Time** : Recherche des 200 situations similaires < 5 ms.
