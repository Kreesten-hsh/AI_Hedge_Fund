# ADR 0026 — Intégration des Taux Réels 10 ans FRED (DFII10) pour l'Analyse Macroéconomique de l'Or

- **Statut** : ACCEPTÉ
- **Date** : 2026-08-06
- **Contexte technique** : `src/aegis_trade/infrastructure/data/providers/fred_provider.py`, `src/aegis_trade/infrastructure/data/providers/openbb_provider.py`, `pyproject.toml`, `docs/refont/BUILD_VS_REUSE.md`
- **Dépend de** : ADR 0025 (rejet des features techniques simples sur Gold M1)
- **Résout** : Levée de la restriction "Mission C" et intégration de la variable macroéconomique fondamentale de l'Or (`DFII10`)

## Contexte

Après le rejet des 25 features techniques usuelles (RSI, EMA, MACD, ATR) sur Gold M1 (ADR 0025), la recherche d'alpha s'oriente vers des facteurs fondamentalement explicatifs du prix de l'Or.

Historiquement, l'Or est un actif de réserve de valeur non rémunéré. Son coût d'opportunité principal est le **taux d'intérêt réel** (le rendement d'une obligation d'État sans risque ajusté de l'inflation anticipée) :
$$\text{Taux Réel} = \text{Taux Nominal (US10Y)} - \text{Inflation Anticipée (Breakeven Inflation)}$$

Jusqu'alors, le projet limitait son abstraction macro à "Mission C" (DXY brut et US10Y nominal). Or :
1. **Le DXY (Dollar Index)** reflète la force relative du USD contre un panier de devises fiat (principalement l'EUR), ce qui en fait un proxy indirect et bruité de l'Or.
2. **Le US10Y (Taux Nominal)** ne prend pas en compte les anticipations d'inflation : un taux nominal qui monte en période de forte inflation peut correspondre à des taux réels en baisse (favorable à l'Or).
3. **Le Taux Réel 10 ans US (série FRED `DFII10` - TIPS)** mesure directement le véritable coût d'opportunité de l'Or.

## Décisions et Implémentation

1. **Adoption du client `fredapi`** (mortada/fredapi) :
   - Ajouté à `pyproject.toml`.
   - Documenté dans `docs/refont/BUILD_VS_REUSE.md`.
2. **Création du `FredDataProvider`** (`src/aegis_trade/infrastructure/data/providers/fred_provider.py`) :
   - Permet l'extraction directe des séries macroéconomiques officielles de la Fed de St. Louis (dont `DFII10`).
3. **Extension du `OpenBBDataProvider`** (`src/aegis_trade/infrastructure/data/providers/openbb_provider.py`) :
   - Prise en charge des symboles `DFII10` et `REAL_RATE_10Y`.
4. **Protocole de validation** :
   - Ne pas lancer la mesure macro prématurément : finaliser le pipeline d'ingestion/alignement temporel avant de soumettre les features macro au Gate de Tradabilité et à `run_feature_research.py`.
