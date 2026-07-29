from aegis_trade.domain.council import IVotingAgent, MarketContext, AgentVote

class VolatilityAgent:
    """
    Detects expansion or contraction regimes.
    Uses ATR or Bollinger Bands.
    """
    @property
    def name(self) -> str:
        return "VolatilityAgent"

    def vote(self, context: MarketContext) -> AgentVote:
        current_price = context.latest_prices.get(context.symbol)
        bb_upper = context.features.get('bb_upper')
        bb_lower = context.features.get('bb_lower')

        if current_price is None or bb_upper is None or bb_lower is None:
            return AgentVote(self.name, "WAIT", 0.0)

        price_f = float(current_price)
        
        # Mean reversion logic at bands
        if price_f >= bb_upper:
            return AgentVote(self.name, "SELL", 0.75)
        elif price_f <= bb_lower:
            return AgentVote(self.name, "BUY", 0.75)
            
        return AgentVote(self.name, "WAIT", 0.3)
