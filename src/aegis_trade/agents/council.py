import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, List

from aegis_trade.domain.reports import ResearchReport, ExecutionResult, ExecutionMetadata
from aegis_trade.domain.decisions import CouncilDecision
from aegis_trade.agents.registry import AgentRegistry
from aegis_trade.agents.runner import AgentRunner
from aegis_trade.agents.synthesizer import CouncilSynthesizer
class CouncilOrchestrator:
    """
    Pure business orchestration rule. 
    Retrieves agents, executes them via the Runner, and triggers the Synthesizer.
    """
    def __init__(self, registry: AgentRegistry, runner: AgentRunner, synthesizer: CouncilSynthesizer):
        self.registry = registry
        self.runner = runner
        self.synthesizer = synthesizer

    def generate_decision(self, context: Dict[str, Any], intent: str) -> CouncilDecision:
        """
        Executes all registered analysts on the context and synthesizes their reports.
        """
        agents = self.registry.list_agents()
        
        # Execute agents via the Runner (returns List[ExecutionResult])
        results: List[ExecutionResult] = self.runner.execute_many(agents, context)
        
        # Extract pure domain reports, filtering out failures
        valid_reports = [res.report for res in results if res.metadata.success]
        
        if not valid_reports:
            return CouncilDecision(
                decision_type="wait",
                confidence=0.0,
                multiplier=0.0,
                reasoning="All analysts failed to produce a valid report.",
                supporting_reports=[]
            )
            
        # Synthesize reports into a CouncilDecision
        return self.synthesizer.synthesize(valid_reports, intent=intent)
