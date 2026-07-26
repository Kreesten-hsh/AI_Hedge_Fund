import pytest
from unittest.mock import Mock, patch
from aegis_trade.agents.runner import AgentRunner
from aegis_trade.agents.base import ResearchAgent
import json

class DummyAgent:
    @property
    def capability(self):
        return "dummy"
        
    @property
    def prompt_path(self):
        return "dummy_prompt.md"

def test_runner_executes_and_returns_execution_result():
    mock_provider = Mock()
    mock_provider.generate.return_value = '{"insight": "bullish"}'
    
    runner = AgentRunner(provider=mock_provider)
    
    agent = DummyAgent()
    
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = "Hello {name}"
        
        result = runner.execute(agent, {"name": "World"})
        
        # Verify provider was called correctly
        mock_provider.generate.assert_called_once_with(
            prompt="Hello World",
            system_prompt=""
        )
        
        # Verify result structure
        assert result.metadata.agent_capability == "dummy"
        assert result.metadata.success is True
        assert result.metadata.latency_seconds >= 0
        assert "insight" in result.report.data
        assert result.report.data["insight"] == "bullish"

def test_runner_handles_missing_context_keys():
    runner = AgentRunner(provider=Mock())
    agent = DummyAgent()
    
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = "Hello {name} and {other}"
        
        with pytest.raises(ValueError, match="Missing required context variable"):
            runner.execute(agent, {"name": "World"})

def test_runner_handles_json_parse_error():
    mock_provider = Mock()
    mock_provider.generate.return_value = "Not JSON"
    
    runner = AgentRunner(provider=mock_provider)
    agent = DummyAgent()
    
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = "Prompt"
        
        result = runner.execute(agent, {})
        
        assert result.metadata.success is False
        assert "Expecting value" in result.metadata.error_message
        assert result.report.data == {}
