import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List

from aegis_trade.agents.base import ResearchAgent
from aegis_trade.infrastructure.llm.adapters.base import ILLMProvider
from aegis_trade.infrastructure.cache.decision_cache import DecisionCache
from aegis_trade.infrastructure.llm.metrics import LLMMetrics
from aegis_trade.domain.reports import ResearchReport, ExecutionMetadata, ExecutionResult

class AgentRunner:
    """
    Central execution engine for Research Agents.
    Responsible for template rendering, LLM calls, and telemetry generation.
    """
    def __init__(self, provider: ILLMProvider, use_cache: bool = True):
        self.provider = provider
        self.use_cache = use_cache
        self.cache = DecisionCache() if use_cache else None
        self.metrics = LLMMetrics.get_instance()

    def _read_prompt(self, filepath: str) -> str:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    def execute(self, agent: ResearchAgent, context: Dict[str, Any]) -> ExecutionResult:
        """Executes a single agent and returns a telemetried ExecutionResult."""
        prompt_template = self._read_prompt(agent.prompt_path)
        
        # Render prompt using standard Python string formatting
        try:
            rendered_prompt = prompt_template.format(**context)
        except KeyError as e:
            raise ValueError(f"Missing required context variable {e} for prompt {agent.prompt_path}")

        start_time = time.perf_counter()
        
        cache_context = {"prompt": rendered_prompt, "agent_capability": agent.capability}
        cache_hit = False
        
        try:
            cached_response = self.cache.get(cache_context) if self.use_cache else None
            if cached_response:
                raw_response = cached_response
                cache_hit = True
            else:
                raw_response = self.provider.generate(
                    prompt=rendered_prompt,
                    system_prompt="" # Externalized prompts contain the system context as well
                )
                if self.use_cache:
                    self.cache.set(cache_context, raw_response)
                    
            parsed_data = json.loads(raw_response)
            success = True
            error_msg = ""
        except Exception as e:
            parsed_data = {}
            success = False
            error_msg = str(e)
            
        latency = time.perf_counter() - start_time
        
        # Record metrics using LLM properties
        settings = getattr(self.provider, "settings", None)
        if hasattr(settings, "provider") and not callable(getattr(settings, "provider")):
            provider_name = str(settings.provider)
            model_name = str(settings.model)
            profile_name = str(settings.active_profile)
        else:
            provider_name = "unknown"
            model_name = "unknown"
            profile_name = "unknown"
        
        # Estimate tokens naively (for local tracking without tokenizer)
        tokens_estimated = len(rendered_prompt.split()) + len(str(parsed_data).split()) if success else 0
        
        self.metrics.record_call(
            provider=provider_name,
            model=model_name,
            profile=profile_name,
            duration_ms=latency * 1000,
            cache_hit=cache_hit,
            success=success,
            tokens=tokens_estimated
        )
        
        report = ResearchReport(
            capability=agent.capability,
            data=parsed_data
        )
        
        metadata = ExecutionMetadata(
            agent_capability=agent.capability,
            model_name=model_name,
            latency_seconds=latency,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            success=success,
            error_message=error_msg
        )
        
        return ExecutionResult(report=report, metadata=metadata)

    def execute_many(self, agents: List[ResearchAgent], context: Dict[str, Any]) -> List[ExecutionResult]:
        """
        Executes multiple agents sequentially.
        API is prepared for future parallelization (ThreadPoolExecutor).
        """
        results = []
        for agent in agents:
            results.append(self.execute(agent, context))
        return results
