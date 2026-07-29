import pytest
from aegis_trade.domain.memory import MarketFeatures, MarketSession
from aegis_trade.infrastructure.memory.basic_embedding import BasicDeterministicEmbedding

def test_basic_embedding():
    embedder = BasicDeterministicEmbedding()
    
    features = MarketFeatures(
        price=1.1, open_price=1.1, high_price=1.1, low_price=1.1, close_price=1.1,
        spread=0.0, volume=0.0, order_book_imbalance=0.0, time_of_day=0.0, session=MarketSession.LONDON,
        time_since_economic_event_min=0.0, economic_calendar_flag=False, ema_distance=0.0, rsi=50.0,
        macd=0.0, momentum_roc=0.0, vwap_distance=0.0, atr=0.0, volatility_state=0.0, liquidity_density=0.0,
        portfolio_correlation=0.0
    )
    
    vec = embedder.generate(features)
    assert len(vec) == 25
    # Since it's L2 normalized, length should be approximately 1.0 (or 0.0 if all zeros)
    import math
    norm = math.sqrt(sum(v*v for v in vec))
    assert math.isclose(norm, 1.0, rel_tol=1e-5)
