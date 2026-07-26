from typing import Sequence

from aegis_trade.dataset.readonly import ReadOnlyDataset
from aegis_trade.strategy_research.domain import ResearchSignal, SignalType
from aegis_trade.strategy_research.strategy import ResearchStrategy

class SmaCrossoverMockStrategy:
    """
    Stratégie factice pour les tests.
    """
    def __init__(self, fast_period: int, slow_period: int):
        self._fast_period = fast_period
        self._slow_period = slow_period
        
    def name(self) -> str:
        return f"sma_crossover_mock_{self._fast_period}_{self._slow_period}"
        
    def version(self) -> str:
        return "1.0"
        
    def dependencies(self) -> list[str]:
        # On prétend qu'on dépend de ces deux colonnes pré-calculées
        return [f"SMA_{self._fast_period}", f"SMA_{self._slow_period}"]
        
    def generate(self, dataset: ReadOnlyDataset) -> Sequence[ResearchSignal | None]:
        fast_col = dataset.column(f"SMA_{self._fast_period}").values
        slow_col = dataset.column(f"SMA_{self._slow_period}").values
        
        signals = []
        for f_val, s_val in zip(fast_col, slow_col):
            # Warmup policy: if dependency is None, signal is None
            if f_val is None or s_val is None:
                signals.append(None)
            else:
                if f_val > s_val:
                    signals.append(ResearchSignal(SignalType.LONG, 1.0))
                elif f_val < s_val:
                    signals.append(ResearchSignal(SignalType.SHORT, 1.0))
                else:
                    signals.append(ResearchSignal(SignalType.FLAT, 1.0))
                    
        return signals
