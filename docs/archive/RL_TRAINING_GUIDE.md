# Guide d'Entraînement RL (Reinforcement Learning)

Ce document décrit comment lancer un cycle d'entraînement pour le moteur RL (AI-04), lire les métriques, et interpréter les promotions de politiques.

## Prérequis Système
- Machine CPU-only.
- **Important :** S'assurer qu'au moins 4 à 8 Go de swap sont configurés (fichier `create_swap.sh` à la racine) pour éviter un `OOM-kill` (Out of Memory) lors des entraînements par batch de PPO.

## 1. Déclenchement de l'Entraînement
L'entraînement ne doit **jamais** s'exécuter dans le thread principal de trading (chemin HFT).
- **Fréquence :** Calendrier fixe hebdomadaire (Batch week-end).
- **Processus :** Isolé dans un script cron ou une tâche de maintenance.
- **Algorithme :** PPO (Proximal Policy Optimization) via `Stable-Baselines3`. On-policy, stable et gérable en RAM.

## 2. Lecture des Métriques
Pendant l'entraînement, SB3 générera des logs (stdout ou TensorBoard) contenant les métriques suivantes :
- `ep_rew_mean` : La récompense moyenne (doit augmenter au fil du temps).
- `loss` : La perte du réseau de neurones.
- `approx_kl` : Divergence KL, indiquant l'ampleur de la mise à jour de la politique.

La récompense utilisée est la **Composite Aegis Reward**, qui pénalise fortement le drawdown, le slippage, le spread, et le temps en position, tout en récompensant le PnL normalisé.

## 3. Policy Promotion Gate
Une fois qu'une nouvelle politique candidate est entraînée, elle n'est **pas automatiquement déployée**. 
Elle passe par la classe `PolicyEvaluator` :
1. **Hold-out Set** : Évaluation sur des expériences récentes non vues.
2. **Critères** : Reward Score >= Politique actuelle ET Max Drawdown <= Politique actuelle.
3. **Audit** : L'événement `PolicyPromoted` ou `PolicyRejected` est émis.

## 4. Contrat d'Interface avec AI-05 (Le Conseil)
La politique génère un objet `PolicyDecision` comprenant :
- **Primaire (AI-04)** : `risk_multiplier` et `confidence_threshold_adjustment` pour moduler le risque global.
- **Secondaire (AI-05)** : Un dictionnaire `agent_weights` pour pondérer l'importance de chaque sous-agent (Trend, Momentum, Volatility, etc.).
