# Audit d'Intégration GitHub - Guide Définitif (Deep Audit)

Ce document détaille l'audit technique de chaque dépôt (actif et inspirationnel) pour l'intégration dans Aegis Quant OS. 

> **Annoté le 2026-07-31** sur la base de `docs/refont/AUDIT_COMPLET_2026-07-31.md` (verdict **NO-GO**).
>
> **Nature de ce document, à ne pas confondre :** il consigne des **décisions d'intégration** — pourquoi tel
> dépôt, ce qu'on en garde, ce qu'on en jette. À ce titre il reste valable et n'est pas réécrit.
> Il ne dit **rien** de l'état réel du câblage. Les « Statut CTO » sont des intentions, pas des mesures.
>
> **Pour l'état mesuré du code, la source est `DEPENDENCY_MATRIX.md`**, qui distingue `[ÉCRIT-NON-CÂBLÉ]`,
> `[CÂBLÉ-NON-VALIDÉ]`, `[FAÇADE]`, `[VENDORÉ]` et `[INSPIRATION]`. Rappel des trois écarts les plus lourds :
> aucun abonnement WebSocket de prix n'existe dans le dépôt ; Kronos est vendoré (1 532 lignes, **sans
> LICENSE**) et prédit sur `np.random.randn` ; la production injecte `MockReasoner()` (`api/deps.py:53`).

---

### `vnpy`
**Rôle :** Broker Adapter et Gateway.
**Justification :** Framework HFT industriel en C++/Python, évite de réécrire la connectivité bas niveau FIX ou REST avec les brokers. Couche d'exécution pure.

### `ta`
**Rôle :** Calcul des indicateurs techniques (RSI, MACD, ATR, EMA, VWAP).
**Justification :** Requis par `FEATURE_ENGINEERING.md`. Fournit des calculs d'indicateurs vectorisés ultra-rapides sans réinventer la roue, crucial pour maintenir la latence < 20 ms lors de la génération des Market Snapshots en direct.

## 1. vn.py (Niveau S - Execution)

> **Correctif de forme (2026-07-31) :** ce titre était corrompu — il lisait
> `## 4. Workflows GitHub Actionses et connectivité MT5/FIX.`, un fragment épissé au milieu de la section
> `vnpy`, et le numéro `4.` était en doublon avec la section FinRL. Le contenu ci-dessous a toujours porté
> sur la passerelle vn.py ; seul l'intitulé est réparé. Aucune décision n'est modifiée.

