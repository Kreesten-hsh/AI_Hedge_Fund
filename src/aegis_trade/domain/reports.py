from dataclasses import dataclass
from typing import Dict, Any

@dataclass(frozen=True)
class ExecutionMetadata:
    """Technical telemetry for agent execution."""
    agent_capability: str
    model_name: str
    latency_seconds: float
    timestamp_utc: str
    success: bool
    error_message: str = ""

@dataclass(frozen=True)
class ResearchReport:
    """Domain object representing a business finding from an analyst."""
    capability: str
    data: Dict[str, Any]  # The parsed JSON business data (e.g. regime, confidence, reasoning)

@dataclass(frozen=True)
class ExecutionResult:
    """Wrapper combining domain data and technical execution metadata."""
    report: ResearchReport
    metadata: ExecutionMetadata
