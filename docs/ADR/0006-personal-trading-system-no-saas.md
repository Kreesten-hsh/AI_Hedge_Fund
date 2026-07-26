# ADR 0006: Personal Trading System (No SaaS)

## Status
Accepted

## Context
Le développement d'applications financières dérive souvent vers des architectures complexes (multi-tenant, gestion d'abonnements, authentification Oauth) en prévision d'une hypothétique commercialisation.

## Decision
Aegis Quant OS est déclaré strictement comme un **Système Personnel**. Aucune fonctionnalité SaaS ou commerciale ne sera développée.

## Rationale
- Gérer des utilisateurs multiples, des droits d'accès concurrents et une base de données partitionnée (multi-tenancy) multiplie la complexité de la base de code par 10.
- La mission d'Aegis est d'être performant sur le trading, pas de gérer des abonnements Stripe.
- Le concepteur unique doit avoir un contrôle direct et sans friction sur son infrastructure.

## Consequences
- Pas de tables `Users`, `Subscriptions` ou `Organizations` dans la base de données.
- Pas de barrière de login complexe autre qu'un simple mot de passe d'accès pour l'opérateur (ACL basique).
- Les décisions architecturales favorisent la simplicité de déploiement (Local-First).
