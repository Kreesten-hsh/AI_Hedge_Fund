import json
import logging
import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import Mapping

import faiss
import numpy as np

from aegis_trade.domain.memory import Experience, MemoryCategory, SearchResult
from aegis_trade.domain.ports.memory import IVectorStore

logger = logging.getLogger(__name__)


class FaissVectorStore(IVectorStore):
    """
    FAISS-based implementation of the Memory Engine's Vector Store.
    Uses IndexIDMap to allow deleting and managing specific experience vectors.
    """

    def __init__(self, dimension: int = 25, storage_dir: str = ".data/memory"):
        self.dimension = dimension
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.index_path = self.storage_dir / "faiss.index"
        self.meta_path = self.storage_dir / "meta.pkl"
        
        self.experiences: dict[int, Experience] = {}
        self.uuid_to_id: dict[str, int] = {}
        self._next_id = 0
        
        self._load_or_create_index()

    def _load_or_create_index(self) -> None:
        if self.index_path.exists() and self.meta_path.exists():
            try:
                self.index = faiss.read_index(str(self.index_path))
                with open(self.meta_path, "rb") as f:
                    data = pickle.load(f)
                    self.experiences = data["experiences"]
                    self.uuid_to_id = data["uuid_to_id"]
                    self._next_id = data["next_id"]
                logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors.")
                return
            except Exception as e:
                logger.error(f"Failed to load FAISS index: {e}. Creating a new one.")
                
        # Create new index wrapped in IDMap to allow ID assignment and removal
        base_index = faiss.IndexFlatL2(self.dimension)
        self.index = faiss.IndexIDMap(base_index)

    def _persist(self) -> None:
        """Saves the index and metadata to disk."""
        faiss.write_index(self.index, str(self.index_path))
        with open(self.meta_path, "wb") as f:
            pickle.dump({
                "experiences": self.experiences,
                "uuid_to_id": self.uuid_to_id,
                "next_id": self._next_id
            }, f)

    def save(self, experience: Experience) -> None:
        if len(experience.embedding) != self.dimension:
            raise ValueError(f"Embedding dimension mismatch. Expected {self.dimension}, got {len(experience.embedding)}")
            
        vector = np.array([experience.embedding], dtype=np.float32)
        faiss_id = self._next_id
        
        # Add to FAISS (IDMap requires an array of IDs)
        self.index.add_with_ids(vector, np.array([faiss_id], dtype=np.int64))
        
        # Store metadata
        self.experiences[faiss_id] = experience
        self.uuid_to_id[experience.id] = faiss_id
        self._next_id += 1
        
        self._persist()

    def search(
        self, 
        embedding: tuple[float, ...], 
        top_k: int = 200, 
        categories: list[MemoryCategory] | None = None
    ) -> list[SearchResult]:
        if self.index.ntotal == 0:
            return []
            
        vector = np.array([embedding], dtype=np.float32)
        
        # Search for more than top_k if filtering by category, to ensure we get enough
        search_k = min(self.index.ntotal, top_k * 5 if categories else top_k)
        
        distances, indices = self.index.search(vector, search_k)
        
        results = []
        for i, faiss_id in enumerate(indices[0]):
            if faiss_id == -1:  # FAISS returns -1 if not enough results
                continue
                
            exp = self.experiences.get(faiss_id)
            if not exp:
                continue
                
            # Filter by category if requested
            if categories and exp.category not in categories:
                continue
                
            # Convert FAISS L2 distance to a basic similarity score (-100 to 100)
            # Distance 0 -> Score 100
            # A completely opposite normalized vector might have L2 distance around 4 (sqrt(2^2))
            distance = float(distances[0][i])
            score = max(-100.0, 100.0 - (distance * 50.0))
            
            results.append(SearchResult(
                experience=exp,
                distance=distance,
                similarity_score=score
            ))
            
            if len(results) >= top_k:
                break
                
        return results

    def delete(self, experience_id: str) -> None:
        faiss_id = self.uuid_to_id.get(experience_id)
        if faiss_id is None:
            return
            
        # Remove from FAISS
        self.index.remove_ids(np.array([faiss_id], dtype=np.int64))
        
        # Remove from maps
        del self.experiences[faiss_id]
        del self.uuid_to_id[experience_id]
        
        self._persist()

    def archive(self, experience_id: str) -> None:
        # In this implementation, archiving implies deleting from the fast index
        # but one could write to an "archive.jsonl" before deleting.
        exp = self.experiences.get(self.uuid_to_id.get(experience_id))
        if exp:
            archive_file = self.storage_dir / "archive.jsonl"
            # Just keeping it simple for MVP
            with open(archive_file, "a") as f:
                f.write(json.dumps({"id": exp.id, "archived_at": datetime.utcnow().isoformat()}) + "\n")
                
        self.delete(experience_id)

    def get_stats(self) -> Mapping[str, object]:
        category_counts = {c.value: 0 for c in MemoryCategory}
        for exp in self.experiences.values():
            category_counts[exp.category.value] += 1
            
        return {
            "total_vectors": self.index.ntotal,
            "category_distribution": category_counts,
            "dimension": self.dimension,
            "storage_path": str(self.storage_dir)
        }

