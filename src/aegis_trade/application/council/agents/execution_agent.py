from aegis_trade.domain.council import IVotingAgent, MarketContext, AgentVote

class ExecutionAgent:
    """
    Microstructure of order routing.
    Can veto (WAIT) if latency is too high or broker is degraded.
    """
    @property
    def name(self) -> str:
        return "ExecutionAgent"

    def vote(self, context: MarketContext) -> AgentVote:
        broker_latency = context.features.get('broker_latency_ms', 0.0)
        
        if broker_latency > 200.0:
            # Latency too high, unsafe to trade
            return AgentVote(self.name, "WAIT", 0.95)
            
        return AgentVote(self.name, "WAIT", 0.0)
