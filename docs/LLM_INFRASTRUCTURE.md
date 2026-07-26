# LLM Infrastructure Architecture (INFRA-01)

The LLM Infrastructure in Aegis Quant OS strictly adheres to **Clean Architecture** principles. The business domain (`engine`, `agents`) is entirely decoupled from the concrete implementation of the Language Models (e.g., Ollama, OpenAI, vLLM).

## Architecture Diagram

```text
       Domain Layer (Agents)
                │
                ▼
        ILLMProvider (Interface)
                │
                ▼
       LLMProviderFactory
                │
      ┌─────────┴─────────┐
      ▼                   ▼
OllamaAdapter         OpenAIAdapter
      │                   │
      ▼                   ▼
Local Inference      Cloud Inference
```

## Core Components

### 1. `config/llm.yaml`
The single source of truth for the active LLM provider, models, performance profiles, and parameters. It allows hot-swapping models without code changes.

### 2. `LLMSettings`
Responsible for loading the YAML file, ensuring configuration integrity with strong validations. Returns parsed configurations and raises `ConfigurationError` if parameters are invalid.

### 3. `DecisionCache`
A generic hashing cache used to skip expensive LLM calls when the input context is identical to a prior execution.

### 4. `LLMMetrics`
Provides structured JSON logging. It tracks metrics such as cache hits, inference latency, and estimated token counts to facilitate performance profiling and dashboard integrations.

### 5. Providers & Factory
All new LLM integrations (like Claude or vLLM) only require:
1. Creating a new adapter inheriting from `ILLMProvider`.
2. Registering the adapter inside `LLMProviderFactory`.

The `AgentRunner` and `CouncilSynthesizer` rely exclusively on `ILLMProvider` and are unconcerned with whether the model is local or remote.
