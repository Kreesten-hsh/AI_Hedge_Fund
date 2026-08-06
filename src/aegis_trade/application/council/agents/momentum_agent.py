from aegis_trade.domain.council import IVotingAgent, MarketContext, AgentVote

class MomentumAgent:
    """
    Evaluates immediate strength of the move.
    Uses RSI or MACD.
    """
    @property
    def name(self) -> str:
        return "MomentumAgent"

    def vote(self, context: MarketContext) -> AgentVote:
        rsi = context.features.get('rsi')
        if rsi is None:
            rsi = context.features.get('rsi_14')
        
        if rsi is None:
            return AgentVote(self.name, "WAIT", 0.0)

        # Simple oversold/overbought logic
        if rsi < 30.0:
            # Oversold, momentum might reverse to upside
            return AgentVote(self.name, "BUY", 0.8)
        elif rsi > 70.0:
            # Overbought
            return AgentVote(self.name, "SELL", 0.8)
            
        return AgentVote(self.name, "WAIT", 0.1)
