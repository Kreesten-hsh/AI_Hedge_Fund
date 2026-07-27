from datetime import datetime, timezone
import time
import logging
from typing import Sequence, Tuple, Optional

from aegis_trade.domain.core import Symbol, TimeFrame, MarketBar
from aegis_trade.domain.data_context import DataContext
from aegis_trade.domain.exceptions.data import PipelineError, DataProviderError, ValidationError, NormalizationError, ConfigurationError
from aegis_trade.infrastructure.data.registry import ProviderRegistry
from aegis_trade.infrastructure.data.validator import DataValidator
from aegis_trade.infrastructure.data.normalizer import DataNormalizer
from aegis_trade.infrastructure.data.cache import CacheBackend
from aegis_trade.infrastructure.data.parquet_storage import ParquetStorage

logger = logging.getLogger(__name__)

class MarketDataPipeline:
    """
    The orchestrator for market data ingestion.
    Flow: Ingestion -> Validation -> Normalization -> Cache -> Publication
    """

    def __init__(
        self,
        cache_backend: CacheBackend,
        validator: DataValidator,
        normalizer: DataNormalizer,
        storage: Optional[ParquetStorage] = None
    ):
        self.cache = cache_backend
        self.validator = validator
        self.normalizer = normalizer
        self.storage = storage or ParquetStorage()

    def fetch_ohlcv(
        self, 
        provider_name: str, 
        symbol: Symbol, 
        timeframe: TimeFrame, 
        start: datetime, 
        end: datetime,
        use_cache: bool = True
    ) -> Tuple[Sequence[MarketBar], DataContext]:
        """
        Orchestrates the fetching, validation, and normalization of OHLCV data.
        Returns the data and its context metadata.
        """
        start_time = time.perf_counter()
        retrieved_at = datetime.now(timezone.utc)
        
        # Check cache
        cache_key = self.cache.generate_key(
            "ohlcv", 
            provider=provider_name, 
            symbol=symbol.name, 
            timeframe=timeframe.value, 
            start=start.isoformat(), 
            end=end.isoformat()
        )
        
        cache_hit = False
        if use_cache:
            try:
                cached_data = self.cache.get(cache_key)
                if cached_data is not None:
                    cache_hit = True
                    latency = time.perf_counter() - start_time
                    context = DataContext(
                        provider=provider_name,
                        symbol=symbol,
                        timeframe=timeframe,
                        timezone="UTC",
                        source="cache",
                        retrieved_at=retrieved_at,
                        latency=latency,
                        cache_hit=cache_hit
                    )
                    logger.info(f"Cache hit for OHLCV {symbol.name} ({timeframe.value}) via {provider_name}")
                    return cached_data, context
            except Exception as e:
                logger.warning(f"Cache get failed: {e}. Falling back to API.")

        # 1. Delta Sync (Data Lake)
        latest_ts = self.storage.get_latest_timestamp(symbol, timeframe)
        
        fetch_required = True
        if latest_ts and latest_ts >= end:
            fetch_required = False
            delta_start = start
        else:
            if latest_ts and latest_ts > start:
                delta_start = latest_ts
            else:
                delta_start = start
                
        if fetch_required:
            provider = ProviderRegistry.get(provider_name)
            try:
                raw_bars = provider.fetch_ohlcv(symbol, timeframe, delta_start, end)
            except DataProviderError:
                raise
            except Exception as e:
                raise PipelineError(f"Unexpected ingestion failure: {e}") from e
                
            if raw_bars:
                # 2. Validation
                try:
                    validated_bars = self.validator.validate_ohlcv(raw_bars)
                except ValidationError:
                    raise
                except Exception as e:
                    raise PipelineError(f"Unexpected validation failure: {e}") from e

                # 3. Normalization
                try:
                    normalized_delta = self.normalizer.normalize_ohlcv(validated_bars)
                except NormalizationError:
                    raise
                except Exception as e:
                    raise PipelineError(f"Unexpected normalization failure: {e}") from e
                    
                # 4. Save to Parquet
                try:
                    self.storage.save_and_merge_bars(symbol, timeframe, normalized_delta)
                except Exception as e:
                    logger.warning(f"Failed to save to parquet: {e}")
                    
        # Load unified history from Parquet and filter by requested range
        try:
            full_history = self.storage.load_bars(symbol, timeframe)
            normalized_bars = [b for b in full_history if start <= b.timestamp <= end]
        except Exception as e:
            raise PipelineError(f"Failed to load unified history from Parquet: {e}") from e

        # 5. Cache
        if use_cache and normalized_bars:
            try:
                self.cache.set(cache_key, normalized_bars)
            except Exception as e:
                logger.warning(f"Failed to cache data: {e}")

        # 5. Context preparation
        latency = time.perf_counter() - start_time
        context = DataContext(
            provider=provider_name,
            symbol=symbol,
            timeframe=timeframe,
            timezone="UTC",
            source="api",
            retrieved_at=retrieved_at,
            latency=latency,
            cache_hit=cache_hit
        )
        
        logger.info(f"Pipeline fetched {len(normalized_bars)} bars for {symbol.name} in {latency:.3f}s")
        return normalized_bars, context
