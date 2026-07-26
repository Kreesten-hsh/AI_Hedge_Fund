# ADR 0004: Abstract LLM Provider

## Status
Accepted

## Context
Aegis Quant OS s'appuie sur des modèles d'IA générative (LLM) pour la prise de décision. Le paysage des LLMs évolue à une vitesse fulgurante (Llama, GPT, Claude, DeepSeek). S'attacher à un client spécifique (ex: bibliothèque `openai` ou appel API statique vers Ollama) rendrait l'OS obsolète en quelques mois.

## Decision
Nous créons une interface abstraite `ILLMProvider` et nous l'instancions via une `LLMProviderFactory`.

## Rationale
- Les agents métier (`AgentRunner`, `CouncilSynthesizer`) n'ont besoin que d'une fonction `generate(prompt)`. Ils n'ont que faire de savoir si l'inférence se fait localement sur un GPU (vLLM/Ollama) ou via le Cloud (OpenAI).
- La Factory permet d'injecter dynamiquement le bon provider en se basant sur le fichier de configuration `llm.yaml`.

## Consequences
- Impossible d'importer des SDK spécifiques (comme `openai`) dans le dossier `agents/`.
- Chaque nouvelle intégration nécessite uniquement la création d'un Adapter héritant de `ILLMProvider`.
