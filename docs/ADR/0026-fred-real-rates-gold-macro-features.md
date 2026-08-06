# ADR 0026 — Intégration des Taux Réels 10 ans FRED (DFII10) via l'Extension OpenBB FRED

- **Statut** : ACCEPTÉ
- **Date** : 2026-08-06
- **Contexte technique** : `src/aegis_trade/infrastructure/data/providers/openbb_provider.py`, `pyproject.toml`, `docs/refont/BUILD_VS_REUSE.md`
- **Dépend de** : ADR 0025 (rejet des features techniques simples sur Gold M1)
- **Résout** : Levée de la restriction "Mission C" et intégration unifiée de la variable macroéconomique fondamentale de l'Or (`DFII10`)

## Contexte

Après le rejet des 25 features techniques usuelles (RSI, EMA, MACD, ATR) sur Gold M1 (ADR 0025), la recherche d'alpha s'oriente vers des facteurs fondamentalement explicatifs du prix de l'Or.

Son coût d'opportunité principal est le **taux d'intérêt réel** (le rendement d'une obligation d'État sans risque ajusté de l'inflation anticipée) :
$$\text{Taux Réel} = \text{Taux Nominal (US10Y)} - \text{Inflation Anticipée (Breakeven Inflation)}$$

Le Taux Réel 10 ans US (série FRED `DFII10` - TIPS) mesure directement ce coût d'opportunité.

---

## 1. Audit Écosystème & Architecture à Source Unique

Conformément à la Règle 4 (*"Aucune duplication. Une seule implémentation"*), l'audit de l'architecture existante a établi que :
- `OpenBBDataProvider` est le provider unifié de données de marché du projet (`openbb>=4.0.0`).
- Au lieu de créer un second provider de données macro (`fredapi` / `FredDataProvider`), l'extension officielle **`openbb-fred`** permet d'interroger directement la Réserve Fédérale de St. Louis via l'interface unifiée `obb.economy.fred_series(symbol='DFII10', provider='fred')`.
- Cela élimine toute tentative de router les séries FRED via Yahoo Finance (`yfinance`), tout en conservant une seule classe de provider de données externes (`OpenBBDataProvider`).

---

## 2. Décisions & Implémentation

1. **Intégration d'openbb-fred** :
   - Extension `openbb-fred` ajoutée dans `pyproject.toml`.
2. **Implémentation unifiée dans `OpenBBDataProvider`** :
   - Méthode `fetch_macro(symbol, start, end)` implémentée dans [src/aegis_trade/infrastructure/data/providers/openbb_provider.py](file:///mnt/WindowsData/AI_Hedge_Fund/src/aegis_trade/infrastructure/data/providers/openbb_provider.py) via `obb.economy.fred_series`.
3. **Protocole de validation** :
   - Conserver la séparation stricte : d'abord le pipeline d'ingestion/alignement temporel des données FRED + Gold M1, puis soumission des nouvelles features macro aux tests de significativité (`domain/tradability` et `run_feature_research.py`).
