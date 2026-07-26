# Spécifications Fonctionnelles du Dashboard

Ce document définit le cahier des charges du tableau de bord de supervision de l'OS. Il s'agit d'une interface locale, à usage unique, offrant un contrôle absolu sur les différents moteurs de trading.

## 1. Architecture Visée

Le Dashboard s'intègre via le paradigme de Clean Architecture :

```text
[ React (Frontend) ]
        │
    (WebSocket / REST)
        ▼
[ FastAPI (Application Layer) ]
        │
    (Dependency Injection)
        ▼
[ Aegis Domain / Core Engines ]
        │
        ▼
[ Infrastructure (Local DB / Cache) ]
```

## 2. Vues et Composants (Wireframes Textuels)

### 2.1 Vue Trading (Main Center)
**Cartes et Métriques :**
- `Balance Globale` ($)
- `Equity Actuelle` ($)
- `PnL Latent` (Unrealized) / `PnL Réalisé` (Realized)
- `Exposition Globale` (%)

**Tableau des Positions Ouvertes :**
| Symbole | Side | Qty | Entry Price | Current Price | PnL | Action |
|---------|------|-----|-------------|---------------|-----|--------|
| AAPL    | LONG | 10  | 150.00      | 152.50        | +25 | [CLOSE]|

### 2.2 Vue Performance (Analytics)
**Cartes et Graphiques :**
- `Win Rate` (%)
- `Profit Factor` (Somme Gains / Somme Pertes)
- `Sharpe Ratio` / `Sortino Ratio`
- `Max Drawdown` (%)
- `Expectancy` (Gain moyen par trade)
- **Graphique interactif** (Ligne temporelle) : Évolution de l'Equity sur 30j, 90j, YTD.

### 2.3 Vue IA (Council Supervisor)
**Logs et Décisions :**
- Flux en temps réel (WebSocket) des délibérations.
- **Grille des Rapports** :
  - *Macro Analyst* : "Bullish (Confidence: 0.8) - CPI data favorable."
  - *Risk Analyst* : "Neutral (Confidence: 0.9) - VIX normal."
- **Décision Finale (Synthesizer)** : `[GO_LONG] Multiplier: 1.0`

### 2.4 Vue Risque (Risk & Control)
**Alertes et Contrôle :**
- Jauge d'exposition par secteur/actif.
- Jauge de distance au *Max Drawdown Limit*.
- **BOUTON KILL SWITCH (Rouge)** : Coupe toutes les connexions broker, annule les ordres en cours, clôture les positions au marché. (Nécessite une modale de confirmation).

### 2.5 Vue Données (Data & Macro)
- Statut du Data Pipeline (Dernière synchronisation réussie).
- Régime de marché identifié (Trend, Range, Volatile).
- Top 3 News/Sentiments récents.

### 2.6 Vue Journal (Trade History)
- Tableau paginé de l'historique complet des trades.
- Export CSV.

## 3. Fréquence de Rafraîchissement
- **Equity / PnL / Positions** : Temps réel (WebSocket, ≤ 1s).
- **Graphiques de Performance** : Mise à jour quotidienne ou à la clôture d'un trade (REST).
- **Council IA** : Événementiel (Poussé via WebSocket lors de la prise de décision).
