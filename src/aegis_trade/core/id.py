import uuid

def generate_id(prefix: str = "") -> str:
    """
    Unified ID generation across Aegis Quant OS.
    Currently uses UUIDv4 without dashes, prefixed.
    """
    base = uuid.uuid4().hex
    if prefix:
        return f"{prefix}_{base}"
    return base
