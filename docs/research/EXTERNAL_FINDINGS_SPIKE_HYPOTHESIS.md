# Synthèse d'étude externe — Analyse statistique de 15M de ticks sur Deriv Boom/Crash 1000

- **Auteur** : Oheneba Berko (@shiekwaku100 / Orphy123)
- **Titre** : *"I Analyzed 15 Million Ticks of Deriv Synthetic Data. The Edge Did Not Survive The Costs."*
- **Date de publication** : 24 avril 2026
- **URL de l'article** : [Medium article](https://medium.com/@shiekwaku100/i-analyzed-15-million-ticks-of-deriv-synthetic-data-the-edge-did-not-survive-the-costs-5e1e85481c4d)
- **Dépôt GitHub public** : [Orphy123/deriv-research](https://github.com/Orphy123/deriv-research)
- **Statut de vérification** : Dépôt GitHub cloné et inspecté par nos soins (`PROTOCOL.md`, `FINDINGS.md`, `PUBLICATION_WRITEUP.md`, `data/analysis/*/regimes/VERDICT.md`, scripts Python et primitives C).

---

## 1. Clause de non-fiabilité (Disclaimer)

> [!CAUTION]
> Ce document rapporte et analyse une étude externe indépendante non publiée dans une revue à comité de lecture. Bien que le dépôt GitHub ait été intégralement audité et son code vérifié, cette source externe doit être traitée comme un **indice empirique complémentaire** corroborant nos propres mesures (ADR 0019, ADR 0024), et **jamais comme une preuve autosuffisante**.

---

## 2. Ce qui a été vérifié par nos soins vs ce qui est rapporté par la publication

### 2.1 Éléments directement vérifiés par inspection du code et des artefacts (Repository GitHub)

- **Protocole pré-enregistré (`PROTOCOL.md`)** : Engagé le 18 avril 2026 avec 4 portes d'arrêt explicites (K1: durée médiane de régime HMM $\ge 45$ min ; K2: $|ACF(1)| \ge 0.15$ sur le résidu de dérive ; K3: dérive net d'au moins 1430 points ; K4: Sharpe walk-forward $> 1.0$).
- **Arrêt strict au Step 2 (`VERDICT.md`)** : Les artefacts `data/analysis/Crash_1000_Index/regimes/VERDICT.md` et `Boom_1000_Index/regimes/VERDICT.md` confirment que le script `scripts/analyze_regimes.py` a déclenché le kill au Step 2 pour les deux symboles sans exécuter la suite ni réajuster les seuils.
- **Qualité du code source** : Implémentation en fonctions pures (`src/regime.py`), HMM gaussien à 2 états écrit en NumPy pur (Baum-Welch + Viterbi) pour éviter les dépendances externes, correction d'échantillon effectif et masquage explicite des ticks de spike (`|Δprice| > 420` pts).
- **Règles d'exclusion du p-hacking** : Séparation stricte entre le test principal (Crash 1000, 10k threshold, H1) et les tests exploratoires (Boom 1000, H4, D1). Les résultats exploratoires ne peuvent pas annuler un arrêt du test principal.

### 2.2 Éléments rapportés par l'auteur (données brutes non re-téléchargées par nous)

- **Périmètre du jeu de données** : 15,18 millions de ticks sur 90 jours (18 janvier au 18 avril 2026), capturés en temps réel via Deriv MT5 Demo (`copy_ticks_range`). Boom 1000 : 7 677 891 ticks ; Crash 1000 : 7 509 682 ticks.
- **Mesure de coût MT5 CFD** : Écart spread médian de ~1430 points sur MT5 CFD.

> [!NOTE]
> **Attention sur le modèle de coût** : L'étude de Berko mesure le coût en *points de spread CFD MT5* (~1430 points), tandis que notre architecture AEGIS QUANT OS négocie via l'API Deriv Multipliers avec un modèle de commission mesuré à **0.745 bps sur Crash** et **1.063 bps sur Boom** (ADR 0021). Les unités ne sont pas directement comparables, mais l'impact économique est identique : le péage absorbe la totalité de la dérive observée.

---

## 3. Synthèse des résultats de l'étude externe

### 3.1 Hypothèse 1 : Post-Spike Drift Capture (PSDC) — RÉFUTÉE

