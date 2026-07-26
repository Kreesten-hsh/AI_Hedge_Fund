# ADR 0002: Clean Architecture

## Status
Accepted

## Context
Trading systems naturally tend to become tightly coupled to their data providers, brokers, or UI frameworks. This coupling makes testing difficult and future migrations extremely risky.

## Decision
We adopt **Clean Architecture**.

## Rationale
- Le code métier (Domain, Engine) ne doit avoir aucune dépendance vers l'extérieur.
- Les changements d'API broker (ex: vn.py vers MetaTrader) ou d'API LLM (Ollama vers OpenAI) ne doivent pas exiger de réécrire la logique de prise de décision ou de gestion des risques.

## Consequences
- Toute intégration technique externe (Base de données, Broker, LLM) DOIT être placée dans le dossier `infrastructure/` ou `providers/`.
- Le flux de dépendances pointe toujours vers l'intérieur (vers le Domain).
