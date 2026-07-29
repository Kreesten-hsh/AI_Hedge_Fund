"""
Reward Calculator for RL Engine (AI-04).
Implements the specific reward function required by Aegis Quant OS.
"""

from src.aegis_trade.domain.rl import RewardComponents
import math


class RewardCalculator:
    """
    Computes the composite reward function based on pure, independently testable functions.
    Reward = PnL_Normalise
           - Penalty_Max_Drawdown (exponential)
           - Penalty_Temps_En_Position (encourages HFT speed)
           - Penalty_Slippage
           - Penalty_Spread
           - Penalty_Variance_Globale
           + Bonus_Ratio_Gain_Risque
    """

    def __init__(
        self,
        drawdown_penalty_weight: float = 2.0,
        time_in_position_weight: float = 0.5,
        slippage_penalty_weight: float = 1.0,
        spread_penalty_weight: float = 1.0,
        variance_penalty_weight: float = 1.0,
        risk_reward_bonus_weight: float = 1.0
    ):
        self.drawdown_penalty_weight = drawdown_penalty_weight
        self.time_in_position_weight = time_in_position_weight
        self.slippage_penalty_weight = slippage_penalty_weight
        self.spread_penalty_weight = spread_penalty_weight
        self.variance_penalty_weight = variance_penalty_weight
        self.risk_reward_bonus_weight = risk_reward_bonus_weight

    def calc_pnl_normalized(self, pnl: float, capital: float) -> float:
        if capital <= 0:
            return 0.0
        # Normalize PnL as a percentage of capital
        return (pnl / capital) * 100.0

    def calc_drawdown_penalty(self, max_drawdown: float, max_allowed_drawdown: float) -> float:
        """
        Calculates an exponential penalty as the drawdown approaches the maximum allowed limit.
        """
        if max_drawdown <= 0:
            return 0.0
        
        ratio = max_drawdown / max_allowed_drawdown
        # Exponential penalty: e^(k * ratio) - 1
        # If ratio = 1 (drawdown hits SL), penalty is huge.
        penalty = math.exp(3.0 * ratio) - 1.0
        return penalty * self.drawdown_penalty_weight

    def calc_time_in_position_penalty(self, duration_seconds: float, expected_duration: float) -> float:
        """
        Penalizes trades that stay open longer than expected, encouraging HFT.
        """
        if duration_seconds <= expected_duration:
            return 0.0
        
        ratio = (duration_seconds - expected_duration) / expected_duration
        return ratio * self.time_in_position_weight

    def calc_slippage_penalty(self, expected_price: float, execution_price: float, side: str) -> float:
        """
        Calculates penalty based on slippage amount.
        """
        slippage = 0.0
        if side.lower() == "long":
            slippage = execution_price - expected_price
        elif side.lower() == "short":
            slippage = expected_price - execution_price
            
        if slippage <= 0:
            return 0.0
            
        # Normalizing slippage impact (this can be relative to price)
        return (slippage / expected_price) * 100.0 * self.slippage_penalty_weight

    def calc_spread_penalty(self, spread: float, avg_price: float) -> float:
        """
        Penalizes trades taken during wide spreads.
        """
        if spread <= 0 or avg_price <= 0:
            return 0.0
        return (spread / avg_price) * 100.0 * self.spread_penalty_weight

    def calc_variance_penalty(self, variance: float) -> float:
        """
        Penalizes high variance (volatility) during the trade.
        """
        if variance <= 0:
            return 0.0
        return variance * self.variance_penalty_weight

    def calc_risk_reward_bonus(self, expected_profit: float, risk_amount: float) -> float:
        """
        Adds a bonus if the ratio of potential gain to risk is high.
        """
        if risk_amount <= 0 or expected_profit <= 0:
            return 0.0
        rr_ratio = expected_profit / risk_amount
        # Cap the bonus to prevent it from overshadowing everything else
        bonus = min(rr_ratio, 5.0)
        return bonus * self.risk_reward_bonus_weight

    def calculate(
        self,
        pnl: float,
        capital: float,
        max_drawdown: float,
        max_allowed_drawdown: float,
        duration_seconds: float,
        expected_duration: float,
        expected_price: float,
        execution_price: float,
        side: str,
        spread: float,
        variance: float,
        expected_profit: float,
        risk_amount: float
    ) -> float:
        """
        Computes the total reward from all the distinct metrics.
        """
        pnl_norm = self.calc_pnl_normalized(pnl, capital)
        dd_pen = self.calc_drawdown_penalty(max_drawdown, max_allowed_drawdown)
        time_pen = self.calc_time_in_position_penalty(duration_seconds, expected_duration)
        slip_pen = self.calc_slippage_penalty(expected_price, execution_price, side)
        spread_pen = self.calc_spread_penalty(spread, expected_price)
        var_pen = self.calc_variance_penalty(variance)
        rr_bonus = self.calc_risk_reward_bonus(expected_profit, risk_amount)

        components = RewardComponents(
            pnl_normalise=pnl_norm,
            drawdown_penalty=dd_pen,
            time_in_position_penalty=time_pen,
            slippage_penalty=slip_pen,
            spread_penalty=spread_pen,
            variance_penalty=var_pen,
            risk_reward_bonus=rr_bonus
        )

        return components.total_reward
