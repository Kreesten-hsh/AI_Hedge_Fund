import logging
from typing import List
from decimal import Decimal
import numpy as np

from aegis_trade.domain.strategy import IStrategy
from aegis_trade.domain.signal import Signal
from aegis_trade.domain.features import FeatureSet
from aegis_trade.application.council.orchestrator import MultiAgentCouncil
from aegis_trade.domain.rl import IPolicyStore, PolicyDecision
from aegis_trade.domain.council import MarketContext
from aegis_trade.engine.portfolio import Portfolio

logger = logging.getLogger(__name__)

class CouncilBacktestAdapter(IStrategy):
    """
    Adapter that allows the MultiAgentCouncil to act as an IStrategy.
    This enables seamless integration with existing historical validation frameworks.
    """
    def __init__(self, council: MultiAgentCouncil, policy_store: IPolicyStore):
        self.council = council
        self.policy_store = policy_store
        # We maintain a dummy portfolio purely to satisfy MarketContext requirements
        # in standard historical backtests, as the actual PnL is tracked by the runner (e.g. backtrader)
        self._dummy_portfolio = Portfolio(initial_capital=100000.0)

    def generate_signals(self, features: FeatureSet) -> List[Signal]:
        """
        Converts the FeatureSet into a MarketContext, queries the active RL policy,
        and asks the council for a decision. Returns a Signal object.
        """
        # 1. Map features to council inputs
        # For MVP, we map what we can. If the agents require strictly bounded [0, 1] scores,
        # we assume `features.features` provides them, or default to 0.5.
        f = features.features
        context = MarketContext(
            symbol=features.symbol,
            features={
                "trend_score": f.get("trend_score", 0.5),
                "momentum_score": f.get("momentum_score", 0.5),
                "volatility_score": f.get("volatility_score", 0.5),
                "liquidity_score": f.get("liquidity_score", 0.5),
                "pattern_score": f.get("pattern_score", 0.5),
                "news_score": f.get("news_score", 0.5),
                "portfolio_risk": f.get("portfolio_risk", 0.5),
                "execution_cost": f.get("execution_cost", 0.5)
            },
            portfolio=self._dummy_portfolio,
            latest_prices={features.symbol: Decimal(str(f.get("close", 100.0)))},
            memory_score=0.0
        )
        
        # 2. Get active policy
        policy_decision = None
        active_model = self.policy_store.load_active_policy()
        if active_model:
            try:
                obs = np.zeros(30, dtype=np.float32)
                action, _ = active_model.predict(obs, deterministic=True)
                policy_decision = PolicyDecision(
                    risk_multiplier=float(action[0]),
                    confidence_threshold_adjustment=float(action[1]),
                    agent_weights={
                        "Trend": float(action[2]),
                        "Momentum": float(action[3]),
                        "Volatility": float(action[4]),
                        "Liquidity": float(action[5]),
                        "Pattern": float(action[6]),
                        "News": float(action[7]),
                        "Portfolio": float(action[8]),
                        "Execution": float(action[9]),
                    }
                )
            except Exception as e:
                logger.error(f"Error executing active RL policy in backtest: {e}")
                
        # 3. Council evaluates
        verdict = self.council.evaluate(context, policy_decision)
        
        # 4. Map Verdict to Signal
        if verdict.final_vote == "WAIT" or verdict.position_size_multiplier <= 0:
            return []
            
        direction = 1 if verdict.final_vote == "BUY" else -1
        
        # Scale strength by confidence and size_multiplier (though Signal limits to [0,1])
        strength = min(1.0, max(0.0, verdict.aggregated_confidence * verdict.position_size_multiplier))
        
        sig = Signal(
            symbol=features.symbol,
            direction=direction,
            strength=strength,
            timestamp=features.timestamp
        )
        return [sig]
