import uuid
from datetime import datetime
from decimal import Decimal
from typing import Mapping, Optional

from aegis_trade.domain.core import Side, Symbol, TimeFrame
from aegis_trade.domain.memory import Experience, MarketFeatures, MemoryCategory
from aegis_trade.domain.ports.memory import IEmbeddingGenerator


class ExperienceBuilder:
    """
    Responsible solely for constructing an Experience object.
    Applies the SRP principle to separate creation from storage.
    """
    def __init__(self, embedding_generator: IEmbeddingGenerator):
        self._embedding_generator = embedding_generator

    def _determine_category(self, pnl: Decimal, max_drawdown: Decimal, features: MarketFeatures, metadata: Mapping[str, str]) -> MemoryCategory:
        """
        Determines the memory category based on performance metrics, features, and metadata overrides.
        """
        if metadata and "force_category" in metadata:
            try:
                return MemoryCategory(metadata["force_category"])
            except ValueError:
                pass

        if metadata and "exit_reason" in metadata:
            reason = metadata["exit_reason"]
            if reason == "liquidation":
                return MemoryCategory.FAILURE
            elif reason == "risk_exit":
                return MemoryCategory.EXCEPTIONAL

        # Exceptional via volatility
        if features.volatility_state > 0.05: # Threshold example
            return MemoryCategory.EXCEPTIONAL

        pnl_float = float(pnl)
        drawdown_float = float(max_drawdown)

        if pnl_float > 0.0 and drawdown_float < 2.0:
            return MemoryCategory.SUCCESS
        elif pnl_float < -2.0 or drawdown_float >= 5.0:
            return MemoryCategory.FAILURE
        elif -2.0 <= pnl_float <= 0.0:
            return MemoryCategory.NEAR_MISS
        
        return MemoryCategory.UNKNOWN

    def build(
        self,
        timestamp: datetime,
        symbol: Symbol,
        timeframe: TimeFrame,
        decision_side: Side,
        features: MarketFeatures,
        pnl: Decimal,
        max_drawdown: Decimal,
        duration_seconds: int,
        metadata: Optional[Mapping[str, str]] = None
    ) -> Experience:
        """
        Constructs an Experience object.
        Generates the embedding and calculates the category.
        """
        meta = metadata or {}
        exp_id = str(uuid.uuid4())
        
        category = self._determine_category(pnl, max_drawdown, features, meta)
        embedding = self._embedding_generator.generate(features)
        
        return Experience(
            id=exp_id,
            timestamp=timestamp,
            symbol=symbol,
            timeframe=timeframe,
            features=features,
            decision_side=decision_side,
            pnl=pnl,
            max_drawdown=max_drawdown,
            duration_seconds=duration_seconds,
            category=category,
            embedding=embedding,
            metadata=meta
        )
