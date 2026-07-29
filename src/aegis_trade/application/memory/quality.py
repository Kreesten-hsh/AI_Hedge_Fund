from typing import List, Optional
from decimal import Decimal

from aegis_trade.domain.memory import Experience

class QualityViolation(Exception):
    """Raised when an Experience fails quality checks."""
    pass

class ExperienceQualityAnalyzer:
    """
    Analyzes an Experience to ensure data hygiene before injection into FAISS.
    Prevents data pollution from broker errors or market anomalies (e.g. absurd spread).
    """
    
    # Thresholds for hygiene
    MAX_SPREAD_MULTIPLIER = 50.0  # e.g., Spread should not be 50x normal
    MIN_DURATION_SECONDS = 0
    MAX_DURATION_SECONDS = 3600 * 24 * 30  # Max 30 days
    
    def analyze(self, experience: Experience) -> None:
        """
        Validates the experience. Raises QualityViolation if hygiene checks fail.
        """
        self._check_basic_hygiene(experience)
        self._check_pricing_anomalies(experience)
        self._check_feature_anomalies(experience)
        
    def _check_basic_hygiene(self, experience: Experience) -> None:
        if experience.duration_seconds < self.MIN_DURATION_SECONDS:
            raise QualityViolation(f"Negative duration: {experience.duration_seconds}")
            
        if experience.duration_seconds > self.MAX_DURATION_SECONDS:
            raise QualityViolation(f"Duration too long (probable ghost trade): {experience.duration_seconds}")
            
        if experience.features.volume < 0:
            raise QualityViolation(f"Negative volume: {experience.features.volume}")
            
    def _check_pricing_anomalies(self, experience: Experience) -> None:
        features = experience.features
        
        # Check basic OHLC validity
        if features.low_price > features.high_price:
            raise QualityViolation(f"Low price ({features.low_price}) is greater than High price ({features.high_price})")
            
        if features.price <= 0 or features.open_price <= 0 or features.close_price <= 0:
            raise QualityViolation(f"Zero or negative price detected")
            
        # Check if spread is completely absurd (e.g. > 10% of asset value, which is unrealistic for most tradable assets except penny stocks, but we shouldn't trade those)
        if features.spread < 0:
            raise QualityViolation(f"Negative spread detected: {features.spread}")
            
        if features.spread > (features.price * 0.10):
            raise QualityViolation(f"Spread is absurdly high (>10% of asset price): {features.spread}")

    def _check_feature_anomalies(self, experience: Experience) -> None:
        features = experience.features
        
        # Check RSI bounds
        if features.rsi < 0 or features.rsi > 100:
            raise QualityViolation(f"RSI out of bounds: {features.rsi}")
            
        # ATR must be positive
        if features.atr < 0:
            raise QualityViolation(f"ATR is negative: {features.atr}")
            
        # Time of day should be between 0 and 24 (or similar normalized metric, assuming hours)
        if features.time_of_day < 0 or features.time_of_day > 24:
            raise QualityViolation(f"Time of day out of bounds: {features.time_of_day}")
