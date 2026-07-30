# Journal de Recherche & Expériences (Research Logbook)

> **Important** : Ce document est le registre officiel de toutes les expériences (gagnantes ou perdantes) d'Aegis Quant OS. Il est le socle de l'apprentissage asymétrique. Chaque ligne correspond à un vecteur dans la base FAISS.

## Template d'Expérience

```yaml
Experience: #00001
Date: YYYY-MM-DD HH:MM:SS
Actif: Boom1000
Configuration_Marche:
  Volatilité_ATR: 
  Spread:
  Trend_MVA:
  RSI:
  Momentum:
Embedding_ID: vector_id_12345
Décision_Initiale: 
  Agents_votants: Quant, Macro, Memory
  Vote: APPROVED
  Risk_Veto: FALSE
  Ordre: BUY 0.1 Lot
Résultat:
  PnL: +X
  Max_Drawdown: -Y
  Temps_en_position: Z secondes
  Slippage: S
Catégorie: SUCCESS_MEMORY
Pourquoi: (Commentaire auto-généré par le LLM post-trade)
```

## Logs d'Expériences (Phase Live / AI-07)

*Les logs des 200 trades du cycle papier réel et du cycle capital réel (AI-07) seront injectés ici automatiquement.*

## Événements de Gouvernance
- **[2026-07-30] Intégration Kronos (Sprint AI-08)** : Erreur de modèle corrigée (passage de l'Amazon Chronos générique au vrai modèle natif finance `shiyu-coder/Kronos`). Fine-tuning et inférence sur CPU testés avec succès via `run_kronos_smoke_test.py`. Isolation totale via l'Adapter. Les résultats de la première évaluation sont très positifs (RAM Peak à ~917 MB, 49s par epoch de 1000 bougies). Décision : **ACTIF**, prêt pour le fine-tuning complet.
- **[2026-07-30] Modèles externes** : 
  - Qlib (Microsoft) : Actif. Modèle `LGBModel` fonctionnel pour features alpha.
  - Kronos (shiyu-coder) : Actif. Modèle AAAI 2026 natif finance avec discrétisation OHLCV `BSQuantizer`. Entraînement et inférence CPU fonctionnels en tâche de fond.
  - Chronos (Amazon) : Rejeté. Modèle générique (T5) non adapté aux séries temporelles financières (remplacé par Kronos).
- **[2026-07-30] Correction de Gouvernance (Post AI-07)** : Alignement de la Roadmap (`PHASE2_ROADMAP.md`) avec le `VALIDATION_PIPELINE_REPORT.md` réel. Modification des statuts de AI-06/AI-07 à `[CODE-READY]`. FinGPT (Abandonné, remplacé par Ollama) et lightweight-charts (Planifié post-validation spec).

## Logs de Validation de Politique (Policy Promotion Gate)
Trace des validations de politiques RL (AI-04).
- *[DATE] Policy [ID] évaluée vs [ID_ACTUELLE]. Statut : PROMOTED / REJECTED.*
