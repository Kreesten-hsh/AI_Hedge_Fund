# ADR 0012: AI Council Pattern

## Status
Accepted

## Context
Dépendre d'un seul agent LLM omniscient pour analyser les données de marché, évaluer le risque macro-économique et formuler une décision de trading mène à des "hallucinations" et à un aplatissement du raisonnement. Le modèle unique peine à pondérer simultanément des signaux contradictoires (ex: fonda haussier, technique baissier).

## Decision
Nous adoptons un **Pattern d'AI Council (Conseil IA multi-agents)**.

## Rationale
- La séparation des rôles (Macro, Risque, Technique) oblige chaque Agent à se concentrer sur son domaine d'expertise, produisant un rapport isolé, spécialisé et non biaisé par les autres agents.
- Un agent final (`CouncilSynthesizer`) endosse le rôle de juge. Il reçoit tous les rapports spécialisés et produit une synthèse pour formuler une décision d'ensemble, avec un niveau de confiance (`confidence`) et des arguments sourcés.

## Consequences
- Multiplie les requêtes LLM par cycle de décision. Le `DecisionCache` devient donc une obligation technique absolue.
- Le format des prompts système (instructions des agents) devient modulaire.
