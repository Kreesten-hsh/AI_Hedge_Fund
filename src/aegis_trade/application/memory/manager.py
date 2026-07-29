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

    def save_experience(self, experience: Experience) -> str:
        """
        Saves a pre-built experience to the vector store.
        Returns the experience ID.
        """
        self._vector_store.save(experience)
        return experience.id

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
