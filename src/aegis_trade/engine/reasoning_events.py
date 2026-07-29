from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class KnowledgeGeneratedEvent:
    """Fired when the LLM generates a new hypothesis from a cluster."""
    cluster_id: int
    knowledge_type: str
    description: str

@dataclass
class KnowledgeValidatedEvent:
    """Fired when a hypothesis is mathematically validated and becomes active knowledge."""
    knowledge_id: str
    support: int
    confidence: float

@dataclass
class KnowledgeRejectedEvent:
    """Fired when a hypothesis fails statistical validation."""
    cluster_id: int
    reason: str
    measured_confidence: float

@dataclass
class KnowledgeArchivedEvent:
    """Fired when a piece of knowledge drops below the score threshold."""
    knowledge_id: str
    final_score: float
    reason: str
