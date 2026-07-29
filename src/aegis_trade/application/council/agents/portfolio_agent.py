from aegis_trade.domain.council import IVotingAgent, MarketContext, AgentVote

class PortfolioAgent:
    """
    Analyzes exposure, diversification, and correlation.
    Reads current portfolio state.
    """
    @property
    def name(self) -> str:
        return "PortfolioAgent"

    def vote(self, context: MarketContext) -> AgentVote:
        pos = context.portfolio.get_position(context.symbol)
        
        if not pos or pos.volume == 0:
            return AgentVote(self.name, "WAIT", 0.0)
            
        # Example logic: if we are long, maybe suggest SELL to rebalance if overexposed
        # This is a basic stub that prefers taking profit or reducing exposure.
        if pos.volume > 0:
            return AgentVote(self.name, "SELL", 0.2)
        else:
            return AgentVote(self.name, "BUY", 0.2)
