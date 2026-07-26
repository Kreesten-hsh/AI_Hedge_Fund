# Aegis Quant OS 🛡️📈

![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Build](https://img.shields.io/badge/build-passing-brightgreen)
![Architecture](https://img.shields.io/badge/architecture-Clean%20%7C%20Hexagonal-orange)

**Aegis Quant OS** est un système de trading quantitatif personnel (Operating System) piloté par Intelligence Artificielle. Il a pour vocation de centraliser l'ingestion de données de marché, de simuler et gérer un portefeuille, d'exécuter des stratégies via des brokers, et d'orchestrer un panel d'agents IA (AI Council) pour formuler des décisions de marché complexes.

Conçu avec les principes du **Domain-Driven Design (DDD)** et de la **Clean Architecture**, Aegis garantit une stricte séparation entre sa logique de trading, ses moteurs de risque, et ses fournisseurs d'infrastructure (LLMs, Bases de données, Brokers).

> ⚠️ **Note** : Aegis Quant OS est strictement un outil personnel. Il n'intègre aucune fonctionnalité SaaS, de gestion multi-utilisateur ou de facturation.

## 🚀 Fonctionnalités Principales

- **Architecture Hexagonale & DDD** : Le domaine financier (Assets, Positions, Trades, Signaux) est isolé de toute dépendance tierce.
- **AI Council** : Un orchestrateur multi-agents permettant d'interroger plusieurs LLMs simultanément (ex: Macro Analyst, Risk Analyst, Technical Analyst) et de synthétiser leurs rapports en une décision unique.
- **LLM Abstraction & Decision Cache** : L'OS s'interface avec n'importe quel LLM via des *Adapters* (Ollama supporté nativement) et met en cache de façon déterministe les délibérations pour optimiser les performances (SHA-256).
- **Risk-First Engine** : Contrôle absolu sur le capital avec limites d'exposition et vérifications globales avant toute exécution d'ordre.
- **Event-Driven Bus** : Communication inter-composants asynchrone réduisant le couplage.

## 🛠️ Technologies et Frameworks

- **Langage** : Python 3.11 (Requis)
- **Configuration** : `PyYAML`
- **Tests** : `pytest`, `unittest.mock`
- **Providers Cibles** : `Ollama` (LLM), `OpenBB` (Data), `Qlib` (Machine Learning), `vn.py` (Broker Gateway)

## ⚙️ Prérequis Système

- **Python 3.11** (Strictement requis, les versions supérieures peuvent casser la compatibilité des bibliothèques quantitatives C-extensions).
- **Ollama** (Recommandé en local pour l'exécution des modèles sans surcoût API).
- Git.

## 📦 Installation et Configuration

1. **Cloner le dépôt** :
   ```bash
   git clone https://github.com/votre-username/AegisQuantOS.git
   cd AegisQuantOS
   ```

2. **Créer et activer un environnement virtuel** :
   - Sur Windows :
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - Sur macOS/Linux :
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```

3. **Installer les dépendances** :
   ```bash
   pip install -r requirements.txt
   ```
   *(Assurez-vous que `PyYAML` et `pytest` font partie de vos dépendances).*

4. **Configurer l'infrastructure LLM** :
   Modifiez le fichier de configuration principal `config/llm.yaml` selon vos ressources (exemple avec un profil local) :
   ```yaml
   llm:
     active_profile: "standard"
     profiles:
       standard:
         provider: "ollama"
         model: "llama3.1"
         temperature: 0.1
         timeout: 120
         keep_alive: 0
   ```

5. **Lancer les tests** :
   Vérifiez l'intégrité de l'environnement avec la suite complète de tests :
   ```bash
   pytest -v
   ```

## 💻 Exemples d'Utilisation

### Lancement du AI Council (Prise de décision synthétique)
Le script `run_council_consensus.py` illustre l'intégration de la Clean Architecture. Le `LLMProviderFactory` injecte le fournisseur de modèle configuré dans l'orchestrateur de l'IA.

```bash
python scripts/run_council_consensus.py
```
*Le système instanciera les agents (Macro, Risque, Fondamental), passera le contexte du marché aux modèles, récupérera les rapports asynchrones, et formulera la décision via le Synthesizer.*

### Backtest Simplifié (Ai Decision Engine)
Évaluez des règles métiers simulées via le moteur de backtest :
```bash
python scripts/run_ai_backtest.py
```

## 🏗️ Structure du Projet

L'arborescence respecte la ségrégation des Bounded Contexts :

```
AegisQuantOS/
├── config/                  # Fichiers YAML de configuration de l'infrastructure
├── docs/                    # Documentation officielle, ADRs, et Roadmaps
├── prompts/                 # Prompts Markdown pour le paramétrage des Agents LLM
├── scripts/                 # Points d'entrée pour lancer le système (Backtest, Live)
├── src/aegis_trade/
│   ├── agents/              # Orchestration des LLMs (Council, Runner, Analystes)
│   ├── core/                # Bus d'événements et exceptions
│   ├── dataset/             # Moteur de chargement des données (MarketBars)
│   ├── domain/              # Objets de domaine (Trades, Positions)
│   ├── engine/              # Logique métier (Portfolio, Global Risk, AI Decision)
│   ├── infrastructure/      # Implémentations techniques (Cache, Logging, LLM Factory)
│   ├── providers/           # Adaptateurs pour services externes (vn.py, Qlib, mt5)
│   ├── strategies/          # Logiques algorithmiques pures
│   └── utils/               # Outils transversaux
└── tests/                   # Suite de tests unitaires (pytest)
```

## 📚 Documentation Additionnelle

Aegis Quant OS est documenté exhaustivement pour sa maintenance à long terme. Consultez le répertoire `docs/` pour :
- **[La Vision et l'Objectif du Système](docs/VISION.md)**
- **[L'Architecture Globale et les Flux](docs/SYSTEM_ARCHITECTURE.md)**
- **[L'Analyse des Écarts et la Feuille de Route](docs/PRODUCT_ROADMAP.md)**
- **[Les Architecture Decision Records (ADRs)](docs/ADR/)**

---
*Aegis Quant OS — Risk First, Always.*
