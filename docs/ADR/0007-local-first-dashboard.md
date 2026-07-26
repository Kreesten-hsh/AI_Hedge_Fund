# ADR 0007: Local-First Dashboard

## Status
Accepted

## Context
Aegis Quant OS nécessite une interface de supervision (Dashboard) pour auditer les décisions de l'IA, observer le PnL, et déclencher un arrêt d'urgence. De nombreux frameworks Cloud et SaaS existent, ainsi que des plateformes d'analytics hébergées.

## Decision
Le Dashboard doit être développé avec une approche **Local-First**, hébergé sur la même infrastructure privée que le moteur de trading.

## Rationale
- La confidentialité absolue des positions et des stratégies est requise. Les données ne doivent pas transiter sur des serveurs tiers.
- La latence d'affichage et surtout de la commande "Kill Switch" doit être la plus faible possible (boucle locale).
- L'infrastructure est simplifiée : aucun besoin de sécuriser une API exposée sur Internet.

## Consequences
- Les frameworks choisis devront être des outils backend/frontend classiques (FastAPI, React, ou Streamlit) déployables localement.
- Pas de déploiement Vercel, Netlify ou Heroku pour le projet.
