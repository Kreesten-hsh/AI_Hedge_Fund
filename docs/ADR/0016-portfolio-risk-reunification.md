# ADR 0016: Réunification du Risque via Adaptateur

## Contexte

Dans le cadre de la mission PM-01 (Portfolio Management), il a été identifié que le `Backtester` modulaire souffrait de l'absence de gestion du risque (ex: drawdown > 100%), tandis qu'un `GlobalRiskManager` robuste et testé existait déjà dans la piste événementielle (legacy/future).

## Décision

Au lieu de réécrire un système de gestion de risque redondant pour la piste modulaire, nous avons décidé de réutiliser le `GlobalRiskManager` existant via le pattern Adaptateur (`GlobalRiskAdapter`).

L'adaptateur traduit l'état interne minimaliste du `Backtester` (capital, equity_curve, position) vers les objets événementiels riches attendus par le gestionnaire de risque (`OrderEvent`, `Portfolio`).

## Conséquences

### Positives
- **DRY (Don't Repeat Yourself)** : La logique de `GlobalRiskManager` reste l'unique source de vérité pour les règles de risque.
- **Sécurité** : Les limites institutionnelles (kill switch) sont appliquées à tous les backtests.
- **Isolation garantie** : Le code de la piste événementielle n'a pas eu besoin d'être modifié, respectant ainsi les contraintes architecturales de la mission.

### Négatives
- **Overhead minime** : L'instanciation de classes fantômes (`_AdapterPortfolio`, `OrderEvent`) à chaque itération engendre un très léger coût de performance.

## Notes
Cette décision servira de modèle pour les futures étapes (ex: EX-01) qui devront réutiliser des composants d'exécution événementielle depuis la piste modulaire.
