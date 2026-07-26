# AEGIS QUANT OS - INTEGRATION BLUEPRINT
**Status:** FINAL (Pass 5)
**Architecture Scope:** Meta-Orchestrator Pattern

---

## 1. OpenBB Platform (v4)

### 1.1 Présentation
- **Objectif :** Interface unifiée pour l'accès aux données financières (TET: Transform-Extract-Transform).
- **Cas d'usage :** Ingestion de données multi-sources (Yahoo, Polygon, FRED), recherche macroéconomique et fondamentale.
- **Maturité :** Très élevée. La version 4 (Platform) a éliminé la dette technique des versions 3 (Terminal/Spaghetti) au profit d'une architecture modulaire basée sur FastAPI et Pydantic.
- **Activité :** Soutenue (soutien VC, communauté massive, mises à jour hebdomadaires).

### 1.2 Architecture
- **Couches :**
  - *Core (`openbb-core`)* : Moteur de routage, validation Pydantic, standardisation en DataFrames Pandas.
  - *Extensions* : Modules métiers pluggables (`openbb-equity`, `openbb-economy`).
  - *Providers* : Implémentations spécifiques des fournisseurs de données.
- **Interfaces :** Python native (`import openbb`), REST API (FastAPI).

### 1.3 Analyse Critique
- **Ce qui est excellent :** La standardisation des données multi-sources via Pydantic et le pattern *pluggable* de la v4. L'orientation "API-first" parfaite pour les agents LLM.
- **Ce qui apporte une valeur directe :** L'accès unifié aux données fondamentales et macroéconomiques, qui remplace avantageusement nos scripts d'ingestion `yfinance` ou `fredapi`.
- **Ce qui est inutile/à ignorer :** Les interfaces Terminal legacy (v3) ou les composants de visualisation interactifs (Aegis gère sa propre UI/Télémétrie).

### 1.4 Stratégie d'Intégration
- **Mode :** **Bibliothèque Core (Data Layer)**
- **Justification :** OpenBB v4 est conçu comme un SDK Python modulaire pur. L'intégrer comme bibliothèque permet au `DatasetEngine` d'Aegis de déléguer l'ingestion brute tout en gardant le contrôle sur le stockage (Parquet).

