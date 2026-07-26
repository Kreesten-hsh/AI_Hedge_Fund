# Providers Roadmap

Ce document répertorie tous les fournisseurs (Data, ML, Brokers, LLMs) qu'Aegis Quant OS intègre ou prévoit d'intégrer. Chaque fournisseur est isolé derrière un *Adapter* strict (Clean Architecture).

---

## 1. Data Providers (Market Data & Alternatifs)

### OpenBB
- **Statut** : PLANNED
- **Priorité** : Critique
- **Utilisation** : Source principale (gratuite et open-source) pour les données macro-économiques, les fondamentaux et les cours End-Of-Day (EOD).
- **Dépendances** : Data Pipeline (Phase 4).
- **Alternatives** : Yahoo Finance (instable), AlphaVantage.

### Polygon.io
- **Statut** : BACKLOG
- **Priorité** : Moyenne
- **Utilisation** : Source premium pour les données intra-day de haute qualité et le flux WebSocket en direct.
- **Dépendances** : Execution Engine en temps réel.
- **Alternatives** : Alpaca Market Data, IBKR Data.

---

## 2. Brokers & Exécution

### vn.py
- **Statut** : PLANNED (Adapter partiel existant)
- **Priorité** : Critique
- **Utilisation** : Gateway de trading multi-marchés. Utilisé pour standardiser les API des courtiers et gérer les connexions CTP/Crypto/Traditionnelles.
- **Dépendances** : Execution Engine (Phase 6).
- **Alternatives** : CCXT (Crypto uniquement), MetaTrader 5.

### Interactive Brokers (TWS API)
- **Statut** : BACKLOG
- **Priorité** : Moyenne (Vise le marché institutionnel/pro)
- **Utilisation** : Broker cible pour le Live Trading sur actions et options américaines.
- **Dépendances** : vn.py IB Gateway.
- **Alternatives** : Alpaca, TD Ameritrade.

---

## 3. Machine Learning & Features

### Qlib (Microsoft)
- **Statut** : PLANNED (Adapter partiel existant)
- **Priorité** : Haute
- **Utilisation** : Génération d'alphas, backtesting de modèles ML (LightGBM, LSTM), gestion de datasets complexes.
- **Dépendances** : Feature Engine (Phase 4).
- **Alternatives** : Zipline (obsolète), Backtrader (lent).

### FinGPT
- **Statut** : BACKLOG
- **Priorité** : Basse (Recherche)
- **Utilisation** : Analyse de sentiment avancée sur les news financières et les réseaux sociaux.
- **Dépendances** : Feature Engine.
- **Alternatives** : BERT fine-tuné maison.

---

## 4. Large Language Models (LLMs)

### Ollama (Local)
- **Statut** : READY
- **Priorité** : Critique (Déjà implémenté)
- **Utilisation** : Inférence locale à coût zéro pour les tâches rapides (Risk Analyst, Technical Analyst). Garantit la confidentialité.
- **Dépendances** : Aucune.
- **Alternatives** : Llama.cpp, LM Studio.

### OpenAI (GPT-4o) / Anthropic (Claude 3.5)
- **Statut** : PLANNED
- **Priorité** : Moyenne
- **Utilisation** : Modèles Cloud réservés aux tâches d'analyse profonde (Macro Analyst, Fundamental Analyst) nécessitant un raisonnement complexe.
- **Dépendances** : Architecture asynchrone du Council (Phase 7).
- **Alternatives** : Google Gemini.
