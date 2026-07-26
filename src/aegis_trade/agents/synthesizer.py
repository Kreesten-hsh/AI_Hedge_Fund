import json
import os
from typing import List

from aegis_trade.domain.reports import ResearchReport
from aegis_trade.domain.decisions import CouncilDecision
from aegis_trade.infrastructure.llm.adapters.base import ILLMProvider
from aegis_trade.infrastructure.llm.metrics import LLMMetrics
import time

class CouncilSynthesizer:
    """
    Dedicated component for LLM synthesis of analyst reports into a final decision.
    Acts as the Lead Portfolio Manager, resolving conflicts and dictating position multipliers.
    """
    def __init__(self, provider: ILLMProvider):
        self.provider = provider
        self.metrics = LLMMetrics.get_instance()
        
    def _read_prompt(self, filepath: str) -> str:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    def synthesize(self, reports: List[ResearchReport], intent: str) -> CouncilDecision:
        """
        Synthesizes multiple analyst reports based on a quantitative intent.
        """
        
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        prompt_path = os.path.join(base_dir, "prompts", "council_v1.md")
        prompt_template = self._read_prompt(prompt_path)
        
        reports_json = json.dumps([
            {"capability": r.capability, "findings": r.data} for r in reports
        ], indent=2)
        
        # Use standard string format with **kwargs
        context = {
            "intent": intent,
            "analyst_reports": reports_json
        }
        
        try:
            rendered_prompt = prompt_template.format(**context)
        except KeyError as e:
            raise ValueError(f"Missing required context variable {e} for prompt {prompt_path}")
        
        start_time = time.perf_counter()
        
        raw_response = self.provider.generate(
            prompt=rendered_prompt,
            system_prompt=""
        )
        
        latency = time.perf_counter() - start_time
        
        try:
            parsed = json.loads(raw_response)
            success = True
        except json.JSONDecodeError as e:
            parsed = {}
            success = False
            
        settings = getattr(self.provider, "settings", None)
        if hasattr(settings, "provider") and not callable(getattr(settings, "provider")):
            provider_name = str(settings.provider)
            model_name = str(settings.model)
            profile_name = str(settings.active_profile)
        else:
            provider_name = "unknown"
            model_name = "unknown"
            profile_name = "unknown"
        
        tokens_estimated = len(rendered_prompt.split()) + len(str(parsed).split()) if success else 0
        
        self.metrics.record_call(
            provider=provider_name,
            model=model_name,
            profile=profile_name,
            duration_ms=latency * 1000,
            cache_hit=False, # We don't cache synthesizer yet, or assume False
            success=success,
            tokens=tokens_estimated
        )
        
        if not success:
            raise ValueError(f"Failed to parse Council JSON response")
            
        return CouncilDecision(
            decision_type=parsed.get("decision_type", "wait"),
            confidence=float(parsed.get("confidence", 0.0)),
            multiplier=float(parsed.get("multiplier", 0.0)),
            reasoning=parsed.get("reasoning", "Parse failure"),
            supporting_reports=reports
        )
