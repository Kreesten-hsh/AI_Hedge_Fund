# Audit d'Intégration GitHub - Guide Définitif (Deep Audit)

Ce document détaille l'audit technique de chaque dépôt (actif et inspirationnel) pour l'intégration dans Aegis Quant OS. 

---

### `vnpy`
**Rôle :** Broker Adapter et Gateway.
**Justification :** Framework HFT industriel en C++/Python, évite de réécrire la connectivité bas niveau FIX ou REST avec les brokers. Couche d'exécution pure.

### `ta`
**Rôle :** Calcul des indicateurs techniques (RSI, MACD, ATR, EMA, VWAP).
**Justification :** Requis par `FEATURE_ENGINEERING.md`. Fournit des calculs d'indicateurs vectorisés ultra-rapides sans réinventer la roue, crucial pour maintenir la latence < 20 ms lors de la génération des Market Snapshots en direct.

## 4. Workflows GitHub Actionses et connectivité MT5/FIX.
- **Pourquoi ne pas le réécrire nous-mêmes ?** Refaire un connecteur MT5 asynchrone robuste en C++ prendrait 6 mois de R&D avec des risques de perte de paquets, ce qui est mortel en HFT.
- **Modules utilisés :** `vnpy.event`, `vnpy.gateway.mt5`, `vnpy.trader.object`.
- **Classes :** `EventEngine`, `Mt5Gateway`, `OrderRequest`, `TickData`.
- **Fonctions :** `subscribe()`, `send_order()`, `cancel_order()`.
- **Architecture :** Event-driven (Publish/Subscribe).
- **Ce que nous gardons :** Uniquement le pont de communication réseau (Le Gateway) et les Data Objects.
- **Ce que nous supprimons :** Toute l'interface graphique (`vnpy.ui`), les modules de backtest (`vnpy.app.cta_strategy`), l'ORM base de données.
- **Temps estimé (Intégration) :** 1 Sprint (Fait).
- **RAM :** < 200 MB.
- **CPU :** Faible (Boucle C++).
- **GPU :** Aucun.
- **Risques :** Conflit GIL Python / C++ si mal wrappé.
- **Alternatives :** MetaTrader5 lib native (synchrone, trop lente), CCXT (pour crypto uniquement).
- **Tests :** Mocking du flux réseau. Load testing (10 000 ticks/sec).

---

## 2. OpenBB (Niveau S - Data Source)
- **Pourquoi l'utiliser ?** Plateforme v4 centralisant +100 fournisseurs de données.
- **Pourquoi ne pas le réécrire nous-mêmes ?** Écrire et maintenir des API wrappers pour FRED, ECB, Yahoo, Binance, etc. est un métier à temps plein.
- **Modules utilisés :** `openbb-core`, `openbb-economy`, `openbb-crypto`.
- **Classes :** `OBBject`.
- **Fonctions :** `obb.economy.calendar()`, `obb.equity.price.historical()`.
- **Architecture :** Pydantic models + FastAPI architecture (Platform v4).
- **Ce que nous gardons :** Les fetchers asynchrones retournant des DataFrames Pandas.
- **Ce que nous supprimons :** Le CLI (`openbb-terminal`), l'UI.
- **Temps estimé :** 2 Semaines.
- **RAM :** 500 MB (Pandas cache).
- **CPU :** Modéré (Désérialisation JSON/Pydantic).
- **GPU :** Aucun.
- **Risques :** Rate limits des APIs gratuites, Latence réseau.
- **Alternatives :** YFinance (Trop instable), Pandas-Datareader (obsolète).
- **Tests :** Cache validation, Retry mechanisms sur timeout.

---

