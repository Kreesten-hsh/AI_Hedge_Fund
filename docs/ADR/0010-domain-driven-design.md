# ADR 0010: Domain-Driven Design (DDD)

## Status
Accepted

## Context
La logique financière est complexe, avec un vocabulaire spécifique (Equity, Slippage, Drawdown, Long, Short). Si le code est parsemé de simples dictionnaires ou de variables primitives non sémantiques, les bugs et erreurs de calcul se multiplieront.

## Decision
Aegis Quant OS est structuré selon les principes du **Domain-Driven Design (DDD)**.

## Rationale
- Le code devient le reflet du "langage omniprésent" (Ubiquitous Language) du trading. Les experts financiers et les développeurs parlent le même langage.
- L'intégrité de la donnée est assurée à sa source. Une position ne peut être modifiée arbitrairement de l'extérieur sans passer par des méthodes de domaine strictes.

## Consequences
- Création obligatoire d'entités métiers riches (`MarketBar`, `Trade`, `Position`, `Signal`) possédant leur propre logique de validation.
- Interdiction stricte d'utiliser des types primitifs ou des dictionnaires bruts pour transporter des informations métiers entre les composants majeurs.
