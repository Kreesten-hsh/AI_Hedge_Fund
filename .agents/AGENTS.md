# DIRECTIVE PERMANENTE — AEGIS QUANT OS

## Philosophie de développement

Nous développons désormais comme une équipe quantitative institutionnelle. Chaque modification doit respecter les principes suivants :

### 1. Une seule direction
La roadmap devient la seule source de vérité. On ne change plus de direction parce qu'une nouvelle idée paraît intéressante. Toute nouvelle idée est ajoutée dans un backlog. Elle ne modifie jamais le sprint en cours.

### 2. Pas de détour
Interdiction de :
- reconstruire une architecture déjà validée ;
- créer une nouvelle couche sans nécessité démontrée ;
- développer des composants qui ne seront pas utilisés dans les prochains sprints.
Chaque ligne de code doit servir le prochain jalon.

### 3. Chaque sprint produit une valeur réelle
Un sprint doit toujours se terminer par un résultat concret (ex: nouvelle stratégie fonctionnelle, amélioration du moteur, feature validée). Jamais uniquement par un audit, une documentation ou une abstraction.

### 4. Une seule vérité
Aucune duplication. Une seule implémentation pour les calculs mathématiques, les métriques, les indicateurs et les utilitaires. Si une logique existe déjà, on la réutilise. On ne la recopie jamais.

### 5. Les tests deviennent obligatoires
Aucun développement n'est terminé tant que :
- tous les tests passent ;
- mypy passe ;
- coverage passe ;
- les scripts critiques fonctionnent.
Une fonctionnalité non testée est considérée comme inexistante.

### 6. Aucun code spéculatif
On n'écrit plus du code "qui servira peut-être". Le code doit répondre à un besoin immédiat de la roadmap.

### 7. Une architecture minimale
La meilleure architecture est la plus simple qui répond au besoin actuel.

### 8. Validation avant évolution
Aucune nouvelle couche ne peut être développée avant validation complète de la couche précédente.
(Dataset -> Backtester -> Baseline -> Recherche de features -> Validation Train -> Validation Holdout -> Validation P&L -> Modèle -> Agents -> Portfolio -> Production). On ne saute jamais une étape.

### 9. Discipline scientifique
Une hypothèse suit toujours le même protocole : Hypothèse -> Implémentation -> Tests unitaires -> Validation statistique -> Validation économique -> Intégration. Si une étape échoue, on abandonne l'hypothèse.

### 10. Une seule définition du succès
Le projet avance uniquement lorsqu'une hypothèse est validée ou rejetée avec des preuves reproductibles. Même un rejet est une progression.

---

## Règle finale
À partir de maintenant, chaque demande de développement devra répondre à trois questions avant d'être implémentée :
1. Est-ce sur la roadmap du sprint actuel ?
2. Apporte-t-elle une valeur mesurable immédiatement ?
3. Peut-elle être validée par des tests et des métriques objectives ?

Si la réponse à l'une de ces trois questions est **non**, la fonctionnalité est reportée au backlog et n'est pas développée.
