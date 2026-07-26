# ADR-001: Aegis as a Meta-Orchestrator

## 1. Contexte
Les architectures quantitatives traditionnelles (ex: Zipline) sont monolithiques : elles gèrent en interne l'ingestion de la donnée, la simulation des ordres, le calcul du P&L et la connectivité aux courtiers. Historiquement, ce monolithisme devient une dette technique fatale car il empêche l'intégration rapide de nouvelles briques IA (LLMs) ou de nouveaux courtiers sans casser le cœur.

## 2. Décision
**Aegis Quant OS est conçu exclusivement comme un Méta-Orchestrateur.**
Nous décidons de séparer strictement les préoccupations :
- Aegis ne gèrera jamais le routage réseau vers Binance ou IBKR.
- Aegis ne maintiendra jamais de parseurs de données Yahoo ou FRED.
- Aegis se concentre à 100% sur l'intelligence (Research Council, LLM prompts) et sur la gestion des risques (Decision/Portfolio Engine).

## 3. Justification
Cette décision protège le code propriétaire d'Aegis contre le "churn" technologique. En déléguant le "sale boulot" (ingestion, connectivité) à des standards industriels, notre code source reste pur, léger et ultra-focalisé sur la création d'Alpha.

## 4. Conséquences
- **Positif :** Réduction drastique de la dette technique. Capacité de changer de source de données ou de courtier en écrivant simplement un nouvel adaptateur.
- **Négatif :** L'architecture exige une grande rigueur dans le pattern Adaptateur (Architecture Hexagonale) pour ne pas polluer nos objets du domaine avec les types externes.
