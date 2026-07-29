# Architecture de la Couche d'Intelligence (AI Layer)

## 1. Principes Fondamentaux
L'intelligence du système ne réside pas dans la prédiction immédiate, mais dans la **réminiscence asymétrique**. Le LLM n'intervient pas dans la boucle critique d'exécution. Il est consulté hors ligne ou en asynchrone pour qualifier les expériences.

## 2. Composants de l'Architecture AI

### 2.1 Feature Extractor
Module chargé de transformer l'état brut du marché (prix, volume, carnet d'ordres) en un vecteur d'état normé.
*Features :* Volatilité (ATR), Spread, Tendance (MVA), RSI, Momentum, Profil de volume.

### 2.2 Embedding Engine
Transforme l'état du marché et le contexte en un vecteur mathématique dense.

### 2.3 Vector Database (FAISS)
Stockage ultra-rapide des expériences passées. Divisé en deux namespaces :
- **Success Memory** : Ce qui a fonctionné, sous quelles conditions.
- **Failure Memory** : Ce qui a tué le capital, sous quelles conditions.

### 2.4 Multi-Agent Advisory Council
Groupe d'agents spécialisés (implémentés via des classes distinctes ou des prompts LLM pré-calculés) qui analysent les situations top-200 remontées par la mémoire.
- L'agent d'exécution propose le trade.
- Le conseil évalue le trade face à l'histoire.
- Le Risk Manager (Algorithmique déterministe) applique son Veto si le profil correspond à 90% à un souvenir de la *Failure Memory*.

### 2.5 Feedback Loop (Apprentissage)
Une fois le trade exécuté et clôturé :
1. Calcul du PnL et des métriques de qualité d'exécution (Slippage, Drawdown max pendant le trade).
2. Création de l'objet `Experience`.
3. Génération de l'Embedding.
4. Injection dans FAISS.
