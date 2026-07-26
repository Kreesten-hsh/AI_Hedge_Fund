# Backlog Officiel — Aegis Quant OS

Ce document liste les missions structurées de l'OS de trading. Il sert de plan de travail séquentiel.

## DATA (Données et Features)

### DATA-01 : Intégration OpenBB (Market Data)
- **Objectif** : Implémenter un connecteur officiel robuste pour télécharger l'historique EOD et intra-day.
- **Priorité** : Haute
- **Dépendances** : Aucune
- **Durée estimée** : 1 Sprint
- **Difficulté** : Moyenne
- **Critères de validation** : Les données OpenBB sont téléchargées, formatées en objets `MarketBar` du domaine, et stockées localement (Parquet/DuckDB).
- **Statut** : PLANNED

### DATA-02 : Feature Engine Standardisé
- **Objectif** : Moteur centralisé pour extraire les indicateurs techniques et statistiques des séries temporelles.
- **Priorité** : Haute
- **Dépendances** : DATA-01
- **Durée estimée** : 1 Sprint
- **Difficulté** : Haute
- **Critères de validation** : Les stratégies ne calculent plus les indicateurs elles-mêmes mais les requêtent au Feature Engine.
- **Statut** : PLANNED

## DASH (Dashboard et Supervision)

### DASH-01 : Architecture Backend FastAPI & Base de Données Métriques
- **Objectif** : Créer l'API locale permettant d'exposer l'état interne (Risque, Portefeuille, Trades).
- **Priorité** : Haute
- **Dépendances** : Aucune
- **Durée estimée** : 1 Sprint
- **Difficulté** : Moyenne
- **Critères de validation** : Des endpoints REST renvoient l'Equity, le Drawdown, et l'historique des décisions de l'IA en temps réel.
- **Statut** : PLANNED

### DASH-02 : Interface Front-End React
- **Objectif** : Développer le tableau de bord visuel basé sur `DASHBOARD_FUNCTIONAL_SPECIFICATION.md`.
- **Priorité** : Haute
- **Dépendances** : DASH-01
- **Durée estimée** : 2 Sprints
- **Difficulté** : Moyenne
- **Critères de validation** : L'interface visuelle s'affiche correctement, met à jour les graphiques PnL en live et inclut le bouton "Kill Switch".
- **Statut** : PLANNED

## EXEC (Exécution et Brokers)

### EXEC-01 : Paper Trading Engine
- **Objectif** : Simuler l'exécution d'ordres en incluant de la latence, du slippage, et le calcul des frais.
- **Priorité** : Haute
- **Dépendances** : DATA-01
- **Durée estimée** : 1 Sprint
- **Difficulté** : Moyenne
- **Critères de validation** : Le système peut "virtuellement" accumuler des positions et un PnL cohérent sans broker externe.
- **Statut** : PLANNED

### EXEC-02 : Connecteur vn.py (Live/Paper)
- **Objectif** : Intégrer formellement l'API vn.py dans l'Execution Engine pour router des ordres sur un vrai compte de démonstration.
- **Priorité** : Moyenne
- **Dépendances** : EXEC-01
- **Durée estimée** : 2 Sprints
- **Difficulté** : Haute
- **Critères de validation** : Des ordres limit/market sont envoyés au broker, acceptés, exécutés et les callbacks mettent à jour le Portfolio Engine.
- **Statut** : PLANNED

## AI (Intelligence Artificielle)

### AI-01 : Asynchronisme du AI Council
- **Objectif** : Permettre l'exécution concurrente (via `asyncio`) des divers Agents pour drastiquement réduire la latence.
- **Priorité** : Moyenne
- **Dépendances** : Aucune
- **Durée estimée** : 1 Sprint
- **Difficulté** : Haute
- **Critères de validation** : Le MacroAnalyst, le RiskAnalyst et le TechnicalAnalyst s'exécutent en parallèle avant la synthèse.
- **Statut** : PLANNED

### AI-02 : Intégration Modèles Cloud (OpenAI / Claude)
- **Objectif** : Créer les nouveaux adaptateurs LLM pour les modèles distants.
- **Priorité** : Basse
- **Dépendances** : INFRA-01 (Terminé)
- **Durée estimée** : 1 Sprint
- **Difficulté** : Faible
- **Critères de validation** : Le fichier `llm.yaml` permet de *plugger* `provider: openai` sans modifier le domaine.
- **Statut** : PLANNED

## RISK (Gestion du Risque)

### RISK-01 : Kill Switch Avancé et Alerting
- **Objectif** : Déclencher un arrêt immédiat (Flatten all positions) si un Max Drawdown ou une anomalie serveur est détectée.
- **Priorité** : Critique avant le Live
- **Dépendances** : EXEC-01
- **Durée estimée** : 1 Sprint
- **Difficulté** : Moyenne
- **Critères de validation** : Le bouton Kill Switch du dashboard force la fermeture de toutes les positions via le broker en moins de 1 seconde.
- **Statut** : PLANNED
