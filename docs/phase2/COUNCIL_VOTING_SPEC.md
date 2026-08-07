# Multi-Agent Council - Voting Specification

Ce document décrit la mathématique d'agrégation, la résolution des conflits et les droits de veto de l'AI-05.

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

Un budget strict de latence est imposé (par défaut 20 ms pour l'évaluation complète CPU-only du conseil). Si l'évaluation dépasse ce budget, un warning d'audit est levé pour éviter que le pipeline de décision ne soit bloqué.

## 5. Mécanisme de Veto d'Exécution et de Liquidité (ADR 0028)

Afin d'éviter tout trade non rentable sur des signaux valides mais pénalisés par le spread et le coût de transaction, le conseil intègre un droit de veto absolu :
- **Agent Liquidity / Execution** : Si le mouvement moyen prédit à l'horizon $H$ est inférieur au péage de transaction amorti ($Péage = 1.859\text{ bps}$ sur Deriv / $11.6\text{ bps}$ sur Gold), l'agent émet un veto impératif `VETO_EXECUTION`.
- **Règle d'Absolutisme** : Le veto de l'Agent Liquidity court-circuite le score d'agrégation $Score_{BUY}/Score_{SELL}$ et annule immédiatement l'ordre, quel que soit l'accord des autres membres du Conseil.
