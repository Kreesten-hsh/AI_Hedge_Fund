# Spécification — Intégration Kronos-mini (Sprint AI-08)

> Ce document répond à "qu'est-ce qu'on fait et où on va" avant d'écrire une ligne de code. Il précède `KRONOS_MINI_IMPLEMENTATION_INSTRUCTIONS.md` (le "comment"). À lire en complément de la section 5 (Kronos) de `GITHUB_INTEGRATION_GUIDE.md`, déjà à jour avec le statut "En évaluation — variante mini uniquement, CPU".

## 1. Objectif

Ajouter un signal de prédiction de série temporelle réel au système — la seule brique de tout Aegis Quant OS qui prédit littéralement le futur, plutôt que de décrire le présent (Council) ou d'apprendre du passé (Knowledge Base, RL). Kronos-mini (4.1M paramètres, conçu pour l'inférence CPU) regarde les 2048 dernières bougies et prédit les prochaines, sur Boom/Crash/Gold spécifiquement — pas en généraliste sur 45 bourses comme le modèle pré-entraîné de base.

**Ce que Kronos-mini n'est pas** : un remplaçant du Council. Sa sortie devient une entrée supplémentaire pour le Trend Agent et le Pattern Agent — la décision finale reste toujours l'agrégation déterministe des 8 votes, jamais directement la prédiction de Kronos.

## 2. Les 4 leviers pour compenser la taille réduite du modèle

Rappel du raisonnement déjà validé : un modèle à 4.1M de paramètres a structurellement moins de capacité qu'un modèle à 102M (base), mais on n'a pas besoin de généraliste — seulement d'être bon sur 2-3 actifs précis.

1. **Fine-tuning ciblé** : ré-entraîner Kronos-mini spécifiquement sur l'historique de Boom 1000, Crash, et Gold — pas d'usage brut du modèle pré-entraîné généraliste. Concentre toute la capacité limitée du modèle sur exactement ce dont on a besoin.
2. **Fenêtre de contexte longue** : exploiter la fenêtre de 2048 bougies de Kronos-mini (4x plus longue que small/base, qui plafonnent à 512) — mini peut repérer des motifs à plus long terme que les versions plus grosses n'ont même pas la capacité structurelle de voir.
3. **Ensemble de prédictions** : plusieurs passes d'inférence avec échantillonnage différent (température/top_p variés), agrégées par moyenne ou médiane — réduit le bruit d'une prédiction individuelle, gratuit en paramètres supplémentaires.
4. **Validation systématique par le système existant, jamais confiance aveugle** : la prédiction brute de Kronos-mini ne pilote jamais directement une décision. Elle passe par le Pattern Agent/FAISS (AI-01) pour vérifier si des prédictions similaires dans le passé se sont avérées justes, et le RL (AI-04) apprend avec le temps le poids de confiance à accorder à ce signal — potentiellement différent par actif (peut-être fiable sur Gold, pas sur Crash).

## 3. Où Kronos-mini s'intègre dans l'architecture existante

```text
Données de marché (Boom/Crash/Gold)
        │
        ▼
   Kronos-mini (fine-tuné, fenêtre 2048, ensemble)
        │  prédiction + intervalle de confiance
        ▼
   Trend Agent / Pattern Agent (AI-05) ── consultent aussi FAISS (AI-01) et Knowledge Base (AI-03)
        │
        ▼
   Vote pondéré dans le Council (poids ajustés par le RL, AI-04)
        │
        ▼
   CouncilVerdict → GlobalRiskManager → Ordre
```

Kronos-mini se branche en amont du Pattern Agent, jamais directement sur le chemin de décision. Cohérent avec la contrainte HFT déjà établie pour tous les composants IA du projet : l'inférence tourne en asynchrone/batch, jamais de façon synchrone dans la boucle tick-to-trade.

## 4. Critères de succès — avant d'activer Kronos en production

Ne pas intégrer sur la foi d'une intuition. Mesurer concrètement, comme déjà décidé dans `GITHUB_INTEGRATION_GUIDE.md` :

| Critère | Seuil |
|---|---|
| MAPE / RMSE vs baseline naïve (persistence, dernière valeur connue) | Doit battre la baseline, pas juste être "raisonnable" dans l'absolu |
| Latence d'inférence (CPU, batch) | Documentée, doit rester compatible avec un usage asynchrone (pas de seuil dur type <20ms — ce n'est pas dans le chemin critique) |
| RAM utilisée | < 4 GB (déjà noté dans `GITHUB_INTEGRATION_GUIDE.md`), à re-confirmer sur le matériel réel (12 GB total, ~2 GB dispo au repos) |
| Impact sur le Win Rate du Council quand le signal Kronos est activé vs désactivé | Comparaison A/B nécessaire — le signal doit démontrer un gain mesurable, pas juste "exister" |

**Si Kronos-mini ne bat pas la baseline naïve après fine-tuning**, la décision par défaut est de ne pas l'activer en production plutôt que de l'intégrer quand même "parce qu'on a fait le travail" — cohérent avec la discipline scientifique déjà appliquée ailleurs dans le projet (le même principe qui a fait annuler l'ancien Council LLM).

## 5. Séquencement avec le live-trading en démo

Le live-trading en démo (`scripts/run_live_paper_trading.py`) **n'attend pas** Kronos pour démarrer — le Council à 8 agents fonctionne déjà de façon autonome. Kronos-mini s'ajoute en parallèle :
1. Fine-tuning et validation de Kronos-mini en offline (sur données historiques déjà disponibles), pas besoin d'attendre le live pour ça.
2. Une fois les critères de succès de la section 4 validés, brancher le signal dans le Trend/Pattern Agent.
3. Le live-trading en démo sert alors doublement d'objectif : accumuler les 200 trades/2 semaines déjà exigés pour la validation globale, **et** servir de terrain d'entraînement en conditions réelles pour affiner la confiance du RL envers le signal Kronos au fil du temps.

## 6. Ce qui reste hors scope pour ce sprint

- Pas de version small/base de Kronos — uniquement mini, pour rester CPU-only.
- Pas de fine-tuning continu automatique en production pour l'pour l'instant — le fine-tuning est un processus offline déclenché manuellement, pas un cycle hebdomadaire automatisé comme le RL (à réévaluer plus tard si les résultats sont bons).
- Pas de News Agent réactivé en parallèle — reste en stub neutre comme décidé en AI-05, sans lien avec ce sprint.
