# Direction Stratégique de Trading — Aegis Quant OS

> **Date** : 2026-08-02  
> **Auteur** : Directive CTO  
> **Périmètre** : Stratégie de trading, sélection des actifs, cadrage de l'exécution et de l'apprentissage.

---

## 1. Choix de l'actif principal pour le démarrage

Pour la phase d'entraînement initial, d'accumulation d'expérience (FAISS, Knowledge Base) et de calibration du RL :

- **Actif unique de démarrage : Un seul indice synthétique Deriv (Crash 1000 ou Boom 1000).**
- **Justification** : Concentrer l'apprentissage sur un seul actif d'abord afin d'atteindre une masse critique d'expériences pertinentes. Diluer le capital d'apprentissage sur 3 actifs en parallèle dès le jour 1 ralentit la convergence des modèles et des agents.
- **Extension future** : Gold (`XAUUSD`) et le second indice synthétique ne seront ajoutés qu'une fois la stabilité et l'edge statistique prouvés sur le premier actif.

---

## 2. Raisons du choix : Indices Synthétiques Deriv vs Gold

| Critère | Indices Synthétiques (Boom/Crash) | Actifs Traditionnels (Gold / Forex) |
|---|---|---|
| **Disponibilité** | 24/7 / 365 jours | Fermeture les week-ends, sessions intermédiaires créant des gaps |
| **Spread** | Fixe et prévisible | Variable, élargissement violent lors des news/rollovers |
| **Dynamique** | Mécanique et répétable (processus stochastique contrôlé) | Bruit macroéconomique complexe, interventions banques centrales |

### Risque spécifique à gérer
Les indices Boom/Crash comportent des **spikes (pics verticaux) récurrents** programmés dans leur algorithme de génération.
- **Mitigation** : Ce risque est strictly géré par le veto absolu du **RiskManager / GlobalRiskManager** (Stop-Loss strict, contrôle d'exposition max).

---

## 3. Cadrage du volume de transactions (100–300 trades/jour)

- **Un résultat mesuré, JAMAIS une contrainte forcée** : Le chiffre de 100 à 300 trades par jour correspond au comportement attendu d'une stratégie de scalping à haute fréquence sur horizon M1/M5.
- **Interdiction absolue** : Aucune ligne de code (`RL`, `ConflictResolver`, seuils de vote) ne doit "pousser" ou forcer le système à prendre des trades pour atteindre ce quota.
- Si le Council n'identifie aucun edge statistique un jour donné, passer 0 trade est le comportement correct et souhaité.

---

## 4. Objectifs de Rentabilité

- **Exprimés en pourcentage (%) de rendement, JAMAIS en dollars fixes** dans le code.
- Un objectif de 10 à 20 $/jour en phase initiale de capital démo sert d'illustration financière, mais les règles de position sizing (`FixedFractionalSizer`) et de risque s'expriment exclusivement en **pourcentage de l'équité**.
- Interdiction de toute cible en dollars codée en dur qui forcerait le sur-dimensionnement des positions pour atteindre un chiffre arbitraire.
