# Kronos-mini CPU Evaluation Report

Ce rapport documente les métriques de performance CPU observées pour l'entraînement et l'inférence du vrai modèle `shiyu-coder/Kronos-mini` sur l'infrastructure actuelle.

## Contexte
- **Modèle** : `shiyu-coder/Kronos-mini` (Modèle AAAI 2026 natif finance)
- **Tokenisation** : `KronosTokenizer` via `BSQuantizer` (discrétisation OHLCV)
- **Hardware** : CPU Node local (sans CUDA)
- **Objectif** : Valider la faisabilité du fine-tuning et de l'inférence en arrière-plan sans bloquer la boucle de trading.

## Inférence (Background Task)
- **Latence par requête** : ~500ms à 1500ms (selon le `pred_len` et `sample_count`)
- **Mémoire** : ~630MB
- **Isolation** : Totalement isolée via `asyncio.to_thread`. La boucle de prix `tick_loop` n'est pas bloquée. Le cache répond en O(1) (<1ms).

## Fine-tuning (Offline)
- **Dataset de test** : 1000 bougies OHLCV générées (stride=10).
- **RAM Initiale** : ~568 MB
- **RAM en pic** : ~917 MB (Delta : +351 MB)
- **Temps par Epoch** : ~15 secondes pour 1000 lignes (Total temps d'entraînement incluant preprocessing/validation: ~49 secondes).

### Extrapolation pour un run complet
Pour un dataset réel de 105,000 bougies (ex: Boom_1000) :
- Le temps d'entraînement sur CPU pour 1 epoch est estimé à environ **25-30 minutes** par actif.
- La consommation RAM maximale est estimée autour de **1.5 GB - 2 GB**.

**Conclusion** : Le fine-tuning CPU est parfaitement réaliste en tâche de fond. Le smoke test confirme que le script d'entraînement est non-bloquant et que l'empreinte mémoire est suffisamment faible pour tourner en parallèle du moteur de trading.
