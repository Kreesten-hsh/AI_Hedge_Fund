from dataclasses import dataclass, field
from typing import Literal, List, Protocol, Dict
from decimal import Decimal
from aegis_trade.domain import Symbol
from aegis_trade.engine.portfolio import Portfolio


@dataclass(frozen=True)
class AgentVote:
    """A single deterministic vote from an agent in the Council."""
    agent_name: str
    vote: Literal["BUY", "SELL", "WAIT"]
    confidence: float  # Range [0.0, 1.0]


@dataclass(frozen=True)
class CouncilVerdict:
    """The final aggregated decision from the Multi-Agent Council."""
    final_vote: Literal["BUY", "SELL", "WAIT"]
    aggregated_confidence: float  # Expected [0.0, 1.0]
    position_size_multiplier: float  # Usually 1.0, can be reduced to e.g. 0.25 on high disagreement
    votes: List[AgentVote]
    veto_reason: str | None
    disagreement_level: float  # Metric quantifying how split the council was [0.0, 1.0]


@dataclass(frozen=True)
class MarketContext:
    """
    Consolidated state passed to all agents for deterministic evaluation.
    Contains everything an agent needs to make a vote.
    """
    symbol: Symbol
    features: Dict[str, float]  # Fast indicators (RSI, EMA, ATR, Volume, Spread, etc.)
    portfolio: Portfolio
    latest_prices: Dict[Symbol, Decimal]
    memory_score: float = 0.0  # Used by PatternAgent [-100.0, +100.0]


class IVotingAgent(Protocol):
    """Protocol for a deterministic Voting Agent."""
    @property
    def name(self) -> str:
        ...

    def vote(self, context: MarketContext) -> AgentVote:
        ...
