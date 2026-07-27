from typing import List

from aegis_trade.domain.features import FeatureSet
from aegis_trade.domain.signal import Signal
from aegis_trade.domain.strategy import IStrategy


class RsiMeanReversionStrategy(IStrategy):
    """
    Mean-reversion strategy based on RSI.
    LONG when RSI drops below oversold threshold (default 30),
    SHORT when RSI rises above overbought threshold (default 70).
    Returns no signal if the RSI feature is missing.
    """

    def __init__(
        self,
        rsi_key: str = "rsi_14",
        oversold: float = 30.0,
        overbought: float = 70.0,
    ):
        self.rsi_key = rsi_key
        self.oversold = oversold
        self.overbought = overbought

    def generate_signals(self, features: FeatureSet) -> List[Signal]:
        rsi = features.features.get(self.rsi_key)

        if rsi is None:
            return []

        if rsi < self.oversold:
            # Oversold -> mean reversion bet: LONG
            # Strength proportional to how deep into oversold territory
            strength = min((self.oversold - rsi) / self.oversold, 1.0)
            return [Signal(
                symbol=features.symbol,
                direction=1,
                strength=strength,
                timestamp=features.timestamp,
            )]

        if rsi > self.overbought:
            # Overbought -> mean reversion bet: SHORT
            strength = min((rsi - self.overbought) / (100.0 - self.overbought), 1.0)
            return [Signal(
                symbol=features.symbol,
                direction=-1,
                strength=strength,
                timestamp=features.timestamp,
            )]

        return []
