# ADR 0009: Event-Driven Architecture

## Status
Accepted

## Context
Un système de trading doit réagir asynchronement et instantanément à de multiples stimuli : l'arrivée d'un nouveau tick (prix), la confirmation d'un ordre, ou une alerte de l'IA, sans bloquer l'exécution globale.

## Decision
Nous adoptons une **Event-Driven Architecture (EDA)** asynchrone, orchestrée par un Event Bus.

## Rationale
- Le couplage entre les composants est réduit. Le `DataPipeline` émet un `MarketBarEvent`, il ne s'occupe pas de savoir si l'IA, le Dashboard ou le Risk Engine sont à l'écoute.
- Permet de gérer la haute fréquence (High Frequency / Intra-day) sans blocage I/O.
- Extrêmement adapté à la logique de *Paper Trading* ou de *Replay* (Backtesting) où l'on simule des événements dans le temps.

## Consequences
- Toute communication majeure entre les "Bounded Contexts" (ex: Data -> Engine, Engine -> Execution) doit se faire par émission d'Événements.
- Le bus d'événements doit être robuste et supporter le mode asynchrone (non-bloquant).
