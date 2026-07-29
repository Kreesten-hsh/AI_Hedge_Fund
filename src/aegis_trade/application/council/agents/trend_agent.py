from aegis_trade.domain.council import IVotingAgent, MarketContext, AgentVote

class TrendAgent:
    """
    Analyzes medium-term market structure (Trend).
    Uses EMA or SMA features.
    """
    @property
    def name(self) -> str:
        return "TrendAgent"

    def vote(self, context: MarketContext) -> AgentVote:
        current_price = context.latest_prices.get(context.symbol)
        if current_price is None:
            return AgentVote(self.name, "WAIT", 0.0)

        # Naive implementation assuming 'ema_50' is provided in features
        ema = context.features.get('ema_50')
        if ema is None:
            return AgentVote(self.name, "WAIT", 0.0)

        price_f = float(current_price)
        if price_f > ema * 1.001:  # 0.1% buffer
            return AgentVote(self.name, "BUY", 0.7)
        elif price_f < ema * 0.999:
            return AgentVote(self.name, "SELL", 0.7)
            
        return AgentVote(self.name, "WAIT", 0.2)
