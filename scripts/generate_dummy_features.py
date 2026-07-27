import os
import sys
import numpy as np
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from aegis_trade.domain.core import Symbol, AssetClass, TimeFrame
from aegis_trade.domain.features import FeatureSet
from aegis_trade.infrastructure.features.feature_store import FeatureStore

def main():
    symbol = Symbol("BTCUSD", AssetClass.CRYPTO)
    timeframe = TimeFrame.D1
    store = FeatureStore()
    
    np.random.seed(42)
    
    # Generate 100 days of data
    features = []
    base_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
    
    returns = np.random.normal(0, 0.02, 100)
    for i in range(100):
        # future return is i+1
        ret_1d = float(returns[i])
        
        # some dummy features
        f1 = float(np.random.normal(0, 1))
        f2 = float(returns[i+1] + np.random.normal(0, 0.005)) if i < 99 else 0.0
        
        fs = FeatureSet(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=base_time + timedelta(days=i),
            features={
                "return_1d": ret_1d,
                "rsi_14": 50.0 + f1 * 10,
                "macd_signal": f2,
                "volatility_20": abs(f1)
            }
        )
        features.append(fs)
        
    store.save_and_merge_features(symbol, timeframe, features)
    print("Dummy features saved.")

if __name__ == "__main__":
    main()
