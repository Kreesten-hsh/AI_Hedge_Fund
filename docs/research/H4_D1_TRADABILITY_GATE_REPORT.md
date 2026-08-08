# RAPPORT DU GATE DE TRADABILITÉ ÉCONOMIQUE H4 / D1 (TÂCHE 1)

**Date d'exécution** : 2026-08-07 00:58 UTC
**Péage d'Exécution Aller-Retour Mesuré (ADR 0021)** : **`1.859 bps`** (`0.0001859`)

## 1. GOLD (XAUUSD - DUKASCOPY 11.6 ANS - DONNÉES LONGUES COMPLÈTES)

### 1.1 Granularité Quotidienne D1 (4 229 barres)

| Horizon H (Jours) | Mouvement Moyen | Ratio Couverture vs Péage | % Fenêtres > Péage | n_eff Global | n_eff Train (70%) | n_eff Holdout (30%) | Statut Gate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| H=1d | **52.66 bps** | **28.3x** | 82.6% | 4228.0 | 2960.0 | **1268.0** | **✅ PASS** |
| H=2d | **79.83 bps** | **42.9x** | 96.9% | 2113.5 | 1480.0 | **633.5** | **✅ PASS** |
| H=3d | **101.17 bps** | **54.4x** | 98.3% | 1408.7 | 986.7 | **422.0** | **✅ PASS** |
| H=5d | **135.20 bps** | **72.7x** | 98.9% | 844.8 | 592.0 | **252.8** | **✅ PASS** |

### 1.2 Granularité 4-Heures H4 (25 252 barres)

| Horizon H (Heures) | Mouvement Moyen | Ratio Couverture vs Péage | % Fenêtres > Péage | n_eff Global | n_eff Train (70%) | n_eff Holdout (30%) | Statut Gate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| H=1b (4h) | **18.38 bps** | **9.9x** | 68.3% | 25251.0 | 17676.0 | **7575.0** | **✅ PASS** |
| H=2b (8h) | **27.36 bps** | **14.7x** | 72.1% | 12625.0 | 8838.0 | **3787.0** | **✅ PASS** |
| H=3b (12h) | **34.54 bps** | **18.6x** | 75.3% | 8416.3 | 5892.0 | **2524.3** | **✅ PASS** |
| H=6b (24h) | **52.41 bps** | **28.2x** | 83.2% | 4207.7 | 2946.0 | **1261.7** | **✅ PASS** |
| H=12b (48h) | **79.93 bps** | **43.0x** | 97.1% | 2103.3 | 1473.0 | **630.3** | **✅ PASS** |

---

## 2. INDICES SYNTHÉTIQUES (DERIV NATIF ~365 JOURS - DONNÉES COURTES SÉPARÉES)

> [!IMPORTANT]
> Les indices synthétiques propriétaires Deriv n'existent sur aucune source externe. Leur évaluation est réalisée sur la fenêtre maximale de 365 jours accessible sur l'API.

### 2.1 Crash 1000 Index (`CRASH1000`)

#### D1 (369 barres) :

| Horizon H | Mouvement Moyen | Ratio Couverture | % > Péage | n_eff Global | n_eff Holdout (30%) | Statut Gate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| H=1d | **92.05 bps** | **49.5x** | 99.7% | 365.0 | **109.0** | **✅ PASS** |
| H=2d | **131.14 bps** | **70.5x** | 99.2% | 182.0 | **54.0** | **✅ PASS** |
| H=3d | **160.87 bps** | **86.5x** | 99.4% | 121.0 | **35.7** | **✅ PASS** |
| H=5d | **202.54 bps** | **108.9x** | 99.2% | 72.2 | **21.0** | **❌ FAIL** |

#### H4 (2 200 barres) :

| Horizon H | Mouvement Moyen | Ratio Couverture | % > Péage | n_eff Global | n_eff Holdout (30%) | Statut Gate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| H=1b (4h) | **36.62 bps** | **19.7x** | 96.6% | 2190.0 | **657.0** | **✅ PASS** |
| H=2b (8h) | **53.32 bps** | **28.7x** | 97.7% | 1094.5 | **328.0** | **✅ PASS** |
| H=3b (12h) | **65.47 bps** | **35.2x** | 98.1% | 729.3 | **218.3** | **✅ PASS** |
| H=6b (24h) | **92.41 bps** | **49.7x** | 98.9% | 364.2 | **108.7** | **✅ PASS** |
| H=12b (48h) | **133.87 bps** | **72.0x** | 99.2% | 181.6 | **53.8** | **✅ PASS** |

### 2.2 Boom 1000 Index (`BOOM1000`)

#### D1 (367 barres) :

| Horizon H | Mouvement Moyen | Ratio Couverture | % > Péage | n_eff Global | n_eff Holdout (30%) | Statut Gate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| H=1d | **86.71 bps** | **46.6x** | 98.4% | 365.0 | **109.0** | **✅ PASS** |
| H=2d | **128.53 bps** | **69.1x** | 99.2% | 182.0 | **54.0** | **✅ PASS** |
| H=3d | **162.14 bps** | **87.2x** | 99.2% | 121.0 | **35.7** | **✅ PASS** |
| H=5d | **213.75 bps** | **115.0x** | 99.7% | 72.2 | **21.0** | **❌ FAIL** |

#### H4 (2 200 barres) :

| Horizon H | Mouvement Moyen | Ratio Couverture | % > Péage | n_eff Global | n_eff Holdout (30%) | Statut Gate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| H=1b (4h) | **35.95 bps** | **19.3x** | 96.3% | 2190.0 | **657.0** | **✅ PASS** |
| H=2b (8h) | **50.90 bps** | **27.4x** | 97.9% | 1094.5 | **328.0** | **✅ PASS** |
| H=3b (12h) | **62.55 bps** | **33.6x** | 97.7% | 729.3 | **218.3** | **✅ PASS** |
| H=6b (24h) | **90.11 bps** | **48.5x** | 98.9% | 364.2 | **108.7** | **✅ PASS** |
| H=12b (48h) | **128.13 bps** | **68.9x** | 99.0% | 181.6 | **53.8** | **✅ PASS** |


## 3. CONCLUSION ET VALIDATION DU GATE DE TRADABILITÉ

1. **Gold (XAUUSD)** : Validé avec succès sur D1 et H4. À l'horizon D1 (H=1d), le mouvement moyen est de **52.66 bps**, couvrant **28.3 fois le péage d'exécution** (1.859 bps). Le sous-échantillon Holdout de 30% fournit **$n_{eff, holdout} = 1268.0$ fenêtres quotidiennes indépendantes**, garantissant une puissance de validation robuste.
2. **Crash 1000 / Boom 1000** : Validés sur H4 à H=6b (92.41 bps, couverture 49.7x, $n_{eff, holdout} = 108.7$ fenêtres). Sur D1, l'échantillon natif court de 365 jours laisse $n_{eff, holdout} = 21.0$ fenêtres à H=5d (sous le seuil minimal de 30). L'horizon H4 est donc retenu à titre exclusif pour les synthétiques.

> [!CAUTION]
> **RAPPEL METHODOLOGIQUE (PASS != EDGE)**
> La validation du Gate de Tradabilité signifie uniquement que le mouvement moyen des prix dépasse suffisamment le coût d'exécution (1.859 bps) pour justifier l'initiation d'une recherche d'alpha. Ce résultat NE CONSTITUE EN AUCUN CAS une preuve d'alpha ni un signal prédictif (comme H5 l'était sur M1 avant le rejet de significativité 0/25 dans GOLD-01).
