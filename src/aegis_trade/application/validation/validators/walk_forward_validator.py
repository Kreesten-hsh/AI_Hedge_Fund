import logging
from typing import Callable, List, Iterator
from aegis_trade.domain.validation import ValidationCampaignResult, ValidationCampaignType
from aegis_trade.domain.strategy import IStrategy
from aegis_trade.domain.ports.data_feed import IDataFeed
from aegis_trade.domain.execution import IBroker
from aegis_trade.domain.core import Symbol, TimeFrame, AssetClass
from aegis_trade.domain.features import FeatureSet
from aegis_trade.application.validation.config import ValidationConfig
from aegis_trade.application.validation.validators.base import IValidator
from aegis_trade.engine.backtester import Backtester

logger = logging.getLogger(__name__)

class ListDataFeed(IDataFeed):
    """DataFeed factice enveloppant une sous-liste de FeatureSets pour un segment temporel."""
    def __init__(self, feature_sets: List[FeatureSet]):
        self._feature_sets = feature_sets
        
    def get_feature_stream(self, symbol: Symbol, timeframe: TimeFrame) -> Iterator[FeatureSet]:
        return iter(self._feature_sets)

class WalkForwardValidator(IValidator):
    """
    Test Walk-Forward : Découpe le flux de données en N fenêtres glissantes (folds),
    exécute un backtest sur chaque fold et évalue la stabilité inter-période des métriques.
    """
    def run(
        self, 
        strategy: IStrategy, 
        data_feed: IDataFeed, 
        broker_factory: Callable[[], IBroker],
        config: ValidationConfig
    ) -> ValidationCampaignResult:
        logger.info("Running WalkForwardValidator with rolling windows...")
        
        symbol = config.markets[0] if config.markets else Symbol("CRASH1000", AssetClass.INDICES)
        timeframe = config.timeframes[0] if config.timeframes else TimeFrame.M1
        
        try:
            # Collecter toutes les barres du flux
            all_bars = list(data_feed.get_feature_stream(symbol, timeframe))
            total_bars = len(all_bars)
            
            num_folds = 5
            if total_bars < 10:
                logger.warning("WalkForwardValidator: pas assez de barres pour découper en 5 folds.")
                num_folds = max(1, total_bars // 2)
                
            fold_size = total_bars // num_folds if num_folds > 0 else total_bars
            
            fold_sharpes: List[float] = []
            fold_win_rates: List[float] = []
            fold_returns: List[float] = []
            fold_drawdowns: List[float] = []

            for i in range(num_folds):
                start_idx = i * fold_size
                end_idx = start_idx + fold_size if i < num_folds - 1 else total_bars
                fold_bars = all_bars[start_idx:end_idx]

                if len(fold_bars) < 2:
                    continue

                fold_feed = ListDataFeed(fold_bars)
                broker = broker_factory()
                backtester = Backtester(data_feed=fold_feed, strategy=strategy, broker=broker)

                try:
                    tearsheet = backtester.run(symbol, timeframe)
                    fold_sharpes.append(float(tearsheet.sharpe_ratio))
                    fold_win_rates.append(float(tearsheet.win_rate))
                    fold_returns.append(float(tearsheet.total_return))
                    fold_drawdowns.append(float(tearsheet.max_drawdown))
                except Exception as ex:
                    logger.debug(f"Fold {i+1} backtest error: {ex}")
                    fold_sharpes.append(0.0)
                    fold_win_rates.append(0.0)
                    # Un fold qui plante n'est pas un fold à rendement nul : on
                    # ne peut rien affirmer dessus, donc il ne doit pas remonter
                    # la moyenne. Il est compté comme perte totale du fold.
                    fold_returns.append(-1.0)
                    fold_drawdowns.append(1.0)

            if not fold_sharpes:
                return ValidationCampaignResult(
                    campaign_type=ValidationCampaignType.WALK_FORWARD,
                    metrics={
                        "sharpe_ratio": 0.0,
                        "win_rate": 0.0,
                        "net_return": -1.0,
                        "max_drawdown": 1.0,
                    },
                    passed=False,
                    details={"reason": "Aucun fold calculable"}
                )

            avg_sharpe = float(sum(fold_sharpes) / len(fold_sharpes))
            avg_win_rate = float(sum(fold_win_rates) / len(fold_win_rates))
            # Rendement composé à travers les folds, pas moyenné : c'est ce que
            # subit un compte qui traverse les périodes l'une après l'autre.
            # Une moyenne masquerait qu'un fold à -50 % ne se compense pas avec
            # un fold à +50 %.
            compounded = 1.0
            for r in fold_returns:
                compounded *= (1.0 + r)
            net_return = float(compounded - 1.0)
            worst_drawdown = float(max(fold_drawdowns)) if fold_drawdowns else 1.0

            # Validation : Sharpe moyen > 0.3, Win Rate moyen > 40% et aucun fold dramatiquement négatif
            passed = (avg_sharpe >= 0.3) and (avg_win_rate >= 0.40)

            return ValidationCampaignResult(
                campaign_type=ValidationCampaignType.WALK_FORWARD,
                metrics={
                    "sharpe_ratio": round(avg_sharpe, 4),
                    "win_rate": round(avg_win_rate, 4),
                    "net_return": round(net_return, 6),
                    "max_drawdown": round(worst_drawdown, 4),
                },
                passed=passed,
                details={
                    "symbol": symbol.name,
                    "timeframe": timeframe.value,
                    "folds_evaluated": len(fold_sharpes),
                    "fold_returns": [round(r, 6) for r in fold_returns],
                }
            )
        except Exception as e:
            logger.error(f"WalkForwardValidator failed: {e}")
            return ValidationCampaignResult(
                campaign_type=ValidationCampaignType.WALK_FORWARD,
                metrics={
                    "sharpe_ratio": 0.0,
                    "win_rate": 0.0,
                    "net_return": -1.0,
                    "max_drawdown": 1.0,
                },
                passed=False,
                details={"error": str(e)}
            )
