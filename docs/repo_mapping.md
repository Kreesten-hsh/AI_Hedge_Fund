# Aegis Quant OS - External Repositories Mapping

This document tracks the mapping between the 6 benchmark repositories and the Aegis Quant OS architecture. The goal is to identify which modules from these repositories can be integrated directly (or adapted) without reinventing the wheel, particularly for Phase 6 (Multi-Agent & ML).

| Repository | Focus Area | Reusable Module / Concept | Target Aegis Phase | Target File / Module in `src/aegis_trade/` |
| :--- | :--- | :--- | :--- | :--- |
| **The-Swarm-Corporation/AutoHedge** | Multi-Agent Swarm | `Director Agent`, `Risk Manager Agent` architecture | Phase 6 (Agents) | `src/aegis_trade/agents/director.py` |
| **TauricResearch/TradingAgents** | Collaborative LLM Debate | Agent debate protocols (Bull vs Bear), LLM structured communication | Phase 6 (Agents) | `src/aegis_trade/agents/researcher.py` |
| **HKUDS/Vibe-Trading** | NLP to Trading | Natural language ingestion to quantitative strategy formulation | Phase 6 (Agents) | `src/aegis_trade/agents/nlp_router.py` |
| **Fincept-Corporation/FinceptTerminal**| Institutional UI / Real-time | C++ / Qt6 or Python market data streaming analytics UI concepts | Phase 7 (UI/Monitoring)| `src/aegis_trade/ui/dashboard/` |
| **microsoft/qlib** | AI Quantitative Investment | Alpha model architectures, robust dataset normalization, and ML models | Phase 2 (ML Models) | `src/aegis_trade/ml/models/qlib_adapter.py` |
| **AI4Finance-Foundation/FinGPT** | Financial LLMs | Pre-trained financial sentiment analysis models and prompt engineering | Phase 6 (NLP) | `src/aegis_trade/nlp/sentiment.py` |

## Integration Principles ("Trading First")

1. **No Code Copy-Pasting Without Execution:** We only integrate a module if it serves an immediate execution need.
2. **Event-Driven Compatibility:** Any external module integrated must plug into the `aegis_trade.engine` via our event bus (e.g. producing a `SignalEvent`).
3. **Data Dependency:** External models (like Qlib or FinGPT) will consume data from `DatasetRepository`.
