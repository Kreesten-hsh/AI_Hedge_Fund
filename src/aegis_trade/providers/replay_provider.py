from typing import Sequence
from aegis_trade.domain import Symbol, TimeFrame, MarketBar, Tick, HealthStatus
from aegis_trade.providers.validation import StrictDataValidator
from aegis_trade.core.exceptions import DataFetchError

class ReplayProvider:
    """
    Fournisseur de données en mode Replay.
    N'accepte que des objets métier purs (Sequence[MarketBar], Sequence[Tick]).
    Le parsing depuis des fichiers (CSV, Parquet) est délégué à une couche d'import externe.
    """

    def __init__(self, bars: Sequence[MarketBar] = (), ticks: Sequence[Tick] = ()):
        validator = StrictDataValidator()
        self._bars = validator.validate_bars(bars)
        self._ticks = validator.validate_ticks(ticks)

    def health_check(self) -> HealthStatus:
        # ReplayProvider est toujours "connecté" s'il est instancié.
        return HealthStatus(
            connected=True,
            latency=0.0,
            provider="replay",
            version="1.0",
            last_error=None
        )

    def get_bars(self, symbol: Symbol, timeframe: TimeFrame, limit: int) -> Sequence[MarketBar]:
        filtered_bars = [b for b in self._bars if b.symbol == symbol and b.timeframe == timeframe]
        if not filtered_bars:
            raise DataFetchError(f"No replay bars available for {symbol.name} on {timeframe.value}")
        return tuple(filtered_bars[-limit:] if limit > 0 else filtered_bars)

    def get_ticks(self, symbol: Symbol, limit: int) -> Sequence[Tick]:
        filtered_ticks = [t for t in self._ticks if t.symbol == symbol]
        if not filtered_ticks:
            raise DataFetchError(f"No replay ticks available for {symbol.name}")
        return tuple(filtered_ticks[-limit:] if limit > 0 else filtered_ticks)
