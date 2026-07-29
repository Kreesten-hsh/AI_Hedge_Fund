# Engineering Rules (Constitution Technique)

> Ces règles sont **absolues** et non négociables. Elles évitent la dérive architecturale d'Aegis Quant OS à mesure de sa croissance.

## Règle 1 : Isolement du Domaine (Clean Architecture)
**Aucun accès direct au Broker depuis le Domain.**
Toutes les interactions avec le marché passent par la couche Infrastructure via des Interfaces (Ports). Le Domain ne connaît pas `vn.py`, il connaît `ILiveBroker`.

## Règle 2 : Sécurisation du Chemin Critique
**Aucun LLM dans le chemin critique d'exécution.**
La décision de prendre un trade temps réel doit être millisecondée et déterministe (Vector Search FAISS, calculs statistiques). Les LLM (comme FinGPT) opèrent **asynchrone** pour l'analyse post-trade, ou en parallèle pour les news.

## Règle 3 : Justification des Dépendances
**Toute nouvelle dépendance doit être justifiée.**
Avant de faire un `pip install` ou de modifier le `pyproject.toml`, l'avantage comparatif doit être documenté dans le `GITHUB_INTEGRATION_GUIDE.md`. La question *"Pourquoi ne pas le réécrire nous-mêmes ?"* doit avoir une réponse solide.

## Règle 4 : Validation par les Tests
**Toute stratégie doit avoir des tests.**
Un agent, un extracteur de features, ou un modèle RL ne passe jamais en production sans une suite de tests unitaires couvrant les *edge cases*.

## Règle 5 : Documentation Driven Development
**Toute mission doit mettre à jour la documentation.**
L'architecture, les spécifications, et le logbook doivent être mis à jour *avant* le code. Le code est la traduction de la documentation, et non l'inverse.

## Règle 6 : Traçabilité des Décisions
**Toute décision doit être traçable.**
Le journal des logs JSON, la base vectorielle d'expériences, et le *Research Logbook* garantissent que l'on puisse expliquer mathématiquement pourquoi Aegis a pris une position à une milliseconde donnée.
