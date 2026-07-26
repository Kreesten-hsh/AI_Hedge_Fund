# ADR 0008: Provider Abstraction

## Status
Accepted

## Context
Dans l'écosystème financier, les APIs changent, les brokers ferment ou restreignent les accès, et les sources de données deviennent payantes (ex: Yahoo Finance devenant instable, AlphaVantage modifiant ses limites).

## Decision
Tout fournisseur de données externe, courtier, ou moteur d'Intelligence Artificielle est considéré comme "remplaçable" et doit être masqué derrière un **Adapter**.

## Rationale
- Évite le "Vendor Lock-in" (la dépendance forte à un seul fournisseur).
- Si vn.py cesse d'être maintenu, l'Execution Engine n'a pas besoin d'être réécrit, seul l'adaptateur change (pour passer à MetaTrader ou Interactive Brokers).
- Permet un basculement instantané en cas de panne réseau (ex: le fournisseur Data A est *down*, on passe sur le Data B).

## Consequences
- Aucun import d'une bibliothèque tierce (ex: `import openbb` ou `import ccxt`) n'est autorisé dans les dossiers `engine/` ou `domain/`.
- La création systématique d'interfaces abstraites est requise.
