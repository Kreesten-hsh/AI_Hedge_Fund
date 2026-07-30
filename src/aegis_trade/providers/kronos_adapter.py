import logging
import asyncio
from typing import Optional, Dict
from datetime import datetime

from aegis_trade.domain.forecasting import IForecaster, KronosForecast
from aegis_trade.providers.kronos.model_factory import KronosModelFactory
from aegis_trade.providers.kronos.predictor import KronosPredictor
import torch

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
        pipeline = self.factory.get_pipeline()
        if pipeline:
            self.predictor = KronosPredictor(pipeline)
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
                        # 1. Fetch latest 2048 candles from data_provider (stubbed here)
                        # context_data = data_provider.get_historical_data(symbol, "1m", limit=2048)
                        # tensor = torch.tensor([context_data['close'].values])
                        
                        # Mock tensor for the structure
                        dummy_tensor = torch.randn(1, 2048) 
                        
                        # 2. Predict (This should ideally be offloaded to a thread pool to not block asyncio if it's heavy CPU)
                        # For CPU inference, asyncio.to_thread is critical to keep HFT loop alive
                        median_pred, conf_interval = await asyncio.to_thread(
                            self.predictor.predict, dummy_tensor, self.prediction_horizon
                        )
                        
                        # 3. Update Cache
                        self._cache[symbol] = KronosForecast(
                            symbol=symbol,
                            horizon=self.prediction_horizon,
                            predicted_values=median_pred,
                            confidence_interval=conf_interval,
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
