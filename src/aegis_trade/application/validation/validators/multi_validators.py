import logging
from typing import Callable
from aegis_trade.domain.validation import ValidationCampaignResult, ValidationCampaignType
from aegis_trade.domain.strategy import IStrategy
from aegis_trade.domain.ports.data_feed import IDataFeed
from aegis_trade.domain.execution import IBroker
from aegis_trade.domain.core import Symbol, TimeFrame, AssetClass
from aegis_trade.application.validation.config import ValidationConfig
from aegis_trade.application.validation.validators.base import IValidator
from aegis_trade.engine.backtester import Backtester

logger = logging.getLogger(__name__)

class MultiMarketValidator(IValidator):
    """
    Test Multi-Marchés : Vérifie la robustesse de la stratégie sur plusieurs actifs.
    """
    def run(
        self, 
        strategy: IStrategy, 
        data_feed: IDataFeed, 
        broker_factory: Callable[[], IBroker],
        config: ValidationConfig
    ) -> ValidationCampaignResult:
        markets = config.markets if config.markets else [Symbol("CRASH1000", AssetClass.INDICES)]
        timeframe = config.timeframes[0] if config.timeframes else TimeFrame.M1
        logger.info(f"Running MultiMarketValidator on {len(markets)} markets...")
        
        sharpes = []
        positive_count = 0
        
        for sym in markets:
            try:
                broker = broker_factory()
                backtester = Backtester(data_feed=data_feed, strategy=strategy, broker=broker)
                tearsheet = backtester.run(sym, timeframe)
                s_ratio = float(tearsheet.sharpe_ratio)
                sharpes.append(s_ratio)
                if s_ratio > 0:
                    positive_count += 1
            except Exception as e:
                logger.warning(f"MultiMarketValidator failed for symbol {sym.name}: {e}")
                
        avg_sharpe = sum(sharpes) / max(1, len(sharpes))
        pos_ratio = positive_count / max(1, len(markets))
        passed = pos_ratio >= 0.5
        
        return ValidationCampaignResult(
            campaign_type=ValidationCampaignType.MULTI_MARKET,
            metrics={"avg_sharpe_ratio": round(avg_sharpe, 4), "positive_markets_ratio": round(pos_ratio, 4)},
            passed=passed,
            details={"markets_tested": [m.name for m in markets]}
        )

class MultiTimeframeValidator(IValidator):
    """
    Test Multi-Timeframe : Vérifie la robustesse sur plusieurs unités de temps.
    """
    def run(
        self, 
        strategy: IStrategy, 
        data_feed: IDataFeed, 
        broker_factory: Callable[[], IBroker],
        config: ValidationConfig
    ) -> ValidationCampaignResult:
        symbol = config.markets[0] if config.markets else Symbol("CRASH1000", AssetClass.INDICES)
        timeframes = config.timeframes if config.timeframes else [TimeFrame.M1]
        logger.info(f"Running MultiTimeframeValidator on {len(timeframes)} timeframes...")
        
        sharpes = []
        positive_count = 0
        
        for tf in timeframes:
            try:
                broker = broker_factory()
                backtester = Backtester(data_feed=data_feed, strategy=strategy, broker=broker)
                tearsheet = backtester.run(symbol, tf)
                s_ratio = float(tearsheet.sharpe_ratio)
                sharpes.append(s_ratio)
                if s_ratio > 0:
                    positive_count += 1
            except Exception as e:
                logger.warning(f"MultiTimeframeValidator failed for timeframe {tf.value}: {e}")
                
        avg_sharpe = sum(sharpes) / max(1, len(timeframes))
        pos_ratio = positive_count / max(1, len(timeframes))
        passed = pos_ratio >= 0.5
        
        return ValidationCampaignResult(
            campaign_type=ValidationCampaignType.MULTI_TIMEFRAME,
            metrics={"avg_sharpe_ratio": round(avg_sharpe, 4), "positive_timeframes_ratio": round(pos_ratio, 4)},
            passed=passed,
            details={"timeframes_tested": [t.value for t in timeframes]}
        )