## 3. Qlib (Niveau S - Quant Lab)
- **Pourquoi l'utiliser ?** Standard Microsoft pour la génération de features quantitatives (Alpha158, Alpha360).
- **Pourquoi ne pas le réécrire nous-mêmes ?** Implémenter 158 formules mathématiques matricielles optimisées en C (Cython) prendrait des mois avec des risques d'erreurs mathématiques.
- **Modules utilisés :** `qlib.data.dataset`, `qlib.utils`.
- **Classes :** `DatasetH`, `ExpressionOps`.
- **Fonctions :** Extracteurs d'Alpha.
- **Architecture :** Data pipeline DAG (Directed Acyclic Graph).
- **Ce que nous gardons :** Le moteur de Feature Engineering.
- **Ce que nous supprimons :** Les modèles Deep Learning EOD (LightGBM, etc.) fournis par défaut, l'interface `Workflow`.
- **Temps estimé :** 3 Semaines.
- **RAM :** 4 GB.
- **CPU :** Extrêmement élevé (Calcul matriciel tensoriel).
- **GPU :** Aucun (ou CUDA pour certains ops).
- **Risques :** Conçu pour des données Journalières (Daily), doit être adapté au HFT.
- **Alternatives :** TA-Lib (Moins IA-friendly), Pandas-TA (Moins optimisé).
- **Tests :** Validation mathématique des outputs sur données statiques.

---