L'hypothèse selon laquelle l'apparition d'un spike laisserait une dérive statistique exploitable dans les 50 à 600 ticks suivants est falsifiée :
- **Processus de Poisson sans mémoire** : Le test de Kolmogorov-Smirnov contre une loi exponentielle ne permet pas de rejeter l'hypothèse de mémoire nulle ($p = 0.26$ à $0.35$ au seuil 10k). L'autocorrelation à lag-1 des inter-arrivées est quasi-nulle ($-0.006$ Boom, $+0.0006$ Crash).
- **Fenêtres post-spike vs fenêtres aléatoires** : Sur 16 combinaisons de fenêtres (50, 100, 300, 600 ticks) $\times$ symboles $\times$ seuils, **aucune comparaison ne montre de différence statistiquement significative à 5 %** (p-values de Welch entre 0.30 et 0.97).
- **Rendement net négatif** : La dérive brute moyenne sur 300-600 ticks est inférieure au spread de franchissement.

### 3.2 Hypothèse 2 : Détection de régimes de dérive horaire (Phase 0.5) — RÉFUTÉE

L'hypothèse selon laquelle la dérive inter-spike présenterait une persistance de régime à l'échelle horaire est falsifiée à la porte K2 :
- **Durée des états HMM (K1 - PASS)** : La durée médiane des états de variance est de 173.5 min (Crash) et 596.5 min (Boom), franchissant le seuil de 45 min.
- **Autocorrélation du résidu de dérive (K2 - KILL)** : L'autocorrélation lag-1 du résidu horaire de dérive (net de l'effet des spikes) est de **$-0.041$ pour Crash 1000** et **$-0.018$ pour Boom 1000**, toutes deux comprises dans la bande de bruit blanc à 95 % ($\pm 0.042$).
- **Marge d'arrêt** : Le seuil exigé de $|ACF(1)| \ge 0.15$ est manqué d'un facteur 4x sur Crash et 8x sur Boom.

---

## 4. Évaluation méthodologique de l'étude

Notre évaluation de ce dépôt GitHub est **très favorable** :
1. **Rigueur scientifique** : Absence de marketing, de vente de signaux ou de formation. Le dépôt est structuré comme un artefact de recherche reproductible avec code modulaire et tests d'hypothèses rigoureux (KS-test, Welch t-test, régression OLS sur résidus, HMM Baum-Welch).
2. **Discipline de pré-enregistrement** : Les critères d'arrêt ont été commités *avant* l'analyse et respectés à la lettre lorsque les données ont invalidé l'hypothèse.
3. **Alignement d'ingénierie** : Les principes de développement utilisés (fonctions pures, pas d'optimisation a posteriori des seuils après échec) rejoignent la doctrine d'AEGIS QUANT OS.

---

## 5. Convergence des preuves (Triple validation indépendante)

Trois travaux indépendants, s'appuyant sur trois approches et trois jeux de données distincts, convergent désormais vers **la même conclusion** :

| Travail / Source | Méthodologie | Périmètre / Données | Verdict sur l'edge court terme |
|---|---|---|---|
| **SIG-01 (ADR 0019)** | Modèle Oracle + Budget économique | 75 000 barres M1, Horizon 1 barre | **RÉFUTÉ** ($5.8\%$ tradable, coût $4.8\times$ budget) |
| **SIG-02 (ADR 0024)** | ML LightGBM + Décomposition P&L + Alpha Research IC Spearman | 75 000 barres M1, 23 features, Horizons 5 & 10 | **RÉFUTÉ** ($0/25$ features significatives, $t \in [-0.71, +0.54]$) |
| **Berko (2026)** | Analyse Poisson de ticks + Test de Welch post-spike + HMM / ACF | 15.18M ticks, 90 jours, Horizons 50-600 ticks & H1 | **RÉFUTÉ** (Processus sans mémoire, $ACF(1) \in [-0.041, -0.018]$) |

> [!IMPORTANT]
> **Conclusion** : À court terme (du tick à l'horizon 10 barres M1), les processus Crash 1000 et Boom 1000 ne présentent **aucun signal directionnel exploitable** en mesure de surmonter la structure de coût de transaction.

---

## 6. Pistes non couvertes par l'étude (Candidats potentiels pour un futur SIG-03)

Si la recherche sur les indices synthétiques devait être rouverte dans le cadre d'un futur jalon (SIG-03), l'étude de Berko et nos propres travaux identifient les axes suivants comme **non testés** :

1. **Horizons de temps supérieurs** : Régimes de tendance à l'échelle H4 ou Daily (conditionnement sur de grands ensembles de données).
2. **Interactions non-linéaires** : Modélisation non-linéaire complexe des relations dérive-spike (vs la régression linéaire simple testée dans Berko 2026).
3. **Dépendance inter-symboles** : Détection de corrélation ou de co-intégration entre différents indices synthétiques (ex: Crash 1000 vs Boom 1000 vs Crash 500).

*Remarque : Aucune de ces pistes n'est garantie d'aboutir. Elles constituent simplement la liste exhaustive des fenêtres non réfutées à ce jour.*
