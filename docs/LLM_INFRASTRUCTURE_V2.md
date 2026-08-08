# LLM Infrastructure v2 — Sélection du modèle local (Sprint pivot cognitif)

> Répond à "quel modèle et pourquoi" avant l'implémentation. Complète `infrastructure/llm/` existant (interface `ILLMProvider`, `LLMProviderFactory`) sans le remplacer.

## 1. Contrainte matérielle de référence

Dell Vostro 15-3568, i3-6006U (2 cœurs / 4 threads, ~2.0 GHz, pas d'AVX-512), 12 Go RAM, disque dur mécanique (HDD). Le risque d'ingénierie dominant sur cette machine n'est pas le débit d'inférence token par token, mais la **pagination mémoire (swap) sur HDD** si la RAM allouée dépasse le disponible — un swap HDD peut faire chuter n'importe quel modèle, quelle que soit sa taille.

## 2. Budget de latence — pourquoi le débit brut n'est pas le facteur limitant

Le pipeline est verrouillé sur H4/D1 (ADR 0029) : une décision au maximum toutes les 4 heures (14 400 s) par instrument, deux instruments en parallèle (Gold, Crash/Boom).

| Débit d'inférence (hypothèse basse) | Sortie 500 tokens | Marge restante sur le cycle H4 |
|---|---|---|
| 1 tok/s | ~500 s (~8 min) | > 99 % du budget |
| 0.3 tok/s (dégradé) | ~1 667 s (~28 min) | > 96 % du budget |

Conclusion : même un débit très dégradé reste largement dans le budget. **Le facteur décisif est donc la RAM disponible, pas la vitesse.**

## 3. Modèles évalués

### `llama3.2:1b`
- Empreinte mémoire estimée : ~1.3–1.5 Go.
- Élimine quasiment tout risque de swap.
- Risque identifié : sous-dimensionné pour la synthèse tactique (justification en langage naturel) et la lecture de contexte RAG (historique injecté depuis `FaissVectorStore`). Un modèle 1B a un taux d'échec de structuration JSON plus élevé sur des sorties contraintes (Entry/SL/TP) — un échec de parsing bloquerait le démon 24/7 sur ce cycle.

### `llama3.1:8b` (quantification `Q4_K_M`) — **retenu comme modèle primaire**
- Empreinte mémoire estimée : ~4.7 Go (`Q4_K_M` est le point d'équilibre qualité/taille standard pour ce modèle).
- Budget RAM disponible sur la machine : OS (~2 Go) + Python/FAISS/dépendances (~1 Go) ≈ 3 Go retenus, ~9 Go restants — marge de sécurité de plus de 4 Go au-dessus de l'empreinte estimée du modèle.
- **Ces trois chiffres (2 Go, 1 Go, 4.7 Go) sont des estimations d'ingénierie, pas des mesures.** Ils doivent être confirmés par un test réel sur la machine avant d'être considérés comme acquis (§5).

## 4. Décision

- **Modèle primaire à tester en premier** : `llama3.1:8b` / `Q4_K_M`.
- **Fallback local** : `llama3.2:1b`, activé uniquement si le 8B produit des timeouts réels dépassant le budget du cycle H4 (mesuré, pas anticipé) — pas comme choix par défaut.
- **Fallback cloud gratuit (Groq / Gemini)** : documenté, non activé par défaut. À n'envisager que si le test empirique du 8B révèle un swap HDD persistant que le fallback 1B ne résout pas non plus (auquel cas la contrainte n'est plus la taille du modèle mais l'architecture machine elle-même).

## 5. Protocole de validation empirique — préalable obligatoire avant intégration

Avant toute intégration dans le pipeline Module 2, Antigravity doit produire un rapport de mesure réelle (pas une estimation) suivant le même format que `docs/archive/KRONOS_EVALUATION_REPORT.md` :

| À mesurer | Méthode |
|---|---|
| RAM effectivement consommée par `ollama run llama3.1:8b` en régime établi | `free -h` avant/pendant inférence |
| Swap déclenché ou non | `vmstat` ou `free -h` colonne swap, avant/pendant |
| Temps de génération réel pour une sortie JSON structurée de taille comparable à celle attendue en production | Chronométrage direct, pas estimé |
| Taux de succès du parsing JSON sur N générations (N ≥ 20) | Script de test dédié, taux rapporté explicitement |

Tant que ce tableau n'est pas rempli avec des chiffres mesurés, `llama3.1:8b` reste une décision **provisoire**, pas actée en dur dans le code.
