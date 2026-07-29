import uuid
from datetime import datetime
from decimal import Decimal
from typing import Mapping

from aegis_trade.domain.core import Side, Symbol, TimeFrame
from aegis_trade.domain.memory import Experience, MarketFeatures, MemoryCategory, SearchResult
from aegis_trade.domain.ports.memory import IEmbeddingGenerator, IVectorStore


class MemoryManager:
    """
    Orchestrates the Experience & Pattern Memory Engine.
    Handles the transformation of raw market context into a stored Experience
    and provides querying capabilities.
    """

    def __init__(self, vector_store: IVectorStore, embedding_generator: IEmbeddingGenerator):
        self._vector_store = vector_store
        self._embedding_generator = embedding_generator

    def _determine_category(self, pnl: Decimal, max_drawdown: Decimal, metadata: Mapping[str, str]) -> MemoryCategory:
        """
        Determines the memory category based on performance metrics.
        This is a basic rule-based classifier. It can be extended based on strict thresholds.
        """
        pnl_float = float(pnl)
        drawdown_float = float(max_drawdown)
        
        # Check for explicit override in metadata
        if metadata and "force_category" in metadata:
            try:
                return MemoryCategory(metadata["force_category"])
            except ValueError:
                pass

        if pnl_float > 0.0 and drawdown_float < 2.0:
            return MemoryCategory.SUCCESS
        elif pnl_float < -2.0 or drawdown_float >= 5.0:
            return MemoryCategory.FAILURE
        elif -2.0 <= pnl_float <= 0.0:
            return MemoryCategory.NEAR_MISS
        
        return MemoryCategory.UNKNOWN

    def save_experience(
        self,
        timestamp: datetime,
        symbol: Symbol,
        timeframe: TimeFrame,
        decision_side: Side,
        features: MarketFeatures,
        pnl: Decimal,
        max_drawdown: Decimal,
        duration_seconds: int,
        metadata: Mapping[str, str] | None = None
    ) -> str:
        """
        Calculates the embedding, categorizes the result, and saves the experience.
        Returns the generated experience ID.
        """
        exp_id = str(uuid.uuid4())
        meta = metadata or {}
        
        category = self._determine_category(pnl, max_drawdown, meta)
        embedding = self._embedding_generator.generate(features)
        
        experience = Experience(
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
        
        self._vector_store.save(experience)
        return exp_id

    def find_similar_experiences(
        self, 
        features: MarketFeatures, 
        top_k: int = 200, 
        categories: list[MemoryCategory] | None = None
    ) -> list[SearchResult]:
        """
        Finds the closest historical experiences based on current market features.
        """
        embedding = self._embedding_generator.generate(features)
        return self._vector_store.search(embedding, top_k=top_k, categories=categories)
        
    def search_failure_patterns(self, features: MarketFeatures, top_k: int = 100) -> list[SearchResult]:
        """Convenience method to search only FAILURE memories."""
        return self.find_similar_experiences(features, top_k, categories=[MemoryCategory.FAILURE])

    def search_success_patterns(self, features: MarketFeatures, top_k: int = 100) -> list[SearchResult]:
        """Convenience method to search only SUCCESS memories."""
        return self.find_similar_experiences(features, top_k, categories=[MemoryCategory.SUCCESS])

    def get_statistics(self) -> Mapping[str, object]:
        """Returns statistics from the underlying vector store."""
        return self._vector_store.get_stats()
        
    def delete_experience(self, experience_id: str) -> None:
        """Removes an experience permanently."""
        self._vector_store.delete(experience_id)
        
    def archive_experience(self, experience_id: str) -> None:
        """Archives an experience for cold storage."""
        self._vector_store.archive(experience_id)
