import numpy as np

from aegis_trade.application.reflection.snapshot import RichMarketSnapshot
from aegis_trade.domain.memory import MarketFeatures, MarketSession

class LiveFeatureExtractor:
    """
    Centralizes the extraction of market features from a snapshot.
    Converts raw market data and indicators into the MarketFeatures domain object.
    """
    
    def extract(self, snapshot: RichMarketSnapshot) -> MarketFeatures:
        df = snapshot.history
        latest = snapshot.latest_bar
        
        # 1. Market Data
        price = float(latest.close)
        open_price = float(latest.open)
        high_price = float(latest.high)
        low_price = float(latest.low)
        close_price = float(latest.close)
        volume = float(latest.volume)
        spread = 0.0001  # Mocked spread, not available in bar
        order_book_imbalance = 0.1  # Mocked imbalance, not available in bar
        
        # 2. Time & Session
        time_of_day = latest.timestamp.hour * 60 + latest.timestamp.minute
        
        hour = latest.timestamp.hour
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
        
        # 3. Oscillators & Trend
        n = len(df)
        ema_distance = 0.0
        rsi = 50.0
        macd = 0.0
        momentum_roc = 0.0
        vwap_distance = 0.0
        atr = (high_price - low_price)
        volatility_state = 0.01

        try:
            if n >= 20:
                ema20 = df['close'].ewm(span=20, adjust=False).mean().iloc[-1]
                if not np.isnan(ema20) and ema20 != 0:
                    ema_distance = (price - ema20) / ema20
                    
            if n >= 15:
                delta = df['close'].diff()
                up = delta.clip(lower=0)
                down = -1 * delta.clip(upper=0)
                roll_up = up.ewm(alpha=1/14, adjust=False).mean()
                roll_down = down.ewm(alpha=1/14, adjust=False).mean()
                rs = roll_up / roll_down
                rsi_val = 100.0 - (100.0 / (1.0 + rs)).iloc[-1]
                if not np.isnan(rsi_val):
                    rsi = rsi_val
                    
            if n >= 26:
                ema12 = df['close'].ewm(span=12, adjust=False).mean()
                ema26 = df['close'].ewm(span=26, adjust=False).mean()
                macd_val = (ema12 - ema26).iloc[-1]
                if not np.isnan(macd_val):
                    macd = macd_val
                    
            if n >= 13:
                roc_val = (df['close'].pct_change(periods=12).iloc[-1]) * 100
                if not np.isnan(roc_val):
                    momentum_roc = roc_val
                    
            if n >= 14:
                # Simplified VWAP over a 14-period window
                vol = df['volume']
                typ = (df['high'] + df['low'] + df['close']) / 3
                vwap = ((typ * vol).rolling(14).sum() / vol.rolling(14).sum()).iloc[-1]
                if not np.isnan(vwap) and vwap != 0:
                    vwap_distance = (price - vwap) / vwap
                    
            if n >= 15:
                prev_close = df['close'].shift(1)
                tr1 = df['high'] - df['low']
                tr2 = (df['high'] - prev_close).abs()
                tr3 = (df['low'] - prev_close).abs()
                tr = np.maximum(tr1, np.maximum(tr2, tr3))
                atr_val = tr.rolling(14).mean().iloc[-1]
                if not np.isnan(atr_val):
                    atr = atr_val
                    
            if n >= 2:
                returns = df['close'].pct_change().dropna()
                vol_val = returns.std()
                if not np.isnan(vol_val):
                    volatility_state = vol_val
        except Exception:
            pass
            
        liquidity_density = 1.0  # Mocked
        
        # 5. Portfolio Correlation
        portfolio_correlation = 0.0  # Mocked
        
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
            ema_distance=float(ema_distance),
            rsi=float(rsi),
            macd=float(macd),
            momentum_roc=float(momentum_roc),
            vwap_distance=float(vwap_distance),
            atr=float(atr),
            volatility_state=float(volatility_state),
            liquidity_density=liquidity_density,
            portfolio_correlation=portfolio_correlation
        )
