from aegis_trade.domain.core import MarketBar
from aegis_trade.domain.memory import MarketFeatures, MarketSession


class LiveFeatureExtractor:
    """
    Centralizes the extraction of market features from a snapshot.
    Converts raw market data and indicators into the MarketFeatures domain object.
    For this phase, some calculations are mocked or simplified.
    """
    
    def extract(self, snapshot: MarketBar) -> MarketFeatures:
        """
        Extracts MarketFeatures from a given MarketBar.
        """
        # 1. Market Data
        price = float(snapshot.close)
        open_price = float(snapshot.open)
        high_price = float(snapshot.high)
        low_price = float(snapshot.low)
        close_price = float(snapshot.close)
        volume = float(snapshot.volume)
        spread = 0.0001  # Mocked spread
        order_book_imbalance = 0.1  # Mocked imbalance
        
        # 2. Time & Session
        # E.g. minute of day
        time_of_day = snapshot.timestamp.hour * 60 + snapshot.timestamp.minute
        
        # Determine Session based on hour (simplified)
        hour = snapshot.timestamp.hour
        if 8 <= hour < 16:
            session = MarketSession.LONDON
        elif 13 <= hour < 21:
            session = MarketSession.NEW_YORK
        elif 0 <= hour < 8:
            session = MarketSession.TOKYO
        else:
            session = MarketSession.ASIAN_BOX
            
        time_since_economic_event_min = 120.0  # Mocked
        economic_calendar_flag = False         # Mocked
        
        # 3. Oscillators & Trend (Mocked)
        ema_distance = 0.05
        rsi = 55.0
        macd = 0.02
        momentum_roc = 0.1
        vwap_distance = 0.01
        
        # 4. Volatility & Liquidity (Mocked)
        atr = (high_price - low_price) * 0.5 if high_price > low_price else 0.001
        volatility_state = 0.02
        liquidity_density = 1.0
        
        # 5. Portfolio Correlation (Mocked)
        portfolio_correlation = 0.2
        
        return MarketFeatures(
            price=price,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            spread=spread,
            volume=volume,
            order_book_imbalance=order_book_imbalance,
            time_of_day=time_of_day,
            session=session,
            time_since_economic_event_min=time_since_economic_event_min,
            economic_calendar_flag=economic_calendar_flag,
            ema_distance=ema_distance,
            rsi=rsi,
            macd=macd,
            momentum_roc=momentum_roc,
            vwap_distance=vwap_distance,
            atr=atr,
            volatility_state=volatility_state,
            liquidity_density=liquidity_density,
            portfolio_correlation=portfolio_correlation
        )
