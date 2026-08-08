# Statut d'Intégration de Kronos — Évaluation & Conditions de Réactivation

- **Statut** : SUSPENDU / INACTIF (Conditionnel v2.0)
- **Date** : 2026-08-08
- **Composants concernés** : `src/aegis_trade/providers/kronos/`, `src/aegis_trade/providers/kronos_adapter.py:1-75`, `docs/phase2/KRONOS_MINI_INTEGRATION_SPEC.md`
- **Dépend de** : ADR 0019 (Réfutation Horizon 1-bar), ADR 0031 (Réfutation Crypto & ML Ranking), ADR 0032 (Pivot Pipeline Cognitif v2.0)

---

## 1. Contexte & Historique

Le composant **Kronos** (`src/aegis_trade/providers/kronos/`) est un modèle de fondation de séries temporelles basé sur des architectures deep learning/sequence-to-sequence. Il visait initialement à fournir des prédictions de prix et de trajectoire de court terme.

---

## 2. Décision de Suspension (ADR 0019, 0031, 0032)

À l'issue des campagnes de validation statistique empirique :
1. **Absence d'Alpha Univarié** : À l'instar des modèles GBDT (LightGBM) et des indicateurs techniques classiques, la prédiction numérique brute de trajectoire temporelle sur séries univariées ne franchit pas la barre du péage d'exécution ($1.859\text{ bps}$ sur Gold, $10\text{ bps}$ sur Crypto).
2. **Rejet de l'Horizon Court** (ADR 0019) : L'horizon 1-bar est mathématiquement dominé par le bruit micro-structurel et les coûts de transaction broker.
3. **Alignement avec la Directive AGENTS.md §2 et §6** : Interdiction de développer ou maintenir en statut actif des composants spéculatifs n'apportant pas de valeur mesurable immédiate.

En conséquence, l'intégration de Kronos est **SUSPENDUE** et le module `kronos_adapter.py` demeure désactivé du chemin d'exécution principal.

---

## 3. Conditions Formelles de Réactivation Futurs (Roadmap Post-Demo)

Le composant Kronos ne pourra être réactivé dans l'architecture Aegis Quant OS qu'aux conditions strictes et cumulatives suivantes :

1. **Publication d'un ADR Dédié** : Rédaction d'un nouvel ADR réorientant l'utilisation de Kronos non pas vers la prédiction univariée de prix, mais vers l'extraction de représentations d'état (embeddings temporels sémantiques).
2. **Validation d'un Spearman Rank IC Out-Of-Sample** $\ge 0.05$ ($|t| > 2.0$) mesuré avec déduction préalable des péages d'exécution broker.
3. **Approbation de l'Agent Cognitif Sémantique** : Intégration de l'output de Kronos en tant que signal contextuel secondaire consommé par le Module 2 (Agent Cognitif), sans droit de soumission directe d'ordre au broker.

En l'absence de ces conditions, le code dans `src/aegis_trade/providers/kronos/` reste conservé à titre de référence et d'archive de recherche, conformément à l'ADR 0032.
