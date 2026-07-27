import logging
import json
import argparse

from aegis_trade.domain.core import Symbol, AssetClass, TimeFrame
from aegis_trade.infrastructure.features.feature_store import FeatureStore
from aegis_trade.infrastructure.data.historical_feed import FeatureStoreFeed
from aegis_trade.infrastructure.brokers.simulated_broker import SimulatedBroker
from aegis_trade.infrastructure.strategies.ema_crossover import EmaCrossoverStrategy
from aegis_trade.infrastructure.strategies.rsi_mean_reversion import RsiMeanReversionStrategy
from aegis_trade.infrastructure.strategies.composite import CompositeStrategy
from aegis_trade.engine.backtester import Backtester

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BT-01 Demo")


def main():
    parser = argparse.ArgumentParser(description="Run BT-01 Modular Backtest Demo")
    parser.add_argument("--symbol", type=str, default="BTCUSD", help="Symbol to backtest")
    parser.add_argument("--timeframe", type=str, default="D1", help="Timeframe (e.g., D1)")
    args = parser.parse_args()

    symbol = Symbol(args.symbol, AssetClass.CRYPTO)
    timeframe = TimeFrame(args.timeframe)

    logger.info(f"Initializing Historical Backtest for {symbol.name} on {timeframe.value}...")

    # 1. Data
    feature_store = FeatureStore(data_dir="data/features")
    data_feed = FeatureStoreFeed(feature_store)

    # 2. Strategy: CompositeStrategy (EMA Crossover + RSI Mean Reversion)
    ema_strategy = EmaCrossoverStrategy(fast_key="ema_10", slow_key="ema_50")
    rsi_strategy = RsiMeanReversionStrategy(rsi_key="rsi_14", oversold=30.0, overbought=70.0)

    strategy = CompositeStrategy(
        strategies=[
            (ema_strategy, 1.0),
            (rsi_strategy, 1.0),
        ],
        threshold=0.3,
    )

    # 3. Broker
    broker = SimulatedBroker(commission_rate=0.001, slippage_bps=5.0)

    # 4. Backtester
    backtester = Backtester(data_feed=data_feed, strategy=strategy, broker=broker, starting_capital=100000.0)

    # 5. Run
    try:
        report = backtester.run(symbol, timeframe)

        print("\n" + "=" * 60)
        print("  INSTITUTIONAL TEARSHEET REPORT (CompositeStrategy)")
        print("  EMA Crossover (w=1.0) + RSI Mean Reversion (w=1.0)")
        print("=" * 60)
        print(json.dumps(report.to_dict(), indent=4))
        print("=" * 60 + "\n")

    except Exception as e:
        logger.error(f"Backtest failed: {e}")


if __name__ == "__main__":
    main()
