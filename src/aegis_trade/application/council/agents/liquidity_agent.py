from aegis_trade.domain.council import IVotingAgent, MarketContext, AgentVote

class LiquidityAgent:
    """
    Validates capacity to execute order without severe slippage.
    Primarily votes WAIT with high confidence if liquidity is poor.
    """
    @property
    def name(self) -> str:
        return "LiquidityAgent"

    def vote(self, context: MarketContext) -> AgentVote:
        spread = context.features.get('spread')
        volume = context.features.get('volume')
        
        if spread is None:
            return AgentVote(self.name, "WAIT", 0.0)

        # E.g. If spread is extremely high, heavily advise against trading
        if spread > 5.0: # Arbitrary threshold
            return AgentVote(self.name, "WAIT", 0.9)
            
        # If liquidity is fine, it is neutral
        return AgentVote(self.name, "WAIT", 0.0)
