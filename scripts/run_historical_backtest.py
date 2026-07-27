import logging
import json
import argparse
from datetime import datetime, timezone, timedelta

from aegis_trade.domain.core import Symbol, AssetClass, TimeFrame
from aegis_trade.domain.features import FeatureSet
from aegis_trade.domain.signal import Signal
from aegis_trade.domain.strategy import IStrategy
from aegis_trade.infrastructure.features.feature_store import FeatureStore
from aegis_trade.infrastructure.data.historical_feed import FeatureStoreFeed
from aegis_trade.infrastructure.brokers.simulated_broker import SimulatedBroker
from aegis_trade.engine.backtester import Backtester

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BT-01 Demo")

class MacdDummyStrategy(IStrategy):
    """
    A simple dummy strategy that uses a macd_signal feature if it exists.
    Otherwise it just buys and holds.
    """
    def generate_signals(self, feature_set: FeatureSet) -> list[Signal]:
        features = feature_set.features
        
        # Check if macd_signal is present (from FE-02)
        macd_signal = features.get('macd_signal', 0)
        
        direction = 0
        if macd_signal > 0:
            direction = 1
        elif macd_signal < 0:
            direction = -1
            
        if direction != 0:
            return [Signal(
                symbol=feature_set.symbol,
                direction=direction,
                strength=abs(macd_signal),
                timestamp=feature_set.timestamp
            )]
        return []

def main():
    parser = argparse.ArgumentParser(description="Run BT-01 Modular Backtest Demo")
    parser.add_argument("--symbol", type=str, default="BTCUSD", help="Symbol to backtest")
    parser.add_argument("--timeframe", type=str, default="D1", help="Timeframe (e.g., D1)")
    args = parser.parse_args()

    symbol = Symbol(args.symbol, AssetClass.CRYPTO)
    timeframe = TimeFrame(args.timeframe)
    
    logger.info(f"Initializing Historical Backtest for {symbol.name} on {timeframe.value}...")
    
    # 1. Setup Feature Store & Feed
    feature_store = FeatureStore(data_dir="data/features")
    data_feed = FeatureStoreFeed(feature_store)
    
    # 2. Setup Strategy
    strategy = MacdDummyStrategy()
    
    # 3. Setup Broker
    broker = SimulatedBroker(commission_rate=0.001, slippage_bps=5.0)
    
    # 4. Setup Backtester Orchestrator
    backtester = Backtester(data_feed=data_feed, strategy=strategy, broker=broker, starting_capital=100000.0)
    
    # 5. Run simulation
    try:
        report = backtester.run(symbol, timeframe)
        
        # 6. Display Tearsheet
        print("\n" + "="*50)
        print(" INSTITUTIONAL TEARSHEET REPORT")
        print("="*50)
        print(json.dumps(report.to_dict(), indent=4))
        print("="*50 + "\n")
        
    except Exception as e:
        logger.error(f"Backtest failed: {e}")

if __name__ == "__main__":
    main()
