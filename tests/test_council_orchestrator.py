import pytest
from unittest.mock import Mock, patch
from aegis_trade.agents.council import CouncilOrchestrator, CouncilSynthesizer
from aegis_trade.agents.registry import AgentRegistry
from aegis_trade.agents.runner import AgentRunner
from aegis_trade.domain.reports import ExecutionResult, ResearchReport, ExecutionMetadata
from aegis_trade.domain.decisions import CouncilDecision

def test_council_orchestrator_integration():
    # Setup mocks
    registry = AgentRegistry()
    mock_agent = Mock()
    mock_agent.capability = "mock_cap"
    registry.register(mock_agent)
    
    mock_runner = Mock(spec=AgentRunner)
    
    # Mock runner returns one successful execution
    report = ResearchReport(capability="mock_cap", data={"trend": "bullish"})
    metadata = ExecutionMetadata("mock_cap", "test-model", 0.1, "2026-01-01", True)
    mock_runner.execute_many.return_value = [ExecutionResult(report, metadata)]
    
    mock_synthesizer = Mock(spec=CouncilSynthesizer)
    mock_synthesizer.synthesize.return_value = CouncilDecision(
        decision_type="go_long",
        confidence=0.9,
        multiplier=1.0,
        reasoning="Test",
        supporting_reports=[report]
    )
    
    orchestrator = CouncilOrchestrator(registry, mock_runner, mock_synthesizer)
    
    # Execute
    context = {"test": "data"}
    decision = orchestrator.generate_decision(context, intent="LONG")
    
    # Verify Runner was called with the agents from registry
    mock_runner.execute_many.assert_called_once_with([mock_agent], context)
    
    # Verify Synthesizer was called only with valid domain reports
    mock_synthesizer.synthesize.assert_called_once_with([report], intent="LONG")
    
    # Verify decision
    assert decision.decision_type == "go_long"
    assert decision.confidence == 0.9

def test_council_orchestrator_handles_all_failed_agents():
    registry = AgentRegistry()
    mock_agent = Mock()
    mock_agent.capability = "mock_cap"
    registry.register(mock_agent)
    
    mock_runner = Mock(spec=AgentRunner)
    
    # Mock runner returns one FAILED execution
    report = ResearchReport(capability="mock_cap", data={})
    metadata = ExecutionMetadata("mock_cap", "test-model", 0.1, "2026-01-01", False, "Error")
    mock_runner.execute_many.return_value = [ExecutionResult(report, metadata)]
    
    mock_synthesizer = Mock(spec=CouncilSynthesizer)
    
    orchestrator = CouncilOrchestrator(registry, mock_runner, mock_synthesizer)
    
    decision = orchestrator.generate_decision({}, intent="LONG")
    
    # Synthesizer should NOT be called if there are no valid reports
    mock_synthesizer.synthesize.assert_not_called()
    assert decision.decision_type == "wait"
    assert "failed" in decision.reasoning
