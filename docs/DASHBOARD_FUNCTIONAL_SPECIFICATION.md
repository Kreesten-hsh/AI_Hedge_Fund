# Spécifications Fonctionnelles du Dashboard — v2 (Post AI-01 à AI-07)

> Ce document remplace intégralement `docs/DASHBOARD_FUNCTIONAL_SPECIFICATION.md` (v1), rédigé avant le pivot Phase 2. La v1 décrit un Council LLM (Macro/Risk Analyst + Synthesizer) qui a depuis été explicitement retiré du chemin de décision (`LEGACY_COUNCIL_MIGRATION.md`, AI-05). Ce document reflète l'architecture réellement en place : Comité à 8 agents déterministes, politique RL, base de connaissances, ségrégation du capital réel.

## 0. Principe directeur

Le Dashboard est le **centre de contrôle unique**, pas un simple visualiseur. Toute vue doit être connectée à une source de données réelle du backend (`MonitoringEngine`, `application/dashboard/services.py`, routers FastAPI existants) — aucune donnée mockée en dur dans le frontend. S'il manque un endpoint backend pour alimenter une vue, cet endpoint doit être créé avant l'implémentation de la vue correspondante, jamais après (pas de maquette front qui tourne dans le vide).

## 1. Architecture (inchangée dans le principe, précisée dans le détail)

```
[ React (Frontend) ]
        │
   (WebSocket temps réel + REST pour l'historique)
        ▼
[ FastAPI — api/routers/*.py ]
        │
   (Dependency Injection)
        ▼
[ DashboardService → MonitoringEngine ]
        │
        ▼
[ Domaine Aegis : Council, RL, Reasoning, Capital, Risk ]
```

Existant déjà en place : `MonitoringEngine` (Portfolio/Risk/System/Performance snapshots), `application/dashboard/services.py`, WebSocket broadcast (`_broadcast`), routers `orders.py`, `portfolio.py`, `positions.py`, `risk.py`, `system.py`, `observability.py`. **Manquant** : aucun router n'expose aujourd'hui le Council, le RL, la Knowledge Base, ni le Capital Tiering.

## 2. Vues et composants

### 2.1 Vue Trading (Main Center) — *existe déjà en partie*
- `Balance Globale`, `Equity`, `PnL Latent/Réalisé`, `Exposition Globale` — déjà servis par `PortfolioSnapshot`.
- **Nouveau** : indicateur de mode proéminent et non-ignorable en permanence à l'écran — `DEMO` / `PAPER` / `LIVE` avec code couleur strict (vert=démo, orange=paper réel non simulé, **rouge=argent réel**). Doit lire l'état réel de `AEGIS_ENV` et du `DerivGateway`/`LiveDerivGateway` actif — jamais un simple label statique.
- Tableau des positions ouvertes (existant), avec ajout de la colonne `Agent Council dominant` (quel agent a le plus pesé dans la décision d'ouverture, via `agent_weights` de la `PolicyDecision` active).

### 2.2 Vue Performance (Analytics) — *à étendre*
- Métriques existantes (Win Rate, Profit Factor, Sharpe, Sortino, Max Drawdown, Expectancy).
- **Nouveau, aligné sur `BENCHMARKS.md`** : les 9 métriques du `BenchmarkGate` affichées avec code couleur pass/fail par rapport aux seuils réels (85% Win Rate, Sortino 2.0, etc.) — pas les anciens seuils laxistes.
- **Nouveau** : fréquence de trading (trades/heure, trades/jour), avec la cible opérationnelle 100-200/jour affichée comme repère visuel.
- **Nouveau** : coût de spread cumulé/jour (métrique ajoutée en AI-07), affiché à côté du PnL net pour vérifier que le frottement ne mange pas les petits gains.
- Graphique Equity — **c'est ici que `lightweight-charts` s'intègre** (remplace tout graphique générique) : ligne d'équity avec superposition des points d'entrée/sortie de trades, zoomable, cohérent avec la philosophie "petits gains accumulés" (visualiser la pente régulière, pas juste le solde final).

### 2.3 Vue Comité IA (Council Supervisor) — *entièrement nouvelle, remplace la v1 obsolète*
Doit refléter le vrai pipeline (`AEGIS_DECISION_PIPELINE.md`) :
- **Flux temps réel des votes** : pour chaque décision, afficher les 8 votes (`AgentVote` : Trend, Momentum, Volatility, Liquidity, Pattern, Portfolio, Execution, News) avec leur `vote` et `confidence` individuels — pas seulement la décision finale.
- **Pondération RL active** : afficher les `agent_weights` actuellement chargés depuis `active_policy.json` (via `PolicyCheckpointStore`), avec la date de dernière promotion de politique et son score au moment de la promotion. Si aucune politique promue (fallback poids égaux), l'indiquer clairement plutôt que d'afficher des poids sans contexte.
- **Résolution de conflit** : afficher le niveau de désaccord calculé (`ConflictResolver`) et l'action prise (position réduite ÷4, ou abandon) quand applicable — c'est un signal important à surveiller, pas à cacher dans les logs.
- **Décision finale** : `CouncilVerdict` (vote, confiance agrégée, multiplicateur de taille) et le résultat du passage par `GlobalRiskManager.validate_order` (approuvé / bloqué + raison).

### 2.4 Vue Connaissance (Knowledge & Reasoning) — *entièrement nouvelle*
Absente de la v1, pourtant centrale au projet (AI-03) :
- Liste des règles `Knowledge` actives (`AvoidPattern`, `PreferredPattern`, `RiskObservation`, `MarketObservation`) avec leur `KnowledgeScore` (confidence, support, fréquence, récence, stabilité) — reprend exactement le format déjà défini dans `KNOWLEDGE_SYSTEM.md` (ex: "Rule #142, Confidence 98%, Support 1247 expériences").
- Historique de versionnement (`KnowledgeVersion`/`KnowledgeDiff`) : possibilité de répondre visuellement à "qu'a appris Aegis cette semaine ?" — exigence déjà posée dans la directive AI-03 d'origine, jamais construite côté UI.
- Clusters découverts (`PatternClusterEngine`) avec leur taille et leur nature (succès/échec/rare).

### 2.5 Vue Risque & Capital (Risk & Control) — *étendue pour le capital réel*
- Jauge d'exposition, distance au Max Drawdown Limit (existant).
- **Nouveau, critique** : vue `CapitalAllocation` — chaque `CapitalTier` affiché individuellement avec son solde, son plafond de drawdown absolu, sa distance à ce plafond, et son statut (actif / tué par kill switch). Aucune agrégation qui masquerait qu'une tranche spécifique est en train d'approcher son seuil.
- **BOUTON KILL SWITCH** (existant dans la v1, à conserver et connecter réellement à `GlobalRiskManager`) — avec modale de confirmation, et distinction visuelle claire entre "couper une tranche" et "couper tout le système".
- **Nouveau** : affichage explicite si `LiveDerivGateway` est actif (le flag `i_understand_this_is_real_money` a été positionné) — jamais silencieux.

### 2.6 Vue Données & Pipeline de Validation (Data & Validation Status) — *nouvelle, remplace la vue "Données" v1 trop vague*
- Statut du Data Pipeline (existant : dernière synchronisation).
- **Nouveau** : statut du `VALIDATION_PIPELINE_REPORT.md` affiché directement dans l'UI (Historical/Replay/Paper/Shadow : PASSED/PENDING/FAILED), avec le verdict GO/NO-GO final bien visible. Le Dashboard ne doit jamais laisser croire que le système est prêt pour le capital réel si le rapport dit NO-GO — cohérence forcée entre ce que dit ce document et ce qu'affiche l'UI, pas deux sources de vérité qui divergent (le problème qu'on vient de corriger côté documentation ne doit pas se reproduire côté UI).

