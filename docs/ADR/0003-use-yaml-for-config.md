# ADR 0003: Use YAML for Configuration

## Status
Accepted

## Context
L'infrastructure de l'OS (notamment l'AI Council) requiert des paramétrages complexes : choix du modèle, timeouts, formats de sortie, adresses API, etc.

## Decision
Nous utilisons **YAML** (`PyYAML` via `yaml.safe_load()`) pour tous les fichiers de configuration d'infrastructure (`config/*.yaml`).

## Rationale
- YAML est infiniment plus lisible pour l'humain que le JSON, particulièrement pour gérer des "profils" (ex: `low_resource`, `high_performance`).
- C'est le standard de facto dans l'industrie pour la configuration d'infrastructure (Docker Compose, Kubernetes, Ansible).
- Il permet l'ajout de commentaires pour documenter les réglages directement dans le fichier.

## Consequences
- JSON est banni pour les fichiers de configuration manuels (réservé aux logs et API).
- La bibliothèque `PyYAML` devient une dépendance système officielle.
