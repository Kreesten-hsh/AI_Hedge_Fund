import abc
from typing import Mapping

from aegis_trade.domain.memory import Experience, MarketFeatures, SearchResult, MemoryCategory


class IVectorStore(abc.ABC):
    """
    Interface for the Vector Database storage (e.g. FAISS, ChromaDB).
    This strictly isolates the Domain from the specific database technology.
    """

    @abc.abstractmethod
    def save(self, experience: Experience) -> None:
        """Stores a new experience and its embedding vector in the database."""
        pass

    @abc.abstractmethod
    def search(
        self, 
        embedding: tuple[float, ...], 
        top_k: int = 200, 
        categories: list[MemoryCategory] | None = None
    ) -> list[SearchResult]:
        """
        Searches for the most similar historical experiences.
        Optionally filters by MemoryCategory (e.g., only SUCCESS or FAILURE).
        """
        pass

    @abc.abstractmethod
    def delete(self, experience_id: str) -> None:
        """Removes an experience from the vector store."""
        pass

    @abc.abstractmethod
    def archive(self, experience_id: str) -> None:
        """Archives an experience (moves it to cold storage and removes from fast search index)."""
        pass

    @abc.abstractmethod
    def get_stats(self) -> Mapping[str, object]:
        """
        Returns memory engine statistics.
        Required: total experiences, breakdown by category, average search time, etc.
        """
        pass


class IEmbeddingGenerator(abc.ABC):
    """
    Interface for generating an embedding vector from Market Features.
    """

    @abc.abstractmethod
    def generate(self, features: MarketFeatures) -> tuple[float, ...]:
        """
        Converts the provided market features into a dense vector representation.
        The resulting tuple must be deterministic for the given inputs.
        """
        pass

