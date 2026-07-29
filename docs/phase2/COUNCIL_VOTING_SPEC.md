# Multi-Agent Council - Voting Specification

Ce document décrit la mathématique d'agrégation et de résolution des conflits pour l'AI-05.

## 1. VoteAggregator

L'agrégation des votes utilise les poids déterminés par le module RL (`PolicyDecision.agent_weights`). 
Sans politique RL, les poids sont uniformes : $W_i = \frac{1}{N}$ avec $N = 8$.

Pour chaque vote reçu (BUY, SELL, WAIT) :
$Score_{BUY} = \sum_{i=1}^{N} (Confidence_{i} \times W_{i}) \quad \text{si } Vote_{i} = BUY$
$Score_{SELL} = \sum_{i=1}^{N} (Confidence_{i} \times W_{i}) \quad \text{si } Vote_{i} = SELL$

Le vainqueur est la direction avec le plus grand score. 

## 2. ConflictResolver

Le désaccord est modélisé par le ratio entre la force minoritaire et la force majoritaire :
$Disagreement = \frac{\min(Score_{BUY}, Score_{SELL})}{\max(Score_{BUY}, Score_{SELL})}$

- Si $Disagreement \geq 0.95$ : Abandon du trade (Incertitude critique).
- Si $Disagreement \geq 0.80$ : Réduction de la taille de position (Multiplier = 0.25).
- Sinon : Taille standard (Multiplier = 1.0).

## 3. RL Policy Application

Le module RL (AI-04) influence le conseil via deux paramètres supplémentaires :
1. `risk_multiplier` : S'applique au multiplicateur de taille final.
2. `confidence_threshold_adjustment` : Décale le seuil de confiance minimum (Base: 0.5) pour bloquer des trades en période d'incertitude macro.
Si $\max(Score_{BUY}, Score_{SELL}) < (0.5 + adjustment)$, le trade est annulé.

## 4. Latency Budget Guard

Un budget strict de latence est imposé (par défaut 20 ms pour l'évaluation complète CPU-only du conseil). Si l'évaluation dépasse ce budget, un warning d'audit est levé pour éviter que le pipeline HFT ne soit bloqué.
