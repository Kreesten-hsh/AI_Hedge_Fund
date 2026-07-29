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
- **Trades/hour** : Fréquence d'exécution (doit justifier une automatisation HFT).
- **Slippage moyen** : Écart entre le prix théorique et le prix exécuté. Objectif < 0.5 pip.

## 3. Métriques Système (Observability)
- **CPU Usage** : Objectif < 60% d'utilisation sur la machine hôte.
- **RAM Usage** : Fuites mémoires interdites (Objectif < 4GB constants hors modèles ML isolés).
- **Vector DB Query Time** : Recherche des 200 situations similaires < 5 ms.
