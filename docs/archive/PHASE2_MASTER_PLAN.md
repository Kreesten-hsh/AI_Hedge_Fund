# Phase 2 : Master Plan

## 1. Vision
La Phase 2 marque la transition d'Aegis Quant OS d'un moteur d'exécution pur vers une **Intelligence Asymétrique**. L'IA n'est pas le trader ; elle est le cerveau analytique, la mémoire, et le conseiller. Le système repose sur l'apprentissage par l'expérience plutôt que sur un LLM prédictif magique.

## 2. Objectifs
- Créer un laboratoire de recherche autonome.
- Implémenter une mémoire vectorielle asymétrique (Success Memory vs Failure Memory).
- Déléguer l'analyse à un comité d'agents spécialisés sans bloquer le moteur d'exécution temps réel.
- Développer en démo exclusivement, jusqu'à validation mathématique de la survie.

## 3. Architecture Logique (Le Nouveau Cerveau)
L'exécution et l'apprentissage sont désynchronisés. 

```text
Marché
  ↓
Extraction des Features
  ↓
Mémoire (FAISS)
  ↓
Recherche de patterns (Top 200)
  ↓
Agents spécialisés (Conseil)
  ↓
Vote
  ↓
Risk Manager (Veto)
  ↓
Broker
  ↓
Trade
  ↓
Apprentissage (Post-Trade)
  ↓
Mémoire (Success / Failure)
```

## 4. Critères de Réussite
- **Stabilité** : Zéro crash du moteur de trading en 1 mois d'exécution continue (24/7).
- **Asymétrie** : Le système doit démontrer qu'il ne reproduit plus une erreur fatale après l'avoir documentée dans la *Failure Memory*.
- **Contrôle des Risques** : Max Drawdown strictement contenu sous le seuil défini dans la philosophie du projet.

## 5. Dépendances
- Infrastructure de Phase 1 validée (vn.py, EventBus, Clean Architecture).
- Modèles d'embedding opérationnels.
- Base vectorielle (FAISS) persistante.
