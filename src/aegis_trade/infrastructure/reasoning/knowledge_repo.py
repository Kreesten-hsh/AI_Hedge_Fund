from typing import List, Dict, Optional
from datetime import datetime
import json
import uuid

from aegis_trade.domain.reasoning import (
    IKnowledgeRepository, 
    Knowledge, 
    KnowledgeType, 
    KnowledgeVersion,
    KnowledgeScore
)

class InMemoryKnowledgeRepository(IKnowledgeRepository):
    """
    In-memory storage for Knowledge.
    Suitable for AI-03 initial implementation, could be swapped for Redis/Postgres later.
    """
    def __init__(self):
        self._knowledge_base: Dict[str, Knowledge] = {}
        
    def save(self, knowledge: Knowledge) -> None:
        self._knowledge_base[knowledge.id] = knowledge
        
    def get_all_active(self) -> List[Knowledge]:
        return [k for k in self._knowledge_base.values() if k.active]
        
    def get_by_type(self, type: KnowledgeType) -> List[Knowledge]:
        return [k for k in self._knowledge_base.values() if k.type == type and k.active]
        
    def create_snapshot(self) -> KnowledgeVersion:
        """
        Creates a version snapshot for auditing.
        """
        active_count = len(self.get_all_active())
        archived_count = len(self._knowledge_base) - active_count
        
        return KnowledgeVersion(
            version_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            active_knowledge_count=active_count,
            archived_knowledge_count=archived_count
        )
