# AEGIS QUANT OS — Environment

Ce document est la référence officielle du projet concernant la configuration, la préparation et la validation de l'environnement de développement et d'exécution.

## Politique de Compatibilité

Afin de garantir la stabilité des dépendances critiques institutionnelles (notamment `OpenBB` et `Qlib`), le projet est strictement verrouillé sur :
- **Python 3.11** (idéalement 3.11.x)
- **Système d'exploitation :** Windows 11 (requis par MetaTrader 5)

*Aucune montée de version vers Python 3.12 ou 3.13 n'est autorisée tant que les bibliothèques quantitatives principales n'offrent pas un support officiel complet et validé.*

## Procédure Complète d'Installation

### 1. Création du Virtual Environment (`.venv`)

Vérifiez d'abord que votre interpréteur par défaut est bien Python 3.11 (`py -3.11 --version`).
Depuis la racine du projet (dans PowerShell) :

```powershell
# Supprimer un éventuel ancien environnement
Remove-Item -Recurse -Force .venv -ErrorAction SilentlyContinue

# Créer le nouvel environnement avec Python 3.11
py -3.11 -m venv .venv
```

### 2. Installation des Dépendances

Activez l'environnement virtuel et installez les dépendances en mode éditable avec les outils de développement :

```powershell
# Activer l'environnement
.venv\Scripts\Activate.ps1

# Mettre à jour pip
python -m pip install --upgrade pip

# Installer le projet et ses dépendances (avec pytest, pytest-cov, pytest-mock)
pip install -e .[dev]
```

### 3. Validation Finale de l'Environnement

Avant de lancer le moindre script métier ou la suite de tests, vous devez exécuter le script de vérification :

```powershell
python scripts/verify_environment.py
```

Si le script affiche un statut final **`READY`**, l'environnement est certifié conforme.

### 4. Exécution des Tests

Une fois l'environnement validé, vous pouvez exécuter la suite de tests de manière isolée pour vérifier les régressions :

```powershell
pytest tests/providers
pytest tests/domain
pytest tests/engine
```

**Règle d'Or :** Si la validation (`verify_environment.py`) échoue, aucun développement n'est autorisé tant que le problème d'environnement n'a pas été corrigé.
