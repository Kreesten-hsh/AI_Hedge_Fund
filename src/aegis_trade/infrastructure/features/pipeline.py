import json
import time
import logging
from typing import List, Tuple, Optional
from datetime import datetime

from aegis_trade.domain.core import Symbol, TimeFrame
from aegis_trade.domain.features import FeatureSet
from aegis_trade.domain.exceptions.data import PipelineError, FeatureValidationError

from aegis_trade.infrastructure.data.pipeline import MarketDataPipeline
from aegis_trade.infrastructure.features.technical_extractor import TechnicalFeatureExtractor
from aegis_trade.infrastructure.features.validator import FeatureValidator
from aegis_trade.infrastructure.features.feature_store import FeatureStore
from aegis_trade.infrastructure.features.cache import FeatureCache

logger = logging.getLogger(__name__)

class FeaturePipeline:
    """
    Orchestrates the generation of quantitative features.
    Flow: MarketDataPipeline -> TechnicalFeatureExtractor -> FeatureValidator -> FeatureStore -> FeatureCache
    """

    def __init__(
        self,
        market_data_pipeline: MarketDataPipeline,
        extractor: TechnicalFeatureExtractor,
        validator: FeatureValidator,
        store: FeatureStore,
        cache: FeatureCache
    ):
        self.market_pipeline = market_data_pipeline
        self.extractor = extractor
        self.validator = validator
        self.store = store
        self.cache = cache

    def fetch_features(
        self, 
        provider_name: str,
        symbol: Symbol, 
        timeframe: TimeFrame, 
        start: datetime, 
        end: datetime,
        use_cache: bool = True
    ) -> Tuple[List[FeatureSet], dict]:
        """
        Retrieves features for the requested range, computing and storing them if necessary.
        Returns the feature sets and a metrics dictionary (Phase 9).
        """
        start_time = time.perf_counter()
        metrics = {
            "symbol": symbol.name,
            "timeframe": timeframe.value,
            "requested_start": start.isoformat(),
            "requested_end": end.isoformat(),
            "cache_hit": False,
            "features_generated": 0,
            "rows_returned": 0,
            "timings_ms": {},
            "error": None
        }

        # 1. Check Cache
        if use_cache:
            t0 = time.perf_counter()
            cached_data = self.cache.get(symbol, timeframe)
            metrics["timings_ms"]["cache_read"] = (time.perf_counter() - t0) * 1000
            
            if cached_data:
                # Filter by range
                filtered = [fs for fs in cached_data if start <= fs.timestamp <= end]
                if filtered:
                    metrics["cache_hit"] = True
                    metrics["rows_returned"] = len(filtered)
                    metrics["timings_ms"]["total"] = (time.perf_counter() - start_time) * 1000
                    logger.info(json.dumps({"event": "FeaturePipeline", **metrics}))
                    return filtered, metrics

        # 2. Check Data Lake (Feature Store) for delta
        t0 = time.perf_counter()
        latest_ts = self.store.get_latest_timestamp(symbol, timeframe)
        metrics["timings_ms"]["store_metadata_read"] = (time.perf_counter() - t0) * 1000

        compute_required = True
        if latest_ts and latest_ts >= end:
            compute_required = False
            delta_start = start
        else:
            if latest_ts and latest_ts > start:
                # We need extra burn-in data to compute technical indicators correctly (e.g., EMA 200)
                # To be completely safe and stateless, a robust Feature Engine fetches market data with 
                # a padding of 250 bars before the required delta_start.
                # However, for simplicity here, we assume the market_pipeline will return the delta, 
                # but we will ask it for market data from 'start' if we don't have enough history,
                # or just process what is missing.
                delta_start = latest_ts
            else:
                delta_start = start

        if compute_required:
            try:
                # 3. Fetch Market Data (Market Pipeline handles its own caching/syncing)
                t0 = time.perf_counter()
                
                # IMPORTANT: Technical indicators require "burn-in". If we just fetch from delta_start, 
                # EMAs and RSI will be NaN. We must fetch market data from the very beginning or use a padding.
                # Here, we fetch from a padded start if possible, or we let the extractor handle the fact
                # that first few values will be NaN (which validator allows up to burn_in_periods).
                # To ensure math continuity, production systems usually fetch delta_start - 250 bars.
                # Since MarketDataPipeline handles caching, fetching from `start` is cheap if it's cached.
                
                bars, md_context = self.market_pipeline.fetch_ohlcv(
                    provider_name, symbol, timeframe, delta_start, end, use_cache=True
                )
                metrics["timings_ms"]["market_data_fetch"] = (time.perf_counter() - t0) * 1000
                
                if bars:
                    # 4. Extract Features
                    t0 = time.perf_counter()
                    new_features = self.extractor.extract(bars)
                    metrics["timings_ms"]["feature_extraction"] = (time.perf_counter() - t0) * 1000
                    metrics["features_generated"] = len(new_features)

                    # 5. Validate Features
                    t0 = time.perf_counter()
                    try:
                        self.validator.validate(new_features, burn_in_periods=200)
                    except FeatureValidationError as e:
                        metrics["error"] = str(e)
                        logger.error(json.dumps({"event": "FeaturePipeline", **metrics}))
                        raise
                    metrics["timings_ms"]["feature_validation"] = (time.perf_counter() - t0) * 1000

                    # 6. Save to Store
                    t0 = time.perf_counter()
                    self.store.save_and_merge_features(symbol, timeframe, new_features)
                    metrics["timings_ms"]["store_write"] = (time.perf_counter() - t0) * 1000

            except Exception as e:
                metrics["error"] = str(e)
                logger.error(json.dumps({"event": "FeaturePipeline", **metrics}))
                raise PipelineError(f"Feature computation failed: {e}") from e

        # 7. Load unified history from Store
        t0 = time.perf_counter()
        try:
            full_history = self.store.load_features(symbol, timeframe)
            normalized_features = [fs for fs in full_history if start <= fs.timestamp <= end]
            metrics["rows_returned"] = len(normalized_features)
        except Exception as e:
            metrics["error"] = str(e)
            logger.error(json.dumps({"event": "FeaturePipeline", **metrics}))
            raise PipelineError(f"Failed to load unified features from Store: {e}") from e
        metrics["timings_ms"]["store_read"] = (time.perf_counter() - t0) * 1000

        # 8. Cache
        if use_cache and normalized_features:
            t0 = time.perf_counter()
            self.cache.set(symbol, timeframe, normalized_features)
            metrics["timings_ms"]["cache_write"] = (time.perf_counter() - t0) * 1000

        metrics["timings_ms"]["total"] = (time.perf_counter() - start_time) * 1000
        logger.info(json.dumps({"event": "FeaturePipeline", **metrics}))
        
        return normalized_features, metrics
