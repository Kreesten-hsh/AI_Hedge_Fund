# ADR 0005: Decision Cache

## Status
Accepted

## Context
Les appels aux LLMs sont coûteux, soit financièrement (API Cloud), soit en temps et ressources matérielles (Inférence locale GPU/CPU). De plus, dans un flux de trading, la même configuration de marché (RSI, ATR, Régime) peut survenir à l'identique entre deux bougies consécutives s'il n'y a pas de mouvement.

## Decision
Implémenter un `DecisionCache` générique basé sur un hash SHA-256 déterministe du dictionnaire de contexte d'entrée.

## Rationale
- Si l'environnement (Market Data) fourni à un Agent (Macro, Risk) est strictement identique au cycle précédent, l'IA produira la même analyse (à température 0).
- Re-calculer cette analyse est un pur gaspillage.
- Le hashage SHA-256 garantit une clé unique, et la normalisation JSON déterministe évite les faux "miss" de cache.

## Consequences
- Chaque itération du système (Tick) est drastiquement accélérée.
- La base de code doit s'assurer que le dictionnaire de `context` est sérialisable en JSON.
