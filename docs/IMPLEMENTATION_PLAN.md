# Plan d'Implémentation Incrémental (Architecture)

Ce document décrit la séquence d'intégration progressive des dépôts open-source sélectionnés. L'objectif est d'absorber la complexité externe étape par étape sans déstabiliser le cœur d'Aegis Quant OS.

## Étape 1 : Data & Macro Context (OpenBB) — *En cours (Mission C)*
- **Objectif** : Injecter du contexte macro-économique (DXY, US10Y) pour filtrer les faux signaux et améliorer l'Alpha.
- **Action** : Création de `aegis_trade.providers.openbb_adapter` et ingestion des séries temporelles dans le `DatasetRepository`.

## Étape 2 : Moteur d'Exécution Live (vn.py)
- **Objectif** : Remplacer le `SimulatedBroker` par un véritable connecteur marché.
- **Action** : 
  - Définir l'interface `ExecutionGateway` dans le domaine (`aegis_trade.engine`).
  - Développer le `VnPyAdapter` qui traduira les `OrderEvent` d'Aegis en commandes natives vn.py.
  - Implémenter la State Machine pour le suivi de cycle de vie des ordres (Fill, Cancel, Reject).

## Étape 3 : NLP & Sentiment (FinGPT)
- **Objectif** : Alimenter le futur `Research Analyst` (Agent) avec des données non structurées.
- **Action** :
  - Intégration d'un endpoint local/API vers FinGPT.
  - Création de l'interface `NLPFeatureProvider` pour convertir les news/earnings en features quantitatives (score de sentiment).

## Étape 4 : Feature Mining à l'échelle (Qlib)
- **Objectif** : Passer d'un Feature Engineering scripté à un pipeline vectorisé massif.
- **Action** :
  - Wrapper le module `qlib.data` derrière notre couche d'ingestion.
  - Migrer les calculs d'IC actuels (`compute_extended_feature_ic.py`) vers des Alpha158/Alpha360 générés par Qlib pour évaluation.

## Règle d'or pour chaque étape
Chaque étape doit obligatoirement inclure :
1. Définition du contrat (Interface) dans le domaine pur d'Aegis.
2. Développement de l'Adaptateur isolé.
3. Tests d'intégration mockés de l'Adaptateur.
4. Validation fonctionnelle complète via la pipeline de tests d'Aegis avant passage à l'étape suivante.
