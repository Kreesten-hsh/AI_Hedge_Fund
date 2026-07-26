import hashlib
import json
from typing import Any

from aegis_trade.infrastructure.serializers import HashSerializer

def compute_hash(data: dict[str, Any]) -> str:
    """
    Computes a cryptographic Hash (exact identity).
    All Hash generation in Aegis Quant OS MUST use this function
    to ensure deterministic serialization.
    """
    serializer = HashSerializer()
    serialized = serializer.serialize(data)
    return hashlib.sha256(serialized).hexdigest()

def compute_fingerprint(data: dict[str, Any]) -> str:
    """
    Computes a Fingerprint (structural equivalence).
    This is intentionally separated from Hash to maintain the semantic 
    distinction between an exact physical version and a logical fingerprint.
    """
    serializer = HashSerializer()
    serialized = serializer.serialize(data)
    # Using SHA-1 for structural equivalence/fingerprinting to distinguish from exact Hash
    return hashlib.sha1(serialized).hexdigest()
