# Aegis Quant OS 🛡️📈

![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Architecture](https://img.shields.io/badge/architecture-Clean%20%7C%20Hexagonal-orange)
![Status](https://img.shields.io/badge/research-concluded%20(216%20hypotheses%20tested)-red)

**Aegis Quant OS** est un système de trading quantitatif et d'évaluation d'hypothèses d'alpha d'inspiration institutionnelle. Le système sépare rigoureusement la logique de domaine, les moteurs de risque, les garde-fous d'exécution et les adapteurs d'infrastructure (LLMs, Open-Source ML, Moteurs de Backtest, Broker Gateways).

---

## 📌 STATUT ACTUEL DE LA RECHERCHE (AOUT 2026)

> [!IMPORTANT]
> **Rigueur Scientifique & Transparence Absolue (Règle Anti-Survente)** :
> - **Hypothèses Évaluées** : **216 hypothèses** (Signaux M1/M5, Indicateurs Techniques univariés, Features Macro FRED DFII10/DXY, Microstructure Spike, Positionnement CFTC COT 088691, Trend-Following Crypto 24/7, ML Cross-Sectional Ranking).
> - **Signaux Validés en Production** : **0 / 216 (0.0%)**.
> - Tous les signaux directionnels univariés usuels sur séries de prix individuelles ont été formellement **réfutés** après déduction des péages d'exécution et correction des tests multiples FDR / Bonferroni (ADR 0025 à ADR 0031).

---

## 🏛️ CE QUI EST OPÉRATIONNEL ET ROBUSTE

1. **Architecture Hexagonale & DDD** : Couche Domaine isolée de toute dépendance tierce, garantissant l'absence de fuite d'infrastructure.
2. **Garde-Fous d'Exécution & Péage (Execution Budget Gates)** :
   - Mesure exacte du péage d'exécution ($1.859\text{ bps}$ sur Deriv / Or et $10.0\text{ bps}$ sur Crypto Spot).
   - Validation stricte par horizon $H$ (ADR 0021).
3. **Multi-Agent Council avec Veto de Liquidité/Exécution (ADR 0028)** :
   - Moteur d'agrégation de votes multi-agents.
   - Veto impératif `VETO_EXECUTION` émis par l'Agent de Liquidité si le mouvement attendu ne couvre pas le péage d'exécution.
4. **Integration des Frameworks Open-Source (Matrice `BUILD_VS_REUSE.md`)** :
   - Connecteurs pour `VectorBT`, `Microsoft Qlib`, `Freqtrade` et `pandas-ta-classic`.
5. **Jeux de Données Validés & Audités** :
   - `XAUUSD` Dukascopy 11.6 ans (D1 et H4) à alignement causal strict.
   - Données CFTC COT filtrées sur le code exact **`088691`** (Gold COMEX 100 oz Standard).

---

## 🛠️ TECHNOLOGIES ET FRAMEWORKS

- **Langage** : Python 3.11
- **Architecture** : Clean Architecture / Ports & Adapters
- **Frameworks Quantitatifs** : `vectorbt`, `pandas-ta-classic`, `scipy`, `numpy`, `pandas`, `lightgbm`
- **Infrastructure LLM** : Ollama (Adapteur local déterministe avec cache SHA-256)

---

## ⚙️ INSTALLATION ET EXÉCUTION DES TESTS

1. **Cloner le dépôt** :
   ```bash
   git clone https://github.com/votre-username/AegisQuantOS.git
   cd AegisQuantOS
   ```

2. **Créer et activer un environnement virtuel** :
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   ```

3. **Installer les dépendances** :
   ```bash
   pip install -e .
   ```

4. **Exécuter la suite complète de tests** :
   ```bash
   pytest -v
   ```

---

## 📂 STRUCTURE DU DÉPÔT ET DECISIONS (ADRs)

- **`src/aegis_trade/`** : Code source (Clean Architecture : `domain/`, `application/`, `infrastructure/`).
- **`docs/ADR/`** : Registre complet des décisions d'architecture et de recherche (0001 à 0031).
- **`docs/refont/BUILD_VS_REUSE.md`** : Matrice de réutilisation des frameworks Open-Source.
- **`docs/research/`** : Rapports de recherche quantitatifs probants.
- **`docs/archive/`** : Archives historiques et métadonnées brutes.

---

## 🎯 PROCHAINE ÉTAPES DE RECHERCHE

Prochaine direction en cours d'arbitrage — voir discussion stratégique.