### 1.5 Composants Retenus
- `openbb-core` (Standardisation)
- `openbb-equity`, `openbb-economy` (Classes d'actifs)
- Standardisation Pydantic pour l'ingestion.

### 1.6 Composants Exclus
- OpenBB Terminal UI
- OpenBB Charting / Visualisation
- OpenBB Copilot (Aegis utilise son propre Research Council).

### 1.7 Dépendances
- **Python :** `openbb`, `pydantic`, `fastapi`.
- **Risques :** Changements d'API des fournisseurs gérés en amont par l'équipe OpenBB. Faible risque local. Coût de maintenance très bas.

### 1.8 Position dans Aegis
- **Couche :** **Data Infrastructure (Ingestion)**
- **Rôle :** Fournisseur universel de données pour le `DatasetEngine`.

### 1.9 Interactions
- `OpenBB` -> `Aegis DatasetEngine` -> `Qlib (Backtest)`
- `OpenBB` -> `Research Council` (requêtes ad-hoc pour les analystes fondamentaux).

### 1.10 Sprint d'intégration
- **Priorité :** P0
- **Sprint cible :** Sprint Data (Immédiat, pour remplacer `yfinance` en dur).
- **Prérequis :** Nettoyage de `DatasetResolver` pour accepter les endpoints OpenBB.

---

## 2. Microsoft Qlib

### 2.1 Présentation
- **Objectif :** Plateforme de recherche quantitative orientée IA couvrant tout le cycle de vie (processing, training, backtesting).
- **Cas d'usage :** Recherche de facteurs (Alpha seeking), modélisation des risques, optimisation de portefeuille, machine learning (RL, LightGBM, Transformers).
- **Maturité :** Production-Grade Research. Utilisé en interne chez Microsoft et par des fonds quantitatifs.
- **Activité :** Maintenue par Microsoft Research, communauté académique et quant très active.

### 2.2 Architecture
- **Couches :**
  - *Data Infrastructure* : Format binaire propriétaire ultra-rapide pour les séries temporelles.
  - *Learning Framework* : Support PyTorch, LightGBM, RL.
  - *Workflow Layer* : Signal generation (Alpha), Risk/Portfolio, Executor.
- **Interfaces :** Python API orientée configurations YAML/Dict.

### 2.3 Analyse Critique
- **Ce qui est excellent :** Le format de données binaire (haute performance), le "Model Zoo" (modèles SOTA prêts à l'emploi comme TabNet, Transformer), et le backtester vectorisé orienté Machine Learning.
- **Ce qui apporte une valeur directe :** Le moteur de backtest ML et le Portfolio Optimizer, infiniment supérieurs à une implémentation maison.
- **Ce qui est inutile/à ignorer :** Les outils de scraping/data collector de Qlib (Aegis utilisera OpenBB pour ça). L'exécution en direct (Live Trading) qui n'est pas le point fort de Qlib.

### 2.4 Stratégie d'Intégration
- **Mode :** **Service/Moteur de Recherche (Research Engine)**
- **Justification :** Qlib est trop lourd pour être un simple module. Aegis doit orchestrer des expériences Qlib en lui fournissant les données (via OpenBB) et en récupérant les signaux générés. Aegis agit comme le *Runner* de Qlib.

### 2.5 Composants Retenus
- `qlib.data` (Conversion Parquet -> Format binaire Qlib)
- `qlib.workflow` (Expérimentation ML)
- `qlib.backtest` (Génération des rendements ML)
- `Model Zoo` (Modèles pré-entraînés).

### 2.6 Composants Exclus
- `qlib.data.dataset.processor` pour l'ingestion brute en ligne (délégué à OpenBB).
- `RD-Agent` (Aegis a son propre Council multi-agents).

### 2.7 Dépendances
- **Python :** `pyqlib`, `lightgbm`, `pytorch`.
- **Système :** C++ build tools (nécessaires pour le format binaire).
- **Risques :** L'installation de `pyqlib` peut être capricieuse sous Windows (nécessite parfois WSL ou Docker). Coût de maintenance moyen lié à l'environnement.

### 2.8 Position dans Aegis
- **Couche :** **Research & AI Backtesting**
- **Rôle :** Moteur de calcul d'Alpha et d'optimisation de portefeuille basé sur l'IA.

### 2.9 Interactions
- `Aegis DatasetEngine (Parquet)` -> `Qlib Binary Store` -> `Qlib Model Training` -> `Alpha Signals` -> `Aegis Decision Engine`.

### 2.10 Sprint d'intégration
- **Priorité :** P1
- **Sprint cible :** Sprint ML & Alpha.
- **Prérequis :** `AEGIS_DATA_DIR` configuré et Pipeline de conversion Parquet-vers-QlibBin.

---

## 3. vn.py (VeighNa)

### 3.1 Présentation
- **Objectif :** Framework de trading quantitatif institutionnel open-source (gestion d'événements, connectivité courtiers).
- **Cas d'usage :** Live trading, exécution des ordres, gestion des connexions WebSocket/FIX avec les bourses (Binance, Interactive Brokers, CTP).
- **Maturité :** Grade institutionnel. Standard de l'industrie pour la connectivité, particulièrement sur les marchés asiatiques et cryptos.
- **Activité :** Très active, maintenue par VeighNa, versions régulières.

### 3.2 Architecture
- **Couches :**
  - *EventEngine* : Le cœur du système (Nervous System). Basé sur un pattern Reactor, il distribue les événements (ticks, ordres, logs) de manière asynchrone avec une latence microseconde.
  - *MainEngine* : Le cerveau (Central Coordinator) qui gère le cycle de vie des modules et injecte les dépendances.
  - *Gateways* : Ponts C++/Python traduisant les API spécifiques des courtiers vers le format interne de vn.py.
- **Interfaces :** Python (PyQt pour l'UI, scripts via `run.py`).

### 3.3 Analyse Critique
- **Ce qui est excellent :** L'implémentation C++/Python des Gateways et la robustesse de l'`EventEngine` face à des milliers d'événements par seconde.
- **Ce qui apporte une valeur directe :** La standardisation des API de courtage. Aegis n'a plus besoin de maintenir ses propres connecteurs Binance ou IBKR.
- **Ce qui est inutile/à ignorer :** Toute l'interface graphique (PyQt), la gestion de base de données intégrée (Aegis gère son propre datalake Parquet), et le moteur de backtest CTA de vn.py.

### 3.4 Stratégie d'Intégration
- **Mode :** **Bibliothèque via Adaptateur**
- **Justification :** vn.py est un "tuyau" vers les courtiers. Aegis doit encapsuler le `MainEngine` et l'`EventEngine` dans un adaptateur d'infrastructure. Les décisions du *Decision Engine* d'Aegis seront traduites en ordres vn.py natifs.

### 3.5 Composants Retenus
- `vnpy.event` (EventEngine)
- `vnpy.trader.engine` (MainEngine)
- `vnpy.gateway.*` (Les gateways nécessaires : Binance, IBKR, etc.)
- Modèles de données de trading (`OrderRequest`, `CancelRequest`).

### 3.6 Composants Exclus
- `vnpy.app.*` (UI, CTA Strategy, DataRecorder).
- `vnpy.database` (Gestion BDD ignorée au profit d'Aegis Parquet).

### 3.7 Dépendances
- **Python :** `vnpy`, `vnpy_binance`, etc.
- **Système :** Compilateurs C++ (cl.exe sous Windows) nécessaires pour compiler certaines dépendances si les wheels manquent.
- **Risques :** L'installation sous Windows peut être complexe (dépendances C++ strictes). Le couplage fort avec leur modèle de données nécessite un Adaptateur Anti-Corruption strict dans Aegis.

### 3.8 Position dans Aegis
- **Couche :** **Execution Layer (OMS)**
- **Rôle :** Moteur d'exécution des ordres (Order Management System) et de récupération des Ticks en direct.

### 3.9 Interactions
- `Aegis Decision Engine` -> `Aegis-vnpy Adapter` -> `vn.py MainEngine` -> `Gateway` -> `Broker`.
- `Broker` -> `Gateway` -> `vn.py EventEngine` -> `Aegis-vnpy Adapter` -> `Aegis Portfolio/Risk Analyst`.

### 3.10 Sprint d'intégration
- **Priorité :** P2
- **Sprint cible :** Sprint Live Execution.
- **Prérequis :** Architecture Hexagonale validée (Pattern Adaptateur implémenté).

---

## 4. Zipline (zipline-reloaded)

### 4.1 Présentation
- **Objectif :** Bibliothèque de trading algorithmique et de backtesting événementiel, initialement développée par Quantopian.
- **Cas d'usage :** Backtesting pas-à-pas (tick par tick ou jour par jour) de stratégies quantitatives classiques.
- **Maturité :** Historique (Le standard Python original). Repris par la communauté via le fork `zipline-reloaded`.
- **Activité :** Modérée à active (`zipline-reloaded` maintient la compatibilité avec Pandas 2.x et Python 3.11+).

### 4.2 Architecture
- **Couches :**
  - *Data Bundles* : Moteur d'ingestion (ETL) très rigide basé sur SQLite/Bcolz (historiquement).
  - *Trading Algorithm* : Boucle événementielle (`handle_data`, `before_trading_start`).
  - *Metrics & Risk* : Calculs de performance (Pyfolio).
  - *Exchange Calendars* : Gestion des jours fériés et horaires d'ouverture (maintenant un package autonome).
- **Interfaces :** Scripting via l'objet `TradingAlgorithm`.

### 4.3 Analyse Critique
- **Ce qui est excellent :** La gestion des calendriers boursiers (qui gère parfaitement les demi-journées et jours fériés mondiaux) et la logique comptable du backtest.
- **Ce qui apporte une valeur directe :** Uniquement les modules écosystémiques isolés comme `exchange_calendars`.
- **Ce qui est inutile/à ignorer :** Le moteur de backtest complet. Les `data bundles` sont trop rigides et incompatibles avec notre architecture Parquet/Qlib. Zipline est trop lent par rapport aux backtests vectorisés (Qlib) pour l'IA, et redondant avec le moteur événementiel léger d'Aegis (Sprint 1).

### 4.4 Stratégie d'Intégration
- **Mode :** **Inspiration uniquement (et Partielle)**
- **Justification :** Le couplage avec le moteur central de Zipline détruirait l'agilité d'Aegis. Nous rejetons le moteur de backtest (trop rigide, obsolète pour le ML) mais récupérons les briques périphériques extrêmement fiables (calendriers).

### 4.5 Composants Retenus
- `exchange_calendars` (Package devenu autonome, essentiel pour éviter le look-ahead bias le week-end).
- Concept comptable d'équité et de P&L (inspiration mathématique).

### 4.6 Composants Exclus
- `zipline.data.bundles` (Rejeté).
- `zipline.algorithm` (Rejeté, Aegis a son `EventEngine` via vn.py pour le live, et Qlib pour le backtest).
- Le moteur de simulation boursier interne.

### 4.7 Dépendances
- **Python :** `exchange_calendars` (nécessite `pandas >= 2.2.2`).
- **Risques :** Risque nul si on se limite à `exchange_calendars`. Si on intégrait le cœur, le risque de "dependency hell" (conflits SQLAlchemy/Pandas) serait massif.

### 4.8 Position dans Aegis
- **Couche :** **Infrastructure Utilities**
- **Rôle :** Fournisseur des contraintes temporelles (horaires d'ouverture, jours fériés) pour l'alignement des données et le déclenchement des agents.

### 4.9 Interactions
- `Aegis DatasetEngine` -> `exchange_calendars` (pour filtrer les NaN sur les jours de fermeture).
- `CouncilOrchestrator` -> `exchange_calendars` (pour ne pas tourner le week-end).

### 4.10 Sprint d'intégration
- **Priorité :** P3
- **Sprint cible :** Sprint Utilities / Datasets.
- **Prérequis :** Aucun.

---

## 5. FinGPT

### 5.1 Présentation
- **Objectif :** Démocratiser l'accès aux LLMs financiers via l'open-source (modèles fine-tunés, pipelines RAG, datasets).
- **Cas d'usage :** Analyse de sentiment sur les actualités financières (News), extraction de relations causales depuis les rapports (SEC filings), robo-advising.
- **Maturité :** État de l'art académique et open-source. Soutenu par la fondation AI4Finance.
- **Activité :** Très active. Adaptation rapide aux nouveaux modèles fondationnels (intégration de Llama 3).

### 5.2 Architecture
- **Couches :**
  - *Data Sources & FinNLP* : Pipelines de scraping et nettoyage (Reuters, SEC, Twitter).
  - *LLMs (Fine-Tuning)* : Méthodes LoRA (Low-Rank Adaptation) pour adapter Llama 3 au domaine financier.
  - *RAG (Retrieval-Augmented Generation)* : Injection de contexte en temps réel pour éviter les hallucinations.
- **Interfaces :** HuggingFace Models (`FinGPT/fingpt-mt_llama3-8b_lora`), GitHub scripts.

### 5.3 Analyse Critique
- **Ce qui est excellent :** L'approche "Data-centric". FinGPT comprend que les poids du modèle comptent moins que la qualité du dataset d'entraînement. Leur pipeline FinNLP et leurs modèles LoRA sur Llama 3 sont remarquables.
- **Ce qui apporte une valeur directe :** Les poids des modèles (weights) hébergés sur HuggingFace que l'on peut télécharger et faire tourner via Ollama, et les datasets FinNLP pour l'ingestion des News.
- **Ce qui est inutile/à ignorer :** L'interface utilisateur ou les scripts de déploiement cloud (Aegis tourne en architecture locale / orchestrateur).

### 5.4 Stratégie d'Intégration
- **Mode :** **Service Externe / Bibliothèque (Modèles et Datasets)**
- **Justification :** Aegis n'a pas vocation à fine-tuner ses propres LLMs. Nous allons utiliser FinGPT comme source de modèles (ex: `fingpt-llama3`) à charger dans notre infrastructure `OllamaClient`, et FinNLP comme bibliothèque d'ingestion pour le `NewsAnalyst`.

### 5.5 Composants Retenus
- Les modèles HuggingFace (ex: `fingpt-mt_llama3-8b_lora`).
- Le module `FinNLP` pour l'acquisition et le formatage des flux d'actualités.
- L'approche RAG (architecture conceptuelle pour injecter des rapports macro/micro dans les prompts).

### 5.6 Composants Exclus
- Les pipelines de training et fine-tuning (LoRA scripts).
- Les benchmarks (inutiles en production).

### 5.7 Dépendances
- **Python :** `finnlp`.
- **Système :** Ollama (pour héberger les poids GGUF dérivés de FinGPT), HuggingFace Hub.
- **Risques :** L'adaptation des modèles au format GGUF pour Ollama peut nécessiter des conversions manuelles (`llama.cpp`). Modéré.

### 5.8 Position dans Aegis
- **Couche :** **Research Council (Intelligence Layer)**
- **Rôle :** Fournir le "cerveau" spécialisé (modèle) pour les analystes fondamentaux et sentiment (ex: `NewsAnalyst`, `FundamentalAnalyst`).

### 5.9 Interactions
- `FinNLP` -> `Aegis DatasetEngine` -> `AgentRunner` (hydration de prompt) -> `OllamaClient (FinGPT Model)`.

### 5.10 Sprint d'intégration
- **Priorité :** P1
- **Sprint cible :** Sprint Intelligence (Multi-Agents).
- **Prérequis :** Convertir les poids de FinGPT-Llama3 en GGUF pour Ollama local.

---

## 6. TradingAgents & AutoHedge

### 6.1 Présentation
- **Objectif :** Frameworks d'orchestration multi-agents LLM dédiés au trading. (TradingAgents par TauricResearch : focus recherche institutionnelle et débats. AutoHedge par The Swarm Corp : focus exécution autonome "Swarm intelligence").
- **Cas d'usage :** Décomposition d'un hedge fund en rôles LLM (Analyste, Quant, Risk Manager, Fund Manager) interagissant pour prendre une décision.
- **Maturité :** Expérimentale à avancée (AutoHedge s'approche du Live Trading sur crypto).
- **Activité :** Très surveillée, architecture à la mode (LangGraph, AutoGen).

### 6.2 Architecture
- **Couches :**
  - *Persona Design* : Prompt engineering assignant des outils et contraintes précis.
  - *Orchestrator* : Moteur de résolution des conflits (débat Bull vs Bear dans TradingAgents) basé sur LangGraph ou architectures de graphes.
  - *Gatekeepers* : Agents de risque bloquant les trades illégitimes (AutoHedge).
- **Interfaces :** Scripts Python monolithiques.

### 6.3 Analyse Critique
- **Ce qui est excellent :** Le design des Personas (rôles ultra-spécialisés limitant les hallucinations) et la mécanique de débat structuré (Chain-of-Thought forcé inter-agents).
- **Ce qui apporte une valeur directe :** L'ingénierie des prompts (Persona, Toolset, Output strict JSON) pour structurer nos propres analystes Aegis (Phase 3).
- **Ce qui est inutile/à ignorer :** Les orchestrateurs natifs (LangGraph, Swarm). Aegis a validé son propre `CouncilOrchestrator` orienté DTOs immuables (Mission G). Les implémentations de ces projets sont souvent trop dépendantes d'OpenAI et souffrent de problèmes de scalabilité (boucles infinies d'agents).

### 6.4 Stratégie d'Intégration
- **Mode :** **Inspiration uniquement**
- **Justification :** Conserver la souveraineté sur l'Orchestrateur est vital. Utiliser LangGraph ajouterait un couplage massif et un risque de non-déterminisme. Le `CouncilOrchestrator` propriétaire d'Aegis, 100% testable en TDD (Mission G), garantit la fiabilité. Nous volons uniquement leurs meilleures idées de "Prompt Design" et de mécanique de débat.

### 6.5 Composants Retenus
- Structure de prompt : Objectif, Rôle, Format JSON strict.
- Mécanique de résolution : Un agent `CouncilSynthesizer` tranchant les avis de N analystes spécialisés.

### 6.6 Composants Exclus
- Moteurs de graphes (LangGraph).
- Dépendances directes aux API OpenAI.
- Couches d'exécution (Aegis utilise vn.py).

### 6.7 Dépendances
- **Python :** Aucune (Inspiration pure).
- **Risques :** Nul (aucun code importé).

### 6.8 Position dans Aegis
- **Couche :** **Research Council**
- **Rôle :** Patron de conception (Design Pattern) pour la rédaction des fichiers `prompts/*.md`.

### 6.9 Interactions
- Inspiration conceptuelle pour la méthode `synthesize()` du `CouncilSynthesizer` d'Aegis.

### 6.10 Sprint d'intégration
- **Priorité :** P1
- **Sprint cible :** Sprint Intelligence (Multi-Agents).
- **Prérequis :** Implémentation du système de Télémétrie LLM (déjà amorcé en Mission G).

---

## 7. AkShare

### 7.1 Présentation
- **Objectif :** Bibliothèque Python open-source massive pour la collecte de données financières (API HTTP / Web Scraping).
- **Cas d'usage :** Accès prioritaire aux données du marché chinois (A-shares, macro-économie asiatique, dérivés, contrats à terme) et agrégation de sources alternatives (Sina, East Money).
- **Maturité :** Standard de facto pour l'écosystème quantitatif asiatique.
- **Activité :** Extrêmement active, mises à jour quasi-quotidiennes pour maintenir les connecteurs de scraping face aux changements des sites web.

### 7.2 Architecture
- **Couches :**
  - *Scraping/API Wrappers* : Centaines de fonctions isolées tapant sur des terminaux web publics ou APIs ouvertes.
  - *AKTools* : Wrapper HTTP optionnel pour exposer AkShare en REST.
- **Interfaces :** Python native (`import akshare as ak`).

### 7.3 Analyse Critique
- **Ce qui est excellent :** La profondeur inégalée sur les marchés asiatiques, la macroéconomie et les contrats à terme, le tout gratuitement.
- **Ce qui apporte une valeur directe :** Un fallback (plan B) data robuste si Aegis étend son univers d'investissement hors de l'Occident.
- **Ce qui est inutile/à ignorer :** La redondance avec OpenBB sur les marchés US/Crypto. La fragilité inhérente au web-scraping (les fonctions peuvent casser sans préavis).

### 7.4 Stratégie d'Intégration
- **Mode :** **Bibliothèque via Adaptateur (Optionnel/Fallback)**
- **Justification :** OpenBB couvre notre besoin prioritaire (Macro US, Yahoo, FRED). AkShare ne sera branché que via un `AkShareAdapter` au sein du `DatasetEngine` si la stratégie pivote (ex: CSI 300, matières premières de Shanghai). L'isolation via l'adaptateur protégera le cœur d'Aegis de la fragilité de ces requêtes.

### 7.5 Composants Retenus
- `akshare.stock_zh_a_*` (Fonctions spécifiques actions A-Share).
- `akshare.macro_china_*` (Indicateurs macro asiatiques).

### 7.6 Composants Exclus
- `AKTools` (Aegis gère sa propre architecture).
- Toutes les requêtes US/Crypto (déjà couvertes proprement par l'architecture institutionnelle d'OpenBB).

### 7.7 Dépendances
- **Python :** `akshare`, `akshare-one`.
- **Risques :** Risque très élevé de cassure des endpoints car il repose partiellement sur du scraping non officiel. Coût de maintenance potentiellement lourd si utilisé en production critique.

### 7.8 Position dans Aegis
- **Couche :** **Data Infrastructure (Ingestion)**
- **Rôle :** Fournisseur de données secondaire / régional (Asie).

### 7.9 Interactions
- `AkShare` -> `AkShareAdapter` -> `Aegis DatasetEngine`.

### 7.10 Sprint d'intégration
- **Priorité :** P3
- **Sprint cible :** Sprint Expansion Marchés (Ultérieur).
- **Prérequis :** Implémentation complète et validée du `DatasetEngine` avec OpenBB.

---

## 8. Fincept Terminal

### 8.1 Présentation
- **Objectif :** Plateforme d'intelligence financière de niveau institutionnel (C++20/Qt6).
- **Cas d'usage :** Environnement de bureau (GUI) complet pour le trading, avec modules de pricing (QuantLib) et exécution (16 brokers).
- **Maturité :** Projet C++ natif visant des performances ultra-basses latences pour l'utilisateur final.
- **Activité :** Maintenu par Fincept Corporation.

### 8.2 Architecture
- **Couches :**
  - *Core C++* : UI Qt6, modules QuantLib.
  - *Embedded Python Engine* : Pour l'exécution de scripts IA/Quant depuis l'interface utilisateur.
- **Interfaces :** GUI Desktop native (C++).

### 8.3 Analyse Critique
- **Ce qui est excellent :** Les performances natives C++ et l'intégration profonde des outils quantitatifs dans une seule interface unifiée.
- **Ce qui apporte une valeur directe :** Une inspiration sur la manière dont une UI professionnelle structure ses modules de risque.
- **Ce qui est inutile/à ignorer :** La quasi-totalité du projet. Aegis Quant OS est un système **Headless** (Backend), conçu pour tourner sur des serveurs, en tâche de fond, piloté par l'IA de manière autonome. Nous ne développerons pas de Desktop GUI lourde.

### 8.4 Stratégie d'Intégration
- **Mode :** **Ignoré (Inspiration très ciblée)**
- **Justification :** Importer une interface Qt6 ou un moteur GUI détruirait l'objectif "Meta-Orchestrator Headless" d'Aegis. La visualisation des performances d'Aegis se fera plus tard via des dashboards web légers (Streamlit, Dash) interrogeant les fichiers Parquet, pas via un terminal client lourd.

### 8.5 Composants Retenus
- Aucun code.

### 8.6 Composants Exclus
- La totalité du projet et son interface graphique.

### 8.7 Dépendances
- **Python :** Aucune.
- **Risques :** Nul.

### 8.8 Position dans Aegis
- **Couche :** Aucune (Hors périmètre).
- **Rôle :** Anti-modèle pour l'Interface Utilisateur (Nous restons Backend/Headless).

### 8.9 Interactions
- Aucune.

### 8.10 Sprint d'intégration
- **Priorité :** Non applicable.
- **Sprint cible :** Aucun.
- **Prérequis :** Aucun.

---

## 9. Awesome Quant

### 9.1 Présentation
- **Objectif :** La liste de curation ultime de bibliothèques et ressources pour la finance quantitative (`wilsonfreitas/awesome-quant` et `leoncuhk/awesome-quant-ai`).
- **Cas d'usage :** Recherche de bibliothèques mathématiques, backtesters, ou parsers de protocoles financiers.
- **Maturité :** Standard historique de la communauté GitHub.

### 9.2 Architecture
- Document Markdown (`README.md`).

### 9.3 Analyse Critique
- **Ce qui est excellent :** La catégorisation structurée (Numerical Libraries, Trading Frameworks, Data).
- **Ce qui apporte une valeur directe :** Un filet de sécurité technique. Si vn.py ou Qlib devaient mourir ou devenir obsolètes, ce dépôt fournit immédiatement l'alternative (ex: nautilus_trader, riskfolio-lib).

### 9.4 Stratégie d'Intégration
- **Mode :** **Inspiration uniquement (Méta-Gouvernance)**
- **Justification :** C'est un outil de veille, pas un outil logiciel.

### 9.5 Composants Retenus
- La veille technologique pour les Sprints de R&D futurs.

### 9.6 Composants Exclus
- N/A.

### 9.7 Dépendances
- N/A.

### 9.8 Position dans Aegis
- **Couche :** Gouvernance du projet.
- **Rôle :** Dictionnaire de substitution technologique.

### 9.9 Interactions
- N/A.

### 9.10 Sprint d'intégration
- **Priorité :** P0 (Continu).
- **Sprint cible :** R&D permanente.
- **Prérequis :** N/A.

## 10. MATRICE D'INTÉGRATION

Le tableau suivant récapitule le statut de chaque composant évalué vis-à-vis du noyau Aegis Quant OS.

| Composant | Couche Cible | Rôle | Mode d'Intégration | Priorité | Sprint |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **OpenBB (v4)** | Data Infrastructure | Ingestion / Data Lake | Bibliothèque Core (Data Layer) | P0 | Sprint Data |
| **Qlib** | Research & AI | Backtest / Alpha Model | Service / Research Engine | P1 | Sprint ML & Alpha |
| **vn.py** | Execution (OMS) | Routage Ordres / Ticks | Bibliothèque via Adaptateur | P2 | Sprint Live Exec |
| **FinGPT** | Research Council | Modèles LLM / FinNLP | Service Externe (Ollama) | P1 | Sprint IA |
| **TradingAgents** | Research Council | Design Pattern | Inspiration uniquement | P1 | Sprint IA |
| **AutoHedge** | Research Council | Gatekeepers | Inspiration uniquement | P1 | Sprint IA |
| **exchange_cal..**| Infra Utilities | Filtrage Temporel | Bibliothèque Core (Partielle) | P3 | Sprint Utilities |
| **AkShare** | Data Infrastructure | Données Asie (Fallback)| Bibliothèque via Adaptateur | P3 | Sprint Expansion |
| **Fincept** | UI / Desktop | N/A | **Ignoré** (Anti-modèle) | N/A | N/A |
| **Awesome Quant**| Méta-Gouvernance | Dictionnaire fallback | Inspiration (Veille) | P0 | Continu |

---

## 11. ARCHITECTURE CIBLE (Méta-Orchestrateur)

Aegis Quant OS est le "cerveau" qui orchestre l'écosystème open-source. Aegis délègue l'ingestion, le backtest et l'exécution aux outils de pointe, mais conserve la gouvernance totale (Council) et le modèle de données (Parquet/DTOs).

```text
========================================================================================
                          AEGIS QUANT OS (Méta-Orchestrateur)
========================================================================================

[SOURCES EXTERNES]                                                   [MARCHÉS / BROKERS]
      │                                                                       ▲
      ▼                                                                       │
┌─────────────┐       ┌─────────────────────────────────────┐         ┌───────────────┐
│  OpenBB v4  │──────▶│             DATA ENGINE             │         │ vn.py (VeighNa)
│ (Ingestion) │       │ (Parquet Datalake, Standardisation) │         │ (Execution OMS)
└─────────────┘       └─────────────────────────────────────┘         └───────────────┘
      │                                 │                                     ▲
      │ (Fallback/Asie)                 ▼                                     │
┌─────────────┐       ┌─────────────────────────────────────┐         ┌───────────────┐
│   AkShare   │       │           RESEARCH COUNCIL          │         │AEGIS ADAPTER  │
│(Via Adapter)│       │ (Ollama + FinGPT Models + FinNLP)   │         │(Anti-Corrupt) │
└─────────────┘       │ 1. Analystes (News, Macro, Risk)    │         └───────────────┘
                      │ 2. Débats & Synthèse (Synthesizer)  │                 ▲
                      └─────────────────────────────────────┘                 │
                                        │                                     │
┌─────────────┐                         ▼                                     │
│exchange_cal.│       ┌─────────────────────────────────────┐                 │
│(Time Filter)│──────▶│           DECISION ENGINE           │─────────────────┘
└─────────────┘       │ (Trade Generation, Position Sizing) │
                      └─────────────────────────────────────┘
                                        │
┌─────────────┐                         ▼
│    Qlib     │       ┌─────────────────────────────────────┐
│ (Backtest)  │◀──────│           PORTFOLIO ENGINE          │
└─────────────┘       │ (Risk constraints, Metrics, P&L)    │
                      └─────────────────────────────────────┘
```

**Légende :**
- **Boîtes Centrales :** Code exclusif Aegis Quant OS.
- **Boîtes Périphériques :** Écosystème Open-Source audité dans ce Blueprint.
- **Flux (Flèches) :** Dépendance directionnelle (Aegis appelle l'outil, ou les données coulent vers Aegis).
