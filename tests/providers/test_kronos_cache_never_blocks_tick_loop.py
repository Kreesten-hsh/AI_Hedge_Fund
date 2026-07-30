import pytest
import asyncio
import time
from aegis_trade.providers.kronos_adapter import KronosAdapter

def test_kronos_cache_never_blocks_tick_loop():
    adapter = KronosAdapter(prediction_horizon=10, refresh_interval_sec=1)
    
    # We do not start the background task, just manually mock the cache
    # to prove get_latest_forecast is O(1) and non-blocking
    
    from aegis_trade.domain.forecasting import KronosForecast
    import datetime
    
    adapter._cache["TEST"] = KronosForecast(
        symbol="TEST",
        horizon=10,
        predicted_values=[100.0]*10,
        confidence_interval=(90.0, 110.0),
        model_version="mock",
        timestamp=datetime.datetime.utcnow()
    )
    
    start_time = time.perf_counter()
    forecast = adapter.get_latest_forecast("TEST")
    end_time = time.perf_counter()
    
    assert forecast is not None
    assert forecast.symbol == "TEST"
    
    duration = end_time - start_time
    # Must be extremely fast (under 1ms, usually microseconds)
    assert duration < 0.001
