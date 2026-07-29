from aegis_trade.domain.council import IVotingAgent, MarketContext, AgentVote

class NewsAgent:
    """
    Macro-economic filter (Asynchronous LLM evaluation).
    Currently implemented as a neutral stub since it runs outside the critical path.
    """
    @property
    def name(self) -> str:
        return "NewsAgent"

    def vote(self, context: MarketContext) -> AgentVote:
        # Stub: The actual LLM evaluation is asynchronous and cached.
        # Until implemented, returns neutral.
        return AgentVote(self.name, "WAIT", 0.0)
