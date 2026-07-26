# ADR 0014: Paper Trading Before Live

## Status
Accepted

## Context
Le déploiement en argent réel (Live Trading) d'algorithmes et de modèles LLMs comporte des risques extrêmes de perte de capital. Les backtests, même rigoureux, souffrent toujours d'overfitting ou d'un décalage temporel avec les conditions réelles de marché.

## Decision
Toute stratégie ou version du système **DOIT prouver sa rentabilité et sa stabilité en Paper Trading (simulation Live forward-testing)** avant d'être autorisée sur un courtier en Live.

## Rationale
- Le Paper Trading confronte l'IA aux données réelles du marché entrant (temps réel) et teste la latence de l'Execution Engine, sans engager d'argent.
- Les biais cognitifs liés à l'excitation d'un backtest prometteur sont limités par cette période de probation obligatoire.

## Consequences
- Un "Paper Trading Engine" ou un simulateur branché sur le vrai flux de données doit être intégré comme citoyen de première classe.
- Il n'y aura aucun *bypass* possible dans l'architecture permettant à une stratégie non validée de router des ordres Live.
