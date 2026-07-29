import time
from decimal import Decimal
from datetime import datetime, timezone
from aegis_trade.domain.core import Symbol, AssetClass, MarketBar, TimeFrame, Side
from aegis_trade.domain.memory import MarketFeatures
from aegis_trade.engine.events import MarketEvent
from aegis_trade.application.reflection.snapshot import MarketSnapshotBuilder
from aegis_trade.application.reflection.extractor import LiveFeatureExtractor
from aegis_trade.application.reflection.builder import ExperienceBuilder

class MockEmbeddingGenerator:
    def generate(self, features: MarketFeatures) -> tuple[float, ...]:
        return tuple(0.1 for _ in range(384))

def test_benchmark_reflection() -> None:
    snapshot_builder = MarketSnapshotBuilder()
    extractor = LiveFeatureExtractor()
    builder = ExperienceBuilder(embedding_generator=MockEmbeddingGenerator())
    
    symbol = Symbol("AAPL", AssetClass.EQUITIES)
    
    # 1. Populate History
    start_time = time.perf_counter()
    for i in range(100):
        bar = MarketBar(
            symbol=symbol,
            timeframe=TimeFrame.M1,
            timestamp=datetime(2023, 1, 1, 14, i % 60, tzinfo=timezone.utc),
            open=Decimal("150.0") + Decimal(i * 0.1),
            high=Decimal("155.0") + Decimal(i * 0.1),
            low=Decimal("149.0") + Decimal(i * 0.1),
            close=Decimal("152.0") + Decimal(i * 0.1),
            volume=Decimal("1000")
        )
        event = MarketEvent(timestamp=bar.timestamp, bar=bar)
        snapshot_builder.on_market_event(event)
    populate_time = time.perf_counter() - start_time
    print(f"Populate 100 bars time: {populate_time*1000:.2f} ms")
    
    # 2. Benchmark Snapshot + Extract
    start_time = time.perf_counter()
    snapshot = snapshot_builder.get_snapshot(symbol)
    features = extractor.extract(snapshot)
    extract_time = time.perf_counter() - start_time
    print(f"Extraction (Tick-to-Features) Latency: {extract_time*1000:.2f} ms")
    
    # 3. Benchmark Experience Build
    start_time = time.perf_counter()
    experience = builder.build(
        timestamp=datetime.now(timezone.utc),
        symbol=symbol,
        timeframe=TimeFrame.M5,
        decision_side=Side.LONG,
        features=features,
        pnl=Decimal("-10.0"),
        max_drawdown=Decimal("5.5"),
        duration_seconds=3600,
        metadata={"exit_reason": "liquidation"}
    )
    build_time = time.perf_counter() - start_time
    print(f"Experience Generation Latency: {build_time*1000:.2f} ms")
    print(f"Total Pipeline Latency: {(extract_time + build_time)*1000:.2f} ms")
    print(f"Generated Category: {experience.category}")
    
    assert (extract_time + build_time) * 1000 < 100.0, f"Latency exceeded 100ms threshold: {(extract_time + build_time)*1000:.2f} ms"

if __name__ == "__main__":
    test_benchmark_reflection()
