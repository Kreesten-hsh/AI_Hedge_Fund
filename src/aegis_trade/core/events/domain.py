import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Mapping, Any

from aegis_trade.core.events.exceptions import EventValidationError


def _generate_deterministic_hash(
    event_id: str,
    event_version: str,
    event_type: str,
    occurred_at: datetime,
    metadata: Mapping[str, Any]
) -> str:
    """Generates a SHA-256 hash strictly based on canonical event data."""
    # Ensure datetime is serialized deterministically
    occurred_at_str = occurred_at.isoformat()
    
    # Sort keys for deterministic JSON serialization
    try:
        metadata_str = json.dumps(metadata, sort_keys=True, separators=(',', ':'))
    except (TypeError, ValueError) as e:
        raise EventValidationError(f"Event metadata must be JSON serializable: {e}")

    canonical_string = f"{event_id}|{event_version}|{event_type}|{occurred_at_str}|{metadata_str}"
    return hashlib.sha256(canonical_string.encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class DomainEvent:
    """
    Base class for all domain events.
    Must be completely immutable, deterministic, and enforce UTC time.
    """
    event_id: str
    event_type: str
    occurred_at: datetime
    metadata: Mapping[str, Any]
    event_version: str = "1.0"
    
    # The hash is generated in __post_init__ so it cannot be manually overridden easily, 
    # but since it's a frozen dataclass, we must use object.__setattr__
    hash: str = field(init=False)

    def __post_init__(self):
        if not self.event_id:
            raise EventValidationError("event_id cannot be empty.")
            
        if not self.event_type:
            raise EventValidationError("event_type cannot be empty.")

        if self.occurred_at.tzinfo is None:
            raise EventValidationError("occurred_at must be timezone-aware (UTC).")
            
        if self.occurred_at.tzinfo != timezone.utc:
            # We enforce strict UTC rather than just any timezone to avoid 
            # normalization ambiguity across the system.
            raise EventValidationError("occurred_at must be strictly in UTC timezone.")

        calculated_hash = _generate_deterministic_hash(
            event_id=self.event_id,
            event_version=self.event_version,
            event_type=self.event_type,
            occurred_at=self.occurred_at,
            metadata=self.metadata
        )
        object.__setattr__(self, 'hash', calculated_hash)
