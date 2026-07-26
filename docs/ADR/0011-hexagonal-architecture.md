# ADR 0011: Hexagonal Architecture

## Status
Accepted

## Context
(Complémentaire à l'ADR 0002 - Clean Architecture)
Le système interagit avec le monde extérieur de multiples façons : il consomme de la donnée entrante (Data Feeds) et émet des ordres sortants (Brokers, Bases de données).

## Decision
Nous implémentons une stricte **Architecture Hexagonale (Ports et Adapters)**.

## Rationale
- L'architecture distingue formellement les **Ports** (les interfaces que l'Engine définit pour ses besoins) et les **Adapters** (l'implémentation concrète de ces interfaces).
- Le Core Engine est au centre de l'hexagone. Il ne sait rien du réseau, d'internet, des fichiers, ou de l'affichage.

## Consequences
- Le dossier `src/aegis_trade/` reste divisé en `domain/`, `engine/` (l'intérieur de l'hexagone) et `providers/`, `infrastructure/` (l'extérieur).
- Le Core Engine est 100% testable unitairement en isolation totale via des Adapters de type "Mock".