### 2.7 Vue Journal (Trade History) — *inchangée*
Tableau paginé, export CSV (v1 déjà correcte sur ce point).

## 3. Fréquence de rafraîchissement

- Equity / PnL / Positions / Votes du Council en cours : temps réel (WebSocket, ≤ 1s).
- Knowledge Base / Clusters : rafraîchissement à chaque `KnowledgeCreated`/`ClusterUpdated` (événementiel, pas de polling).
- Politique RL active : rafraîchissement à chaque `PolicyPromoted` (événementiel).
- Rapport de Validation Pipeline : à chaque régénération du rapport (événementiel + bouton de rafraîchissement manuel).
- Graphiques de performance : quotidien ou à la clôture d'un trade (REST), inchangé de la v1.

## 4. Ordre d'implémentation recommandé

Ne pas tout construire en un bloc. Ordre suggéré, du plus simple/déjà-connecté au plus nouveau :
1. Compléter les vues déjà partiellement câblées (2.1, 2.2, 2.7) et y intégrer `lightweight-charts` pour le graphique d'équity.
2. Vue 2.6 (Statut Validation) — la plus critique pour éviter toute confusion sur l'état réel du système avant capital réel, et relativement simple (lecture directe du rapport).
3. Vue 2.5 étendue (Capital Tiering) — nécessaire dès qu'AI-07b devient réel.
4. Vues 2.3 (Council) et 2.4 (Knowledge) — les plus nouvelles, demandent de nouveaux endpoints backend dédiés (`api/routers/council.py`, `api/routers/knowledge.py`, à créer).

## 5. Endpoints backend à créer (constat, pas encore existants)

- `api/routers/council.py` : expose le dernier `CouncilVerdict` + les 8 `AgentVote`, en WebSocket.
- `api/routers/knowledge.py` : expose les `Knowledge` actifs + versions, en REST (pagination) + WebSocket pour les nouveaux.
- `api/routers/capital.py` : expose `CapitalAllocation`/`CapitalTier` en temps réel.
- `api/routers/validation.py` : expose le contenu structuré de `VALIDATION_PIPELINE_REPORT.md` (le parser/générer en JSON plutôt que markdown brut pour l'UI).
