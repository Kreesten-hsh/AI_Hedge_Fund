# ADR-002: Institutional Open-Source Integration & Zero API Cost

## 1. Contexte
Le développement d'un hedge fund IA nécessite des outils de pointe (modélisation de risque, backtest ML, gestion des événements de marché). Réécrire ces briques depuis zéro prendrait des mois et introduirait des bugs fatals. En parallèle, l'utilisation de services IA managés (OpenAI) viole la contrainte budgétaire du projet (Zéro coût d'API) et pose des risques de souveraineté/confidentialité.

## 2. Décision
**Nous adoptons massivement l'Open Source de grade institutionnel, hébergé localement.**
- Les briques complexes (Qlib pour le ML, vn.py pour le routage) sont adoptées en tant qu'infrastructures.
- L'intelligence artificielle s'appuie sur des modèles locaux (Llama 3, FinGPT) via Ollama, sans aucun appel externe.

## 3. Justification
D'un point de vue quantitatif, la valeur d'un hedge fund n'est pas dans le "tuyau" qui passe les ordres (vn.py fait cela mieux que quiconque), mais dans les signaux et la gestion des risques.
D'un point de vue économique, la contrainte "Zero API Cost" garantit la pérennité du projet, force la frugalité et protège les stratégies (pas d'envoi de données au cloud).

## 4. Conséquences
- **Positif :** Focus immédiat sur l'Alpha. Coût d'infrastructure nul. Souveraineté totale sur les données et la prise de décision.
- **Négatif :** Nécessite une machine de recherche robuste en local pour faire tourner les modèles de langage et les bases de données (Parquet, Qlib).
