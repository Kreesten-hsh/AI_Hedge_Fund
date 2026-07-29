import numpy as np

from aegis_trade.domain.memory import MarketFeatures
from aegis_trade.domain.ports.memory import IEmbeddingGenerator


class BasicDeterministicEmbedding(IEmbeddingGenerator):
    """
    A deterministic embedding generator that normalizes features without AI/LLM.
    This serves as the initial Baseline. It converts the domain MarketFeatures
    into a flat dense vector for FAISS indexing.
    """

    def __init__(self) -> None:
        # Expected dimensionality:
        # price, open, high, low, close, spread, volume, imbalance (8)
        # time, session (one-hot?), event_min, flag (4+4=8)
        # ema, rsi, macd, roc, vwap (5)
        # atr, vol_state, liq_density (3)
        # correlation (1)
        # Total approx = 25 dimensions
        pass

    def _session_to_vector(self, session_str: str) -> list[float]:
        # Simple one-hot encoding for the 5 sessions
        mapping = {
            "london": [1.0, 0.0, 0.0, 0.0, 0.0],
            "new_york": [0.0, 1.0, 0.0, 0.0, 0.0],
            "tokyo": [0.0, 0.0, 1.0, 0.0, 0.0],
            "asian_box": [0.0, 0.0, 0.0, 1.0, 0.0],
            "other": [0.0, 0.0, 0.0, 0.0, 1.0],
        }
        return mapping.get(session_str, mapping["other"])

    def generate(self, features: MarketFeatures) -> tuple[float, ...]:
        # Normalize and flatten. 
        # For this basic version, we assume features are already pre-normalized by the Domain/Extractor
        # or we just pass them as floats. In a production system, a MinMaxScaler or StandardScaler 
        # state would be loaded here.
        
        vector = [
            float(features.price),
            float(features.open_price),
            float(features.high_price),
            float(features.low_price),
            float(features.close_price),
            float(features.spread),
            float(features.volume),
            float(features.order_book_imbalance),
            
            float(features.time_of_day),
            float(features.time_since_economic_event_min),
            1.0 if features.economic_calendar_flag else 0.0,
            
            float(features.ema_distance),
            float(features.rsi),
            float(features.macd),
            float(features.momentum_roc),
            float(features.vwap_distance),
            
            float(features.atr),
            float(features.volatility_state),
            float(features.liquidity_density),
            
            float(features.portfolio_correlation)
        ]
        
        # Add session one-hot (5 elements)
        vector.extend(self._session_to_vector(features.session.value))
        
        # Total dimensions: 20 + 5 = 25
        
        # Optional: L2 normalization of the vector to improve FAISS Cosine/L2 distance behavior
        arr = np.array(vector, dtype=np.float32)
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
            
        return tuple(arr.tolist())
