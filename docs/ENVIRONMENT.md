# Aegis Quant OS — Institutional Development Environment

Ce document décrit la configuration officielle et certifiée pour développer et exécuter Aegis Quant OS. 

Conformément à la mission **INFRA-01**, cet environnement est 100% reproductible et basé sur Linux Mint. 
À partir de ce stade, Linux devient la plateforme unique de développement et de déploiement (VPS, Cloud, Edge).

---

## 1. Système et Prérequis

* **Système d'Exploitation** : Linux Mint (ou distribution basée sur Ubuntu/Debian récente).
* **Interpréteur Officiel** : Python 3.11.x
* **Gestionnaire d'Environnement** : `uv` (recommandé pour une installation isolée ultra-rapide) ou `apt`.

---

## 2. Création de l'Environnement

Nous recommandons fortement l'utilisation de `uv` pour isoler Python 3.11 proprement, indépendamment des paquets de votre système d'exploitation.

### Méthode A : Avec `uv` (Recommandée)

1. **Installer uv**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
2. **Créer l'environnement virtuel Python 3.11**
   Dans le répertoire racine d'Aegis Quant OS :
   ```bash
   uv venv -p 3.11 .venv
   ```
3. **Activer le venv**
   ```bash
   source .venv/bin/activate
   ```

### Méthode B : Avec `apt` (Classique)

1. **Installer Python 3.11**
   ```bash
   sudo apt update
   sudo apt install -y python3.11 python3.11-venv python3.11-dev
   ```
2. **Créer le venv**
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   ```

---

## 3. Installation des Dépendances

L'ensemble des dépendances quantitatives institutionnelles a été figé.

1. **S'assurer d'avoir l'environnement actif** :
   ```bash
   source .venv/bin/activate
   ```
2. **Installer les dépendances figées** :
   ```bash
   pip install -r requirements.txt
   ```
   *Alternative si vous utilisez uv :*
   ```bash
   uv pip install -r requirements.txt
   ```

*(Les bibliothèques incluent : OpenBB, Microsoft Qlib, vn.py, pandas, numpy, scipy, scikit-learn, lightgbm, xgboost, polars, pyarrow, matplotlib, etc.)*

---

## 4. Vérification et Certification (INFRA-01)

Une fois l'installation terminée, vous devez valider votre environnement grâce au script de certification fourni.

### Étape 4.1 : Exécution du Certificateur
```bash
python scripts/verify_environment.py
```
Le script va auditer l'OS, l'architecture, la RAM, le disque, la version de Python, l'activation du `.venv`, ainsi que l'import effectif de toutes les bibliothèques. **L'état final doit être `[PASS]`.**

### Étape 4.2 : Lancement des Smoke Tests
Afin de garantir que les briques internes d'Aegis (Moteur de Portefeuille, Gouvernance du Risque) ne sont pas altérées par les dépendances quantitatives :
```bash
pytest tests/test_smoke_env.py
```
*(Si certaines bibliothèques très spécifiques comme `qlib` ou `vnpy` remontent des exceptions C++ dues au système, le test le signalera de façon explicite (xfail) sans casser le moteur).*

---

## 5. Résolution des Problèmes Connus (Troubleshooting)

### A. Echec d'import de `pyqlib` ou `vn.py` sur Linux
Certaines distributions peuvent manquer de bibliothèques C++ requises par ces moteurs. 
- Vérifiez la présence de `build-essential` et `cmake` :
  ```bash
  sudo apt install -y build-essential cmake
  ```
- Sous Python 3.11, pyqlib (version < 0.9.x) pouvait poser problème sous Windows mais fonctionne sous Linux via compilation source. Si vous rencontrez une erreur, Aegis Quant OS isole les pannes via son système Anti-Corruption Layer (ACL). Les *smoke tests* reporteront une alerte `[WARNING]` ou `[xfailed]` mais ne bloqueront pas le démarrage global.

### B. OOM (Out of Memory) lors de `pip install`
Si votre machine ou VPS dispose de moins de 8Go de RAM, l'installation de bibliothèques lourdes comme `xgboost` ou `scipy` peut crasher.
- Solution : Utilisez `uv pip install` qui gère mieux la mémoire, ou installez via `--no-cache-dir`.

---
*Ce document sert de référence absolue pour l'intégration de nouveaux collaborateurs ou de nouveaux agents sur le projet Aegis Quant OS.*
