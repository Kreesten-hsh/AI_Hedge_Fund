# FinRL - Spécification de l'Apprentissage par Renforcement

## 1. Objectif de l'Agent RL
Le module RL ne remplace pas le moteur de trading. Il ajuste dynamiquement les poids du comité et la pondération des filtres de la mémoire vectorielle. L'objectif n'est pas de maximiser les profits bruts.

## 2. La Fonction de Récompense (Reward Function)
La récompense mathématique est calculée post-trade et n'est *pas* égale au PnL.
La formule prend en compte les 8 axes définis :

```text
Reward = PnL_Normalise
         - Penalty_Max_Drawdown (pénalité exponentielle)
         - Penalty_Temps_En_Position (encourager la vitesse HFT)
         - Penalty_Slippage (pénaliser l'exécution instable)
         - Penalty_Spread
         - Penalty_Variance_Globale
         + Bonus_Ratio_Gain_Risque
```
*Exemple : Un gain de 2$ obtenu avec un drawdown frôlant le StopLoss de 20$ aura une Reward extrêmement NÉGATIVE.*

## 3. L'Environnement d'Entraînement
Nous allons créer un `CustomAegisEnv` héritant de `gym.Env`. Cet environnement rejouera les expériences stockées dans le *Research Logbook* (et non de simples bougies OHLC). 

## 4. Stratégie d'Apprentissage
L'apprentissage se fait de manière asynchrone (Batch Learning) chaque week-end ou lors des périodes de maintenance, en utilisant l'historique de la semaine écoulée pour réajuster le modèle (PPO ou SAC).
