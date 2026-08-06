---
name: oss-first
description: Use when implementing new calculation, analysis, or infrastructure modules (technical indicators, backtesting engines, risk management, feature pipelines, broker connectors, schedulers) before writing code — searches open source ecosystem, evaluates candidates (maintenance status, license, dependencies), documents decision in docs/refont/BUILD_VS_REUSE.md even when conclusion is to build internally
---

# OSS-first — chercher avant de construire

## Pourquoi ce fichier existe
Quatre implémentations d'ATR différentes ont coexisté dans ce dépôt avant
d'être découvertes en Lot 3. Une bibliothèque mature n'aurait jamais permis
ça — il n'y en aurait eu qu'une à appeler. Ce n'est pas un principe abstrait,
c'est un correctif après incident.

## Quand l'utiliser
Toute tâche qui crée un nouveau module de calcul générique : indicateur
technique, moteur d'analyse de facteurs/IC, backtester, gestion de risque,
pipeline de features, scheduler, connecteur broker/exchange.

Ne s'applique PAS à :
- la correction de bugs sur du code existant,
- la logique métier propre au projet (RiskGate, DerivGateway, CapitalTier,
  la philosophie de trading elle-même) — ça, c'est à nous, pas à remplacer.

## Processus, dans l'ordre, avant d'écrire une ligne
1. Consulter d'abord references/quant_ecosystem_map.md si le domaine y
   figure — point de départ, pas vérité figée : la carte peut dater.
2. Formuler 3-5 requêtes de recherche web ciblées sur le besoin réel, pas
   juste le nom générique du domaine.
3. Pour chaque candidat sérieux, vérifier avant de se prononcer :
   - dernière activité (idéalement <12 mois — un projet dormant depuis
     18+ mois est un signal d'alerte, pas une disqualification automatique,
     mais ça se documente)
   - nombre de mainteneurs (mainteneur unique = risque à noter)
   - licence (MIT/BSD/Apache = sans friction ; GPL/AGPL = à signaler avant
     tout usage, même sur projet perso)
   - poids des dépendances, compatible CPU-only / 12 Go RAM / pas de
     compilation lourde si évitable (contrainte matérielle du projet)
4. Comparer avec le besoin réel : la lib couvre-t-elle 80%+ sans fork
   lourd ni contournement fragile ?
5. Décider : réutiliser tel quel / wrapper mince par-dessus / construire.
   Écrire la décision ET le raisonnement dans docs/refont/BUILD_VS_REUSE.md
   — même conclusion "on construit nous-mêmes", la raison doit être écrite
   (perf mesurée, dépendance disqualifiante, licence incompatible,
   fonctionnalité manquante), jamais supposée en silence.

## Règle non négociable
Un rapport de progression qui ne mentionne pas être passé par cette
recherche, pour une tâche qui la déclenche, est traité comme une étape
sautée — pas comme "rien à signaler". Même discipline que la vérification
du code réellement poussé : ce qui n'est pas documenté n'a pas eu lieu.

## Ressources
- references/quant_ecosystem_map.md — carte de démarrage par domaine
  (indicateurs, analyse de facteurs, backtesting, RL, risque, exécution).
