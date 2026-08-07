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

#### Gate : recherche écosystème avant construction
Avant toute tâche qui construit un module de calcul, d'analyse, ou d'infrastructure générique (indicateur, backtester, gestion de risque, scheduler, etc.) :

1. **Recherche obligatoire** : 3-5 requêtes web + vérification GitHub (dernière activité, nombre de mainteneurs, licence) AVANT d'écrire du code.
2. **Documentation dans `docs/refont/BUILD_VS_REUSE.md`** : consigner le résultat même si la conclusion est "on code nous-mêmes" — la raison doit être écrite (performance, dépendance trop lourde, licence incompatible, fonctionnalité manquante), jamais supposée.
3. **Signal d'alerte** : brique non maintenue depuis 12+ mois ou à mainteneur unique = surveiller, pas disqualification automatique.

Rationale : pandas-ta-classic (193+ indicateurs) et alphalens-reloaded (analyse IC + détection tests multiples) existent déjà et couvrent du code qu'on vient de déboguer manuellement. Le gate force la question "existe-t-il déjà ?" avant "comment on le code ?".

### 10. Une seule définition du succès
Le projet avance uniquement lorsqu'une hypothèse est validée ou rejetée avec des preuves reproductibles. Même un rejet est une progression.

---

## Constitution Technique (Engineering Rules)

1. **Règle 1 - Isolement du Domaine (Clean Architecture)** : Aucun accès direct au Broker depuis la couche Domaine (`domain/`). Toutes les interactions passent par la couche Infrastructure via des Ports/Adaptateurs.
2. **Règle 2 - Sécurisation du Chemin Critique** : Aucun LLM dans le chemin critique d'exécution des ordres temps réel. Les LLM opèrent en asynchrone hors de la boucle déterministe.
3. **Règle 3 - Justification des Dépendances & Vendoring** : Toute nouvelle dépendance ou tout code amont vendoré doit porter une justification formelle et sa licence exacte dans `docs/refont/BUILD_VS_REUSE.md`.
4. **Règle 4 - Validation par les Tests Effectifs** : Tout composant doit posséder une suite de tests unitaires exécutables qui valident le comportement réel (les mocks à `passed=True` ou tests non exécutés comptent comme absence de test).
5. **Règle 5 - Documentation-Driven Development Verified** : Toute affirmation d'état dans `docs/` doit citer un `fichier:ligne` vérifiable ou porter un marqueur d'audit mesurable.
6. **Règle 6 - Traçabilité Totale des Décisions** : Chaque cycle d'évaluation ou trade doit être traçable via un hash de commit `git_version` et un hash de données `data_hash`.

---

## Règle finale
À partir de maintenant, chaque demande de développement devra répondre à trois questions avant d'être implémentée :
1. Est-ce sur la roadmap du sprint actuel ?
2. Apporte-t-elle une valeur mesurable immédiatement ?
3. Peut-elle être validée par des tests et des métriques objectives ?

Si la réponse à l'une de ces trois questions est **non**, la fonctionnalité est reportée au backlog et n'est pas développée.
