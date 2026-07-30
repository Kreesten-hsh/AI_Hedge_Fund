import logging
import asyncio
from typing import Optional, Dict
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from aegis_trade.domain.forecasting import IForecaster, KronosForecast
from aegis_trade.providers.kronos.model_factory import KronosModelFactory
from aegis_trade.providers.kronos.shiyu_model.kronos import KronosPredictor

logger = logging.getLogger(__name__)

class KronosAdapter(IForecaster):
    """
    Anti-Corruption Layer for Kronos-mini.
    Provides non-blocking O(1) access to predictions via cache.
    Refreshes cache asynchronously (e.g., every 1m).
    """
    def __init__(self, prediction_horizon: int = 10, refresh_interval_sec: int = 60):
        self.prediction_horizon = prediction_horizon
        self.refresh_interval_sec = refresh_interval_sec
        
        self.factory = KronosModelFactory()
        self.predictor: Optional[KronosPredictor] = None
        
        self._cache: Dict[str, KronosForecast] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def initialize(self) -> bool:
        """
        Loads the model and initializes the predictor.
        """
        predictor = self.factory.get_predictor()
        if predictor:
            self.predictor = predictor
            return True
        return False

    def start_background_refresh(self, symbols: list[str], data_provider):
        """
        Starts the background async task to refresh predictions.
        """
        self._running = True
        self._task = asyncio.create_task(self._refresh_loop(symbols, data_provider))

    def stop_background_refresh(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _refresh_loop(self, symbols: list[str], data_provider):
        while self._running:
            start_time = datetime.utcnow()
            try:
                if self.predictor:
                    for symbol in symbols:
                        # 1. Fetch latest candles from data_provider (stubbed here)
                        # The true Kronos model expects a dataframe with ['open', 'high', 'low', 'close', 'volume', 'amount']
                        
                        # Mock dataframe for structure
                        now = pd.Timestamp(datetime.utcnow())
                        x_timestamps = pd.date_range(end=now, periods=512, freq='1min')
                        y_timestamps = pd.date_range(start=now + pd.Timedelta(minutes=1), periods=self.prediction_horizon, freq='1min')
                        
                        dummy_df = pd.DataFrame(
                            np.random.randn(512, 6) + 100, 
                            columns=['open', 'high', 'low', 'close', 'volume', 'amount'],
                            index=x_timestamps
                        )
                        
                        # 2. Predict (Offloaded to a thread pool to not block asyncio CPU-bound)
                        # We use predictor.predict from the true Kronos model
                        def run_prediction():
                            return self.predictor.predict(
                                df=dummy_df,
                                x_timestamp=x_timestamps,
                                y_timestamp=y_timestamps,
                                pred_len=self.prediction_horizon,
                                sample_count=5, # Ensemble for confidence
                                verbose=False
                            )
                            
                        pred_df = await asyncio.to_thread(run_prediction)
                        
                        # Calculate median and confidence bounds from the close price
                        # Note: The original sample_count logic averages internally in the true model predict() method,
                        # so we just take the last point's close value as a proxy or use the whole path.
                        # For simplicity of the interface matching what we had:
                        median_pred = pred_df['close'].tolist()
                        low_bound = min(median_pred)
                        high_bound = max(median_pred)
                        
                        # 3. Update Cache
                        self._cache[symbol] = KronosForecast(
                            symbol=symbol,
                            horizon=self.prediction_horizon,
                            predicted_values=median_pred,
                            confidence_interval=(low_bound, high_bound),
                            model_version=KronosModelFactory.MODEL_NAME,
                            timestamp=datetime.utcnow()
                        )
            except Exception as e:
                logger.error(f"Error in Kronos background refresh: {e}")
                
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            sleep_time = max(1.0, self.refresh_interval_sec - elapsed)
            await asyncio.sleep(sleep_time)

    def get_latest_forecast(self, symbol: str) -> Optional[KronosForecast]:
        """
        O(1) access to the latest forecast from cache.
        """
        return self._cache.get(symbol)
