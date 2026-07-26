# Product Roadmap — Aegis Quant OS

La feuille de route définit les jalons de développement d'Aegis Quant OS pour combler les écarts architecturaux identifiés. Elle abandonne toute terminologie commerciale (MVP, V1, V2) au profit de Phases techniques séquentielles (Phase 4, Phase 5...), garantissant que l'on construit brique par brique ce système de trading personnel.

---

## Phase 4 : Data & Feature Pipelines (Fondations des Données)

### Objectif
Mettre en place une source de vérité unique pour les données de marché et standardiser l'extraction des signaux quantitatifs pour l'IA.

### Livrables
- Intégration officielle complète avec **OpenBB** (Market Data unifié).
- Architecture de **Data Pipeline** (Stockage local Parquet / DuckDB pour l'historique time-series).
- **Feature Engine** formel (Connecté à Qlib) pour la standardisation des features techniques (RSI, ATR, Volatilité) indépendamment de la logique de trading.

### Dépendances
- Infrastructure LLM validée (Phase 3 - Terminée).

### Risques
- Saturation des limites de requêtes API (Rate limits) lors du backfill massif. Solution : Mise en cache agressive.

### Critères d'acceptation
- Le `DatasetEngine` est remplacé ou complété par un Data Pipeline capable de télécharger, nettoyer et stocker des milliers de bougies (Marketbars) automatiquement.
- Les Stratégies ne calculent plus manuellement l'ATR ou le RSI, elles le lisent via le Feature Engine.

---

## Phase 5 : Control Center (Le Dashboard Local)

### Objectif
Créer l'interface visuelle (Le Centre de Contrôle) permettant de superviser les moteurs (Risque, Portefeuille, IA) sans interagir directement dans le terminal.

### Livrables
- Spécifications techniques du Dashboard (React/FastAPI ou Streamlit).
- Base de données locale de journalisation (Trade Journal persisté).
- Dashboard opérationnel (Lecture seule dans un premier temps) affichant PnL, Positions et Historique des Décisions IA.

### Dépendances
- Phase 4.

### Risques
- Dérive technologique vers un outil Web lourd. La contrainte "Local-First" doit prévaloir.

### Critères d'acceptation
- Le Dashboard tourne localement et affiche l'état réel des objets `PortfolioEngine` et `RiskEngine`.
- L'utilisateur peut voir les décisions prises par l'IA et le "pourquoi".

---

## Phase 6 : Paper Trading & Brokers (Execution Engine)

### Objectif
Brancher Aegis Quant OS sur un environnement d'exécution simulé (Paper Trading) via un broker, puis préparer le routage Live.

### Livrables
- Implémentation de l'**Execution Engine**.
- Intégration formelle avec l'API **vn.py** ou Interactive Brokers.
- Mécanique de Slippage simulé.

### Dépendances
- Phase 4 (Données live requises) et Phase 5 (Pour le monitoring des exécutions).

### Risques
- Asynchronisme des flux de brokers (WebSockets vs REST). Le bus d'événements doit être extrêmement robuste.

### Critères d'acceptation
- Un ordre généré par le `PortfolioEngine` et validé par le `RiskEngine` est routé vers un compte de Paper Trading et réconcilié correctement au retour.

---

## Phase 7 : Échelle IA & Cloud LLM

### Objectif
Démultiplier la puissance de décision en intégrant de vrais LLMs asynchrones Cloud (OpenAI, Claude) pour le Macro et le Fondamental, gardant les modèles locaux pour le haut-débit (Technique/Risque).

### Livrables
- Adapters pour OpenAI, Anthropic (Claude), vLLM.
- AI Council asynchrone (Exécution concurrente des agents de recherche).
- Modèles prédictifs croisés (FinGPT).

### Dépendances
- Phase 6.

### Risques
- Dérive des coûts liés aux appels d'API LLM Cloud.
- Temps de latence incompatibles avec le trading court-terme.

### Critères d'acceptation
- L'utilisateur peut utiliser Ollama pour le *Risk Analyst* et Claude pour le *Macro Analyst* simultanément.
- Le Cache de Décision prouve son efficacité économique.

---

## Phase 8 : Live Trading & Optimisation

### Objectif
Engagement de capital réel sous contrôle strict du Risk Engine.

### Livrables
- Kill Switch manuel actif depuis le Dashboard.
- Alerting (Email/Telegram/Discord) en cas d'anomalies.
- Moteur de réconciliation nocturne des fonds (Account Sync).

### Dépendances
- Succès validé sur au moins 3 mois en Paper Trading (Phase 6).

### Risques
- Perte financière due à une anomalie. Le Risk Engine doit être sanctuarisé.

### Critères d'acceptation
- Ordres exécutés sur le marché réel sans intervention manuelle (autre que la supervision du Dashboard).
