# Infrastructure LLM Locale V2.0 — Architecture & Protocole de Validation

- **Statut** : SPÉCIFICATION TECHNIQUE V2.0
- **Date** : 2026-08-08
- **Composants clés** : `src/aegis_trade/infrastructure/llm/adapters/ollama_adapter.py`, `src/aegis_trade/infrastructure/llm/factory.py`, `src/aegis_trade/infrastructure/llm/settings.py`, `src/aegis_trade/infrastructure/cache/decision_cache.py`, `config/llm.yaml`
- **Dépend de** : ADR 0004 (Abstraction Provider LLM), ADR 0005 (Decision Cache), ADR 0032 (Pivot Pipeline Cognitif v2.0)

---

## 1. Contexte & Principes Directeurs

L'infrastructure LLM d'Aegis Quant OS v2.0 héberge le moteur de raisonnement sémantique local de l'Agent Cognitif (Module 2). Elle s'appuie sur deux piliers d'ingénierie stricts :

1. **Clean Architecture & Inversion de Dépendance** : Le domaine fonctionnel (`engine/`, `domain/`) ne dépend d'aucun moteur d'inférence concret. Il interagit exclusivement avec l'interface `ILLMProvider` via la `LLMProviderFactory` (`src/aegis_trade/infrastructure/llm/factory.py:1-50`).
2. **Sécurisation du Chemin Critique (Règle 2)** : Le modèle LLM **n'intervient JAMAIS dans la boucle déterministe d'exécution en temps réel**. L'Agent Cognitif opère en asynchrone pour soumettre une *intention de trade*. La validation du risque, l'échéancier des ordres et l'application des vétos déterministes restent intégrés dans l'orchestrateur déterministe (`src/aegis_trade/engine/orchestrator.py:1-120`).

---

## 2. Cartographie de l'Infrastructure LLM Local

```text
               ┌──────────────────────────────────────────┐
               │    Agent Cognitif Sémantique (Module 2)  │
               └────────────────────┬─────────────────────┘
                                    │
                                    ▼
                         ILLMProvider (Interface)
                                    │
                                    ▼
                       LLMProviderFactory (Factory)
                                    │
               ┌────────────────────┴────────────────────┐
               ▼                                         ▼
     OllamaAdapter (Local)                     vLLMAdapter (High-Throughput)
(src/.../ollama_adapter.py:1-110)           (src/.../vllm_adapter.py)
               │                                         │
               ▼                                         ▼
   Serveur Ollama Local                      Serveur vLLM GPU Local
 (llama3.1 / qwen2.5-coder)                (qwen2.5-7b / deepseek-r1)
```

---

## 3. Paramétrage & Budgets de Ressources (`config/llm.yaml`)

Configuration centralisée de la couche d'inférence locale :

```yaml
llm:
  active_provider: "ollama"
  timeout_seconds: 30.0
  max_retries: 3
  
  providers:
    ollama:
      base_url: "http://localhost:11434"
      model: "qwen2.5:7b-instruct-q4_K_M"
      temperature: 0.1
      top_p: 0.9
      context_window: 8192
      token_budget_per_call: 1024

    vllm:
      base_url: "http://localhost:8000/v1"
      model: "Qwen/Qwen2.5-7B-Instruct"
      temperature: 0.1
      max_tokens: 1024

cache:
  enabled: true
  strategy: "sha256_context_exact"
  ttl_seconds: 300
```

### Directives d'Optimisation :
- **Budget de jetons** : Limité à 1024 jetons en sortie pour forcer un raisonnement synthétique et des réponses JSON structurées sans bavardage.
- **Cache de décision** (`src/aegis_trade/infrastructure/cache/decision_cache.py:1-80`) : Déduplication immédiate si le contexte d'entrée (marché + mémoire RAG) est identique à une exécution récente (< 5 min).

---

## 4. Isolation du Chemin Critique d'Exécution

```text
[Signal Sémantique / Prompt]
         │
         ▼
 ┌────────────────┐
 │ Agent Cognitif │ ──(Inférence Asynchrone ~2-5s)──> [Intention de Trade JSON]
 └────────────────┘                                           │
                                                              ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                       Orchestrateur Déterministe                            │
 │  1. Validation du Format & Contrat (Pydantic / Domain schema)               │
 │  2. Évaluation RiskGate (Drawdown, Capital Limits)                          │
 │  3. Veto MultiAgentCouncil (Liquidity/Execution threshold >= 0.8)          │
 │  4. Soumission des Ordres au Broker (vnpy / Deriv Gateway)                  │
 └─────────────────────────────────────────────────────────────────────────────┘
```

Si le LLM subit une latence excessive (> 30s) ou génère un JSON invalide, l'Orchestrateur Déterministe rejette immédiatement la demande et maintient l'état du portefeuille neutre.

---

## 5. Protocole de Validation LLM (§5)

Avant l'activation de tout nouveau modèle local dans le pipeline cognitif, ce dernier doit être évalué via le protocole formel ci-dessous.

> [!NOTE]
> Un script de mesure ponctuel isolé (ex: `scripts/benchmark_llm_inference.py`) peut être utilisé pour exécuter ce banc d'essai sans polluer le code de production.

### Matrice d'Évaluation du Modèle LLM Local

| Critère d'Évaluation | Métrique / Indice | Seuil de Tolérance V2.0 | Méthode de Mesure | Statut / Preuve |
| :--- | :--- | :--- | :--- | :--- |
| **Latence d'Inférence** | Latence p95 sur 50 requêtes | $\le 5.0\text{ secondes}$ | `LLMMetrics` / bench script | Testé via `OllamaAdapter` |
| **Consommation VRAM** | Empreinte mémoire GPU | $\le 10\text{ Go VRAM}$ | `nvidia-smi` / `rocm-smi` | Profiling local |
| **Conformité JSON** | Taux de réponses au format valide | $100\%$ ($50/50$ requêtes) | Validation Pydantic schema | Strict zero-error |
| **Répétabilité Décisionnelle** | Consistance à $T=0.1$ | $\ge 95\%$ d'accord | Tri des réponses identiques | Bench prompt répétitif |
| **Débit d'Inférence** | Jetons par seconde (tok/s) | $\ge 25\text{ tok/s}$ | Benchmark Ollama / vLLM | Stream token counting |

Tout modèle ne satisfaisant pas à 100% au seuil de conformité JSON ou dépassant le SLA de latence de 5.0s est automatiquement disqualifié du pipeline de production.