- **Pourquoi ne pas le réécrire nous-mêmes ?** Refaire un connecteur MT5 asynchrone robuste en C++ prendrait 6 mois de R&D avec des risques de perte de paquets, ce qui est mortel en HFT.
- **Modules utilisés :** `vnpy.event`, `vnpy.gateway.mt5`, `vnpy.trader.object`.
- **Classes :** `EventEngine`, `Mt5Gateway`, `OrderRequest`, `TickData`.
- **Fonctions :** `subscribe()`, `send_order()`, `cancel_order()`.
- **Architecture :** Event-driven (Publish/Subscribe).
- **Ce que nous gardons :** Uniquement le pont de communication réseau (Le Gateway) et les Data Objects.
- **Ce que nous supprimons :** Toute l'interface graphique (`vnpy.ui`), les modules de backtest (`vnpy.app.cta_strategy`), l'ORM base de données.
- **Temps estimé (Intégration) :** 1 Sprint (Fait).
- **Correctif de statut (2026-07-31) :** « (Fait) » est faux au sens du câblage. La passerelle route des
  ordres, mais `on_trade` a pour corps `pass` (`infrastructure/live/vnpy/execution.py:69`) et
  `send_order` renvoie `return "mock_id"` (`:46`) : **aucun retour d'exécution ne remonte au
  portefeuille**. Trois chemins contournent le `RiskEngine` (`providers/vnpy_adapter.py:52,57,79`).
  Statut mesuré : `[CÂBLÉ-NON-VALIDÉ]`. Prérequis Lot 1 et Lot 2.
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
- **Pourquoi l'utiliser ?** Standard Microsoft pour la génération de features quantitatives et l'entraînement de modèles quantitatifs.
- **Note d'implémentation (Directive CTO 2026-08-02) :** `qlib.init()` souffre actuellement d'une incompatibilité au niveau de `mlflow 1.27.0` (`mlflow.exceptions` manquant). L'intégration utilise un entraînement **LightGBM direct** (`lightgbm 4.7.0`) consommant le `FeatureStore` Aegis via `QlibDataset` et `DatasetBuilder`. **Ceci est un contournement TEMPORAIRE.** Le passage au `qlib.init()` standard et au workflow Qlib complet aura lieu au **Lot 5** après la mise à jour de `mlflow`.
- **Modules utilisés :** `qlib.data.dataset`, `qlib.utils` (complétés par `lightgbm`).
- **Classes :** `QlibDataset`, `DatasetBuilder`, `LightGBMModel`.
- **Fonctions :** Extracteurs d'Alpha et entraînement direct LightGBM.
- **Architecture :** Data pipeline DAG + interface `IModel`.
- **Ce que nous gardons :** Le modèle et la structure de dataset.
- **Ce que nous supprimons :** Tout mock ou façade fictive.
- **Temps estimé :** 3 Semaines.
- **RAM :** 4 GB.
- **CPU :** Faible à modéré.
- **GPU :** Aucun.
- **Risques :** Conçu pour des données Journalières (Daily), doit être adapté aux données intraday.
- **Alternatives :** TA-Lib (Moins IA-friendly), Pandas-TA (Moins optimisé).
- **Tests :** Validation via Walk-Forward, Hold-Out, Monte-Carlo et Benchmarks.

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
Status: **ACTIF** (Mode: Fine-tuning & Inférence sur CPU en tâche de fond)
- **Pourquoi l'utiliser ?** Modèle LLM pré-entraîné (`shiyu-coder/Kronos`) pour le forecasting sur séries temporelles, conçu pour la finance (discrétisation OHLCV).
- **Pourquoi ne pas le réécrire nous-mêmes ?** Architecture spécialisée, fine-tuning CPU réalisable grâce à la taille (4.1M params).
- **Modules utilisés :** `aegis_trade.providers.kronos`.
- **Classes :** `KronosAdapter`, `KronosModelFactory`, `KronosFineTuner`.
- **Fonctions :** `adapter.get_latest_forecast()`.
- **Architecture :** Transformer avec Hierarchical Embeddings et Dependency Aware Layers.
- **Ce que nous gardons :** Tout le code officiel de `shiyu-coder/Kronos` dans `shiyu_model`.
- **Ce que nous supprimons :** Rien, mais nous l'appelons via notre `KronosAdapter` asynchrone non-bloquant avec mise en cache.
- **Temps estimé :** Sprint AI-08 (Actif).
- **RAM :** ~800-900 MB max.
- **CPU :** Inférence et fine-tuning CPU-only.
- **GPU :** Aucun.
- **Risques :** Modèle très sensible à la qualité des OHLCV. La non-régression est garantie par l'isolation du cache.
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
- **Correctif de statut (2026-07-31) :** ce paragraphe présente `MockReasoner` comme une dette parmi d'autres. Mesure : `api/deps.py:53` injecte `MockReasoner()` sur **le seul chemin de production**. `OllamaReasoner` existe mais n'a aucun site d'appel productif. Le raisonnement des agents n'est donc pas « partiellement dégradé » — il est absent. Ce n'est pas « à trancher plus tard » : c'est un prérequis du Lot 4. Par ailleurs `ADR-002`, qui acte le remplacement de FinGPT par Ollama, décrit un état qui n'existe pas et doit être marqué `Superseded` (Lot 5).
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