## 4. FinRL (Niveau S - Reinforcement)
- **Pourquoi l'utiliser ?** Implémente correctement PPO, SAC, DDPG pour des environnements Gym financiers.
- **Pourquoi ne pas le réécrire nous-mêmes ?** Écrire PPO de zéro est suicidaire (trop d'instabilité de convergence mathématique).
- **Modules utilisés :** Wrappers SB3 (Stable-Baselines3).
- **Classes :** `PPO` via `sb3_policy_adapter.py`.
- **Fonctions :** `train_policy()`, `predict()`.
- **Architecture :** Actor-Critic (RL).
- **Ce que nous gardons :** Uniquement la dépendance `stable-baselines3>=2.0.0`, `gymnasium>=0.29.0`, et l'algorithme PPO (CPU only).
- **Ce que nous supprimons :** Les environnements Gym par défaut de FinRL (actions Yahoo Finance), la fonction de récompense standard (PnL pur). L'installation globale de FinRL est évitée si possible pour limiter le bloat.
- **Temps estimé :** 4 Semaines (Fait - AI-04).
- **RAM :** 4 GB.
- **CPU :** Très élevé.
- **GPU :** Non (Machine cible CPU-only). PPO optimisé pour tourner sur CPU.
- **Risques :** Overfitting, Reward Hacking (l'IA triche au lieu d'apprendre).
- **Alternatives :** Ray RLlib (Plus puissant mais beaucoup trop complexe à configurer).
- **Tests :** Validation de convergence (Loss decrease), Backtest sur Holdout set.

---

## 5. Kronos (Niveau S - Forecasting)
- **Statut CTO :** En évaluation — variante mini uniquement, CPU.
- **Pourquoi l'utiliser ?** Modèle LLM pré-entraîné pour le forecasting Zero-Shot sur séries temporelles.
- **Pourquoi ne pas le réécrire nous-mêmes ?** Entraîner un LLM Time-Series demande un cluster de GPU H100 et des mois de compute.
- **Modules utilisés :** Inférence locale.
- **Classes :** `KronosForecaster` (wrapper à écrire).
- **Fonctions :** `predict(horizon=N)`.
- **Architecture :** Transformer.
- **Ce que nous gardons :** Les poids pré-entraînés et le script d'inférence.
- **Ce que nous supprimons :** Le pipeline d'entraînement distribué.
- **Temps estimé :** En évaluation (Hors chemin critique).
- **RAM :** ~2-4 GB pour Kronos-mini.
- **CPU :** Inférence CPU-only (batch asynchrone).
- **GPU :** Aucun (utilisation stricte de Kronos-mini, 4.1M paramètres, conçu pour environnements contraints CPU).
- **Risques :** Précision inférieure à la version base. À mesurer concrètement (MAPE/RMSE vs baseline naïve) avant de décider l'intégration complète.
- **Alternatives :** TimeGPT (Payant/SaaS - Refusé), ARIMA/GARCH (Trop statique).
- **Tests :** Comparaison MAPE/RMSE vs baseline naïve.

---

## 6. TradingAgents (Niveau A - Orchestration)
- **Pourquoi l'utiliser ?** Pour extraire la structure du débat entre agents (Quant vs Risk vs Macro).
- **Pourquoi ne pas le réécrire nous-mêmes ?** La logique de "State Graph" (qui parle à qui et quand) est déjà modélisée intelligemment ici.
- **Modules utilisés :** Modélisation LangGraph / AutoGen (Structure sémantique).
- **Classes :** Concept de `AgentNode`.
- **Ce que nous gardons :** La structure des prompts (Rôles) pour structurer le `Knowledge` dans le Reasoning Engine (AI-03).
- **Ce que nous supprimons :** Le code (Nous réécrivons en Python pur dans notre Domain).
- **Temps estimé :** 1 Semaine (Inspiration).
- **RAM/CPU/GPU :** N/A (Code natif).
- **Risques :** Sur-complexité si trop d'agents débattent.
- **Alternatives :** LangChain (Trop lourd), AutoGen (Microsoft).

---

## 7. AutoHedge (Niveau A - Orchestration)
- **Pourquoi l'utiliser ?** Mécanismes de hedging automatique pilotés par IA.
- **Ce que nous gardons :** Les règles métier (Comment un Risk Manager IA décide de couvrir une position perdante plutôt que de la fermer).
- **Ce que nous supprimons :** L'intégration broker.
- *(Similaire à TradingAgents pour l'intégration).*

---

## 8. lightweight-charts (Niveau A - Frontend)
- **Statut CTO :** Ni abandonné ni reporté — nécessaire, mais séquencé après la spécification du Dashboard (`DASHBOARD_FUNCTIONAL_SPECIFICATION.md`). Ne pas commencer l'intégration avant que le document de spécification du Dashboard soit validé.
- **Pourquoi l'utiliser ?** Rendu de centaines de milliers de bougies à 60 FPS.
- **Pourquoi ne pas le réécrire nous-mêmes ?** Recoder un moteur de rendu Canvas HTML5 optimisé pour la finance prendrait 1 an.
- **Modules utilisés :** NPM `lightweight-charts`.
- **Classes :** `createChart`, `addCandlestickSeries`.
- **Architecture :** Canvas WebGL.
- **Ce que nous gardons :** Tout le package NPM.
- **Ce que nous supprimons :** Rien.
- **Temps estimé :** En attente de validation spec.
- **RAM :** Client-side (Browser).
- **Risques :** Memory Leak JS si les séries ne sont pas nettoyées.
- **Alternatives :** Highcharts (Payant), Chart.js (Trop lent).

---

## 9. FinGPT (Niveau A - Reasoning)
- **Statut CTO :** Abandonné pour raisonnement en temps réel, conservé uniquement comme option future pour le générateur de rapport macro asynchrone (AI-05 legacy). Le LLM local générique (Ollama) suffit pour ce rôle non-critique. (Pas de gain démontré vs Ollama générique pour un usage aussi limité, complexité d'intégration non justifiée).
- **Pourquoi l'utiliser ?** Modèle NLP fine-tuné sur le vocabulaire financier.
- **Pourquoi ne pas le réécrire nous-mêmes ?** Fine-tuner LLaMA sur des rapports financiers coûte des milliers de dollars en cloud.
- **Modules utilisés :** HuggingFace Transformers, bitsandbytes (Quantization).
- **Ce que nous gardons :** Le modèle GGML/GGUF pour exécution locale via `llama.cpp` dans l'adaptateur `OllamaReasoner` du Reasoning Engine (AI-03).
- **Dette Technique (MockReasoner) :** Actuellement, le système utilise `MockReasoner` par défaut pour ne pas bloquer l'Event Loop si Ollama n'est pas lancé. Conséquence : les objets `Knowledge` générés ne contiennent que des règles statistiques brutes (`AvoidPattern`/`PreferredPattern`) sans résumé textuel généré. Il faudra trancher plus tard sur l'activation d'Ollama local en production.
- **Architecture :** Transformer LLM.
- **Temps estimé :** N/A (Abandonné actif).
- **RAM/GPU :** 8-16 GB VRAM.
- **Risques :** Hallucination.
- **Alternatives :** Ollama (Générique, actuellement utilisé via Mock/Fallback).

---

## 10. FinceptTerminal & 11. Vibe-Trading (Niveau B - UI/UX)
- **Pourquoi les utiliser ?** Références de Design System pour le *Trading Control Center*.
- **Pourquoi ne pas le réécrire nous-mêmes ?** Nous LE réécrivons. Ces dépôts servent uniquement de Moodboard (Couleurs, Layouts de terminaux pro).
- **Ce que nous gardons :** Inspiration CSS/Layout.
- **Ce que nous supprimons :** Tout le code.
- **Risques :** Aucun.
