# Spécifications des Agents du Comité (Multi-Agent Council)

> **Document annoté le 2026-07-31** sur la base de `docs/refont/AUDIT_COMPLET_2026-07-31.md`.
>
> **La version précédente annonçait « Entièrement implémenté (Sprint AI-05) ».** La mesure ne conteste
> pas l'existence du code : les 8 agents existent bien dans
> `src/aegis_trade/application/council/agents/`, implémentent `IVotingAgent` et sont appelés par
> `MultiAgentCouncil.evaluate()`. Ce que « entièrement implémenté » cachait, c'est le comportement à
> l'exécution.
>
> **Exécution réelle mesurée :** `7 agents WAIT conf=0.0` → `VERDICT: WAIT | mult=0.0 | conf=0.0`.
> Le comité ne se trompe pas : il ne décide rien. Les agents ne reçoivent pas les clés de `FeatureStore`
> qu'ils lisent, donc chacun tombe sur son chemin par défaut. Un comité qui vote `WAIT` à l'unanimité
> avec une confiance nulle est structurellement indistinguable d'un comité vide.

Chaque agent est une fonction spécialisée, déterministe ou prédictive, isolée et responsable d'une
dimension spécifique du marché. Ils ne tradent pas ; ils **votent** (`BUY`, `SELL`, `WAIT`) avec un degré
de `Confidence`. Cette conception n'est pas remise en cause.

## Objectif rappelé

**Démo réelle sur Deriv pour entraîner le système, puis capital réel.** Le comité est le seul organe
décisionnel entre les features et le `RiskEngine`. S'il vote `WAIT` avec `conf=0.0` sur tous les cycles,
la démo n'entraîne rien : elle enregistre une absence de décision.

## Statut mesuré, par agent

Vocabulaire identique aux autres documents Phase 2 : `[ÉCRIT-NON-CÂBLÉ]` = code présent, zéro site
d'appel en production · `[CÂBLÉ-NON-VALIDÉ]` = appelé, aucune validation franchie · `[FAÇADE]` = renvoie
une constante, un mock ou du bruit au lieu de calculer.

| Agent | Statut mesuré | Cause mesurée |
| --- | --- | --- |
| 1. Trend | `[CÂBLÉ-NON-VALIDÉ]` | Appelé, mais les clés de features attendues sont absentes du `FeatureStore` fourni → chemin par défaut `WAIT conf=0.0`. |
| 2. Momentum | `[CÂBLÉ-NON-VALIDÉ]` | Idem. |
| 3. Volatility | `[CÂBLÉ-NON-VALIDÉ]` | Idem, aggravé par 4 implémentations d'ATR divergentes (Lot 3) : l'agent ne peut pas être fiable tant que « ATR » désigne quatre nombres différents dans le dépôt. |
| 4. Liquidity | `[CÂBLÉ-NON-VALIDÉ]` | La profondeur du carnet d'ordres n'est fournie par aucun provider. Aucune souscription de prix WebSocket n'existe dans le dépôt. |
| 5. Pattern | `[FAÇADE]` | Dépend de Kronos, qui prédit sur `np.random.randn` (`providers/kronos_adapter.py:40-41,63-71`), et de FAISS, dont l'index n'est jamais alimenté (`MemoryManager(` : 0 occurrence hors définition). Le vote est donc dérivé de bruit et d'une mémoire vide. |
| 6. News | `[FAÇADE]` | FinGPT est `[ABANDONNÉ]` (`ADR-002`) et la production injecte `MockReasoner()` (`api/deps.py:53`). Le filtre macro ne lit aucune news. |
| 7. Portfolio | `[CÂBLÉ-NON-VALIDÉ]` | Les positions ouvertes ne remontent pas : `on_trade` a pour corps `pass` (`infrastructure/live/vnpy/execution.py:69`). L'agent raisonne sur un portefeuille qui n'est jamais mis à jour par les exécutions. |
| 8. Execution | `[FAÇADE]` | Les entrées qu'il surveille sont falsifiées en amont : `latency_ms = 50.0` et `fill_price = Decimal("100.0")` en dur, `BrokerSnapshot(connected=True, latency_ms=12.5, gateway="BINANCE")` (`application/monitoring/engine.py:60-78`) alors que le broker du projet est Deriv. |

**Aucun agent `[VALIDÉ]` au 2026-07-31.** Zéro agent produit un vote issu d'une donnée de marché réelle.

## Spécification de conception (inchangée)

Les huit sections ci-dessous décrivent l'**intention** de chaque agent. Elles restent la référence de
conception ; seules les mentions de technologies déjà mesurées comme absentes sont annotées.

