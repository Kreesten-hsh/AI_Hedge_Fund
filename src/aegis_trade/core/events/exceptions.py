class EventValidationError(ValueError):
    """Raised when an event does not meet the strict domain requirements (e.g., non-UTC timestamp)."""
    pass
