from aegis_trade.infrastructure.portfolio.fixed_fractional_sizer import FixedFractionalSizer
from aegis_trade.domain.signal import Signal
from aegis_trade.domain.core import Symbol, AssetClass

def test_fixed_fractional_sizer_no_max():
    sizer = FixedFractionalSizer(fraction=0.95)
    signal = Signal(Symbol("AAPL", AssetClass.EQUITIES), direction=1, strength=1.0, timestamp=None)
    
    qty = sizer.size(signal, capital=10000.0, current_price=100.0)
    assert qty == 95.0 # (10000 * 0.95) / 100

def test_fixed_fractional_sizer_with_max_allowed_fraction():
    sizer = FixedFractionalSizer(fraction=0.95, max_allowed_fraction=0.20)
    signal = Signal(Symbol("AAPL", AssetClass.EQUITIES), direction=1, strength=1.0, timestamp=None)
    
    qty = sizer.size(signal, capital=10000.0, current_price=100.0)
    assert qty == 20.0 # (10000 * 0.20) / 100