## 1. Trend Agent
- **Responsable :** Analyse de la structure du marché à moyen terme.
- **Features surveillées :** EMA, MA, ADX, Structure des prix (Higher Highs, Lower Lows).
- **Sortie :** `[Vote, Confidence]`

## 2. Momentum Agent
- **Responsable :** Évaluation de la force immédiate du mouvement.
- **Features surveillées :** RSI, MACD, Momentum, ROC, CCI.
- **Sortie :** `[Vote, Confidence]`

## 3. Volatility Agent
- **Responsable :** Détection des régimes d'expansion ou de contraction.
- **Features surveillées :** ATR, Bandes de Bollinger, Volatility Regime (VIX proxy).
- **Sortie :** `[Vote, Confidence]`
- **Réserve mesurée :** l'ATR a 4 implémentations divergentes dans le dépôt (`utils/math.py:66-135`,
  `engine/strategy.py:118-145`, `application/reflection/extractor.py:54-101`,
  `infrastructure/features/technical_extractor.py:100-140`). Unification requise au Lot 3 avant que le
  vote de cet agent soit reproductible.

## 4. Liquidity Agent
- **Responsable :** Validation de la capacité à exécuter un ordre sans slippage.
- **Features surveillées :** Volume, Spread, Slippage estimé, Profondeur du Carnet d'Ordres (Order Book).
- **Sortie :** `[Vote, Confidence]`
- **Réserve mesurée :** aucune de ces quatre entrées n'est alimentée par une source réelle. Prérequis :
  `DerivMarketGateway` (Lot 2).

## 5. Pattern Agent
- **Responsable :** Projection prédictive et analyse vectorielle.
- **Technologies :** Kronos (Forecasting), Embedding FAISS.
- **Features surveillées :** Similarité de forme, Score d'échec/réussite historique.
- **Sortie :** `[Vote, Confidence]`
- **Réserve mesurée :** Kronos prédit sur `np.random.randn` (`providers/kronos_adapter.py:40-41,63-71`) et
  l'index FAISS n'est jamais alimenté (`MemoryManager(` : 0 occurrence). La « similarité de forme » est
  calculée contre du bruit.

## 6. News Agent
- **Responsable :** Filtre macro-économique (Analyse asynchrone).
- **Technologies :** FinGPT, OpenBB.
- **Features surveillées :** Sentiment des news, Événements du calendrier économique.
- **Sortie :** `[Vote, Confidence]`
- **Réserve mesurée :** FinGPT est `[ABANDONNÉ]` (`ADR-002`), aucun remplaçant n'est câblé —
  `MockReasoner()` est injecté en production (`api/deps.py:53`). Cet agent ne lit aucune news.

## 7. Portfolio Agent
- **Responsable :** Diversification et corrélation inter-actifs.
- **Features surveillées :** Corrélation avec les positions ouvertes, Exposition brute et nette.
- **Sortie :** `[Vote, Confidence]`
- **Réserve mesurée :** les positions ouvertes ne remontent jamais — `on_trade` a pour corps `pass`
  (`infrastructure/live/vnpy/execution.py:69`). L'agent raisonne sur un portefeuille vide par construction.

## 8. Execution Agent
- **Responsable :** Microstructure du routage d'ordre.
- **Features surveillées :** Broker API Status, Latence, Taux de "Fill" (exécution).
- **Sortie :** Recommande un type d'ordre (Market, Limit, TWAP).
- **Réserve mesurée :** les trois entrées sont des constantes (`latency_ms = 50.0`,
  `fill_price = Decimal("100.0")`, `BrokerSnapshot(connected=True, gateway="BINANCE")` alors que le broker
  est Deriv — `application/monitoring/engine.py:60-78`).

## Ce que ce document ne promet pas

- **Pas de rentabilité.** Huit agents qui votent ne sont pas huit agents qui gagnent. Aucune validation
  économique n'a été franchie.
- **L'existence des 8 agents n'est pas la décision des 8 agents.** Le code est là, il est appelé, et il
  produit `VERDICT: WAIT | mult=0.0 | conf=0.0`. Ces deux faits ne se contredisent pas : un agent bien
  écrit dont les entrées sont absentes retourne correctement « je ne sais pas ».
- **Une unanimité `WAIT conf=0.0` n'est pas de la prudence.** C'est une absence d'entrée. Un comité
  prudent aurait des avis divergents et une confiance non nulle. Le déblocage passe par le Lot 2 (clés
  `FeatureStore` réellement alimentées par des données de marché) puis le Lot 3 (un seul ATR). Tant que
  ces deux lots ne sont pas faits, augmenter le nombre d'agents ne changera rien au verdict.

