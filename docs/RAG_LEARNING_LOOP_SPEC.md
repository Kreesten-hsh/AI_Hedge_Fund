# Spécification de la Boucle d'Apprentissage RAG & Mémoire d'Expérience

- **Statut** : SPÉCIFICATION TECHNIQUE V2.0 (Lot 1)
- **Date** : 2026-08-08
- **Composants concernés** : `src/aegis_trade/infrastructure/memory/faiss_store.py`, `src/aegis_trade/infrastructure/memory/basic_embedding.py`, `src/aegis_trade/domain/memory.py`
- **Dépend me** : ADR 0032 (Pivot Pipeline Cognitif v2.0), `docs/SYSTEM_ARCHITECTURE_V2.md`

---

## 1. Périmètre & Interdiction du DRL / Fine-Tuning

> [!CAUTION]
> **CADRE STRICT ET SANS ÉQUIVOQUE** :
> L'expression « apprendre de ses erreurs » au sein d'Aegis Quant OS v2.0 désigne **EXCLUSIVEMENT** un mécanisme d'indexation et de recherche contextuelle par similarité vectorielle (Retrieval-Augmented Generation / RAG).
> - **AUCUN ré-entraînement de poids** (fine-tuning, LoRA, RLHF) n'est autorisé.
> - **AUCUN algorithme de Deep Reinforcement Learning (DRL)** (PPO, SAC, DQN) n'est implémenté.
> - Toute tentative d'introduire des mises à jour de gradient ou un entraînement de modèle sans un nouvel ADR validé constitue une violation grave des règles d'ingénierie du projet (Directive AGENTS.md §2 et §6).

---

## 2. Format Exact du Log par Trade

Chaque opération clôturée donne lieu à la création d'un enregistrement immuable normé `MemoryEntry` (`src/aegis_trade/domain/memory.py:1-50`). Le format JSON exact est le suivant :

```json
{
  "trade_id": "trd_20260808_XAUUSD_00104",
  "timestamp_entry": "2026-08-08T14:30:00Z",
  "timestamp_exit": "2026-08-08T16:45:00Z",
  "symbol": "XAUUSD",
  "timeframe": "H1",
  "context": {
    "market_regime": "BULLISH_TREND_HIGH_VOL",
    "volatility_atr": 14.50,
    "spread_bps": 1.859,
    "sentiment_summary": "Résultats d'inflation US plus forts qu'attendu, pression haussière sur les taux réels",
    "prompt_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  },
  "decision": {
    "action": "BUY",
    "reasoning_summary": "Rupture de résistance majeure confirmée par la volatilité H1 avec biais sémantique haussier",
    "target_horizon_bars": 5,
    "confidence_score": 0.85,
    "stop_loss_price": 2380.50,
    "take_profit_price": 2415.00
  },
  "outcome": {
    "exit_reason": "TAKE_PROFIT_REACHED",
    "entry_price": 2390.00,
    "exit_price": 2415.00,
    "gross_pnl_pct": 1.046,
    "total_fees_bps": 1.859,
    "net_pnl_pct": 1.027,
    "hold_duration_minutes": 135
  }
}
```

---

## 3. Mécanisme d'Injection RAG dans le Prompt (Module 2)

Lorsqu'une nouvelle décision doit être prise par l'Agent Cognitif (Module 2) :

```text
[Contexte Marché Actuel]
          │
          ▼
   Génération Vectorielle (BasicEmbedding:1-60)
          │
          ▼
   Recherche k-NN (FaissVectorStore:1-120) ──> Top-k=3 Souvenirs les Plus Similaires
          │
          ▼
   Injection Dynamique dans le Prompt System (`cognitive_agent_v1.md`)
```

### Règle d'Injection Top-k :
- Le nombre de souvenirs injectés est **strictement borné à $k=3$** (ou maximum $k=5$) pour respecter le budget de jetons (1024 tokens maximum en sortie, context window de 8192).
- **L'historique complet n'est JAMAIS réinjecté**. Seuls les trades passés présentant la plus forte similarité cosinus sur l'état sémantique et la volatilité sont extraits.

### Template d'Injection dans le Prompt :

```markdown
## EXPÉRIENCES SIMILAIRES PASSÉES (MÉMOIRE RAG)

Voici 3 situations passées similaires à l'état actuel et leurs résultats :

1. [P&L NET : +1.03%] Symbole: XAUUSD | Régime: BULLISH_TREND_HIGH_VOL
   Raisonnement passé: Rupture de résistance avec fort volume.
   Leçon: La sortie sur Take-Profit fixe a permis de capturer l'extension avant retracement.

2. [P&L NET : -0.85%] Symbole: XAUUSD | Régime: BULLISH_TREND_HIGH_VOL
   Raisonnement passé: Entrée immédiate sur cassure sans confirmation de bougie.
   Leçon: Cassure feinte (whipsaw), péage d'exécution de 1.859 bps ayant alourdi la perte.

Utilisez ces leçons passées pour éviter de répéter les mêmes erreurs de jugement.
```
