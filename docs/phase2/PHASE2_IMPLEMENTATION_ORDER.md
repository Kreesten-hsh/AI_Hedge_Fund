# Ordre d'Implémentation de la Phase 2

## Règle de Gouvernance Absolue
> **Aucun nouveau code ne sera accepté tant qu'il n'existe pas un document officiel qui explique pourquoi ce code existe.**
> Tout développement d'une mission `AI-X` est bloqué tant que sa documentation technique n'a pas été formellement validée. Toute modification d'architecture exige une mise à jour de la documentation *avant* la modification du code.

## Ordre de Marche Strict

1. **DOC-01 à DOC-04** : Rédaction, Audit, Architecture, Validation. *(Terminé)*
2. **AI-01 : Memory Engine** *(Terminé)*
   - *Pré-requis :* Validation de `EXPERIENCE_MEMORY_SPEC.md`
   - *Implémentation :* FAISS, Base Vectorielle.
3. **AI-02 : Reflection Engine**
   - *Pré-requis :* Validation AI-01, Modèles Kronos/FinGPT définis.
   - *Implémentation :* Feature extraction, boucle post-trade.
4. **AI-03 : Reinforcement Learning**
   - *Pré-requis :* Validation AI-02, `RL_LEARNING_SPEC.md`.
   - *Implémentation :* Custom Gym Environment, Reward Function.
5. **AI-04 : Multi Agent Council**
   - *Pré-requis :* Validation AI-03, `MULTI_AGENT_COUNCIL.md`.
   - *Implémentation :* Prompting, Voting system, Risk Veto.
6. **AI-05 : Demo Training**
   - *Pré-requis :* Assemblage AI-01 à AI-04.
   - *Implémentation :* Exécution Paper Trading HFT continue, remplissage du `RESEARCH_LOGBOOK.md`.
7. **AI-06 : Performance Validation**
   - *Pré-requis :* > 5000 expériences enregistrées.
   - *Implémentation :* Audit mathématique des résultats.
8. **AI-07 : Live Trading**
   - *Pré-requis :* Validation de la survie (Zéro risque de ruine détecté).
   - *Implémentation :* Dépôt de capital réel.
