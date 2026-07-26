# ADR 0013: Risk-First Philosophy

## Status
Accepted

## Context
En trading quantitatif, les stratégies les plus rentables s'effondrent si le risque n'est pas maîtrisé. Un bug dans la génération des signaux ou une hallucination de l'IA pourrait générer des ordres absurdes ruinant le portefeuille.

## Decision
La gestion du risque n'est pas un module optionnel. Nous adoptons une philosophie **Risk-First**. Le `RiskEngine` est l'autorité suprême du système.

## Rationale
- Protéger le capital est plus important que d'optimiser le profit.
- Le `RiskEngine` agit comme un "pare-feu". Toute décision prise par l'AI Council ou le Portfolio Engine DOIT passer au travers de ses filtres avant d'atteindre l'Execution Engine.
- Si le `RiskEngine` rejette une transaction ou déclenche un Kill Switch, aucune autre brique du système ne peut outrepasser cette décision.

## Consequences
- Le module `RiskEngine` doit être testé avec une couverture (Coverage) de 100%.
- Son code doit rester le plus simple, robuste et déterministe possible (pas d'IA probabiliste dans les règles dures du RiskEngine).
