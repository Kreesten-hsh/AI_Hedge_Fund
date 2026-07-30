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
- **[2026-07-30] Évaluation Kronos-mini (Sprint AI-08)** : Smoke test réalisé sur CPU. L'empreinte mémoire est validée (+273 MB pour le chargement, ~830 MB peak total). L'architecture asynchrone non-bloquante est validée (non-régression du Council assurée). Décision : **NO-GO / PAUSED** pour le fine-tuning complet. L'API interne de `ChronosModel` empêche une simple boucle PyTorch sans réimplémenter leur DataCollator spécifique. Le système poursuit le Paper Trading sans Kronos.
- **[2026-07-30] Correction de Gouvernance (Post AI-07)** : Alignement de la Roadmap (`PHASE2_ROADMAP.md`) avec le `VALIDATION_PIPELINE_REPORT.md` réel. Modification des statuts de AI-06/AI-07 à `[CODE-READY]` pour refléter l'attente de tests réels sans argent simulé. Audit réel de `DEPENDENCY_MATRIX.md` effectué sur la base du code (utilisation d'OpenBB, Qlib, SB3/FinRL, Deriv). Décision tranchée pour Kronos (Reporté, contrainte GPU et complexité de fine-tuning), FinGPT (Abandonné, remplacé par Ollama) et lightweight-charts (Planifié post-validation spec).

## Logs de Validation de Politique (Policy Promotion Gate)
Trace des validations de politiques RL (AI-04).
- *[DATE] Policy [ID] évaluée vs [ID_ACTUELLE]. Statut : PROMOTED / REJECTED.*
