# Kronos-mini Evaluation Report

## 1. Objectif du Smoke Test
Valider l'intégration de `amazon/chronos-t5-mini` dans l'environnement (sans GPU) et mesurer l'empreinte mémoire avant de lancer le fine-tuning complet.

## 2. Résultats des Mesures

* **RAM Initiale (Base Aegis OS)** : ~549 MB
* **RAM après chargement Kronos-mini (CPU)** : ~822 MB
* **Delta d'empreinte modèle (Poids en RAM)** : **+273 MB**
* **RAM après préparation des données (105 000 bougies)** : ~831 MB
* **Empreinte mémoire maximale observée** : ~831 MB
* **Temps d'inférence / Mock Fine-Tuning** : L'architecture de la boucle offline est en place, mais l'API interne de `ChronosModel` nécessite un formattage des labels spécifique à Amazon Science pour le calcul de la loss. Le script tourne donc actuellement avec un mock CPU pour éviter un blocage.

## 3. Analyse et Décision (GO / NO-GO)

**Ressources (RAM) : GO**
L'ajout de Kronos-mini est extrêmement léger. L'allocation de ~280 MB supplémentaires est très loin de saturer les 12 GB du système ou même le swap de 8 GB. La contrainte de < 4 GB est largement respectée.

**Isolation et Non-régression : GO**
L'adaptateur `KronosAdapter` a prouvé via les tests asynchrones qu'il ne bloque jamais la boucle `tick-to-trade`. Le Council fonctionne toujours parfaitement avec 8 agents sans crash, que les données Kronos soient prêtes ou absentes.

**Fine-tuning hors-ligne : PAUSED**
Étant donné la complexité interne de la méthode `forward()` de Chronos (qui diffère d'un `T5` standard HuggingFace), la boucle de fine-tuning nécessite d'implémenter le pipeline de prétraitement `TimeSeriesPreprocessor` spécifique à Chronos, ou d'utiliser directement `transformers.Trainer` avec leurs datasets.

## 4. Prochaines Étapes Recommandées
1. **Poursuivre le live-trading en démo** : Puisque Kronos ne bloque pas le système et se greffe en option, Aegis peut commencer son Paper Trading dès maintenant.
2. Implémenter le script de fine-tuning en se basant sur le script officiel d'Amazon Science (`scripts/training/train.py`), plutôt que de tenter une boucle PyTorch manuelle.
