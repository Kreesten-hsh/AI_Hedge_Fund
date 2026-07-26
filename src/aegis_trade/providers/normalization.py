from typing import Sequence
from datetime import datetime, timezone
from decimal import Decimal

from aegis_trade.domain import Symbol, TimeFrame, MarketBar, Tick

class MT5DataNormalizer:
    """
    Normalise les données provenant de MetaTrader5 en objets du domaine.
    Ne fait AUCUNE validation logique, seulement de la conversion de format.
    """

    def normalize_bars(self, raw_data: object, symbol: Symbol, timeframe: TimeFrame) -> Sequence[MarketBar]:
        """
        Convertit un ndarray de MT5 rates en MarketBar.
        """
        bars = []
        for rate in raw_data:
            bars.append(MarketBar(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=datetime.fromtimestamp(int(rate['time']), tz=timezone.utc),
                open=Decimal(str(rate['open'])),
                high=Decimal(str(rate['high'])),
                low=Decimal(str(rate['low'])),
                close=Decimal(str(rate['close'])),
                volume=Decimal(str(rate['tick_volume']))
            ))
        return tuple(bars)
        
    def normalize_ticks(self, raw_data: object, symbol: Symbol) -> Sequence[Tick]:
        """
        Convertit un ndarray de MT5 ticks en Tick.
        """
        ticks = []
        for tick in raw_data:
            ticks.append(Tick(
                symbol=symbol,
                timestamp=datetime.fromtimestamp(int(tick['time']), tz=timezone.utc),
                bid=Decimal(str(tick['bid'])),
                ask=Decimal(str(tick['ask']))
            ))
        return tuple(ticks)
