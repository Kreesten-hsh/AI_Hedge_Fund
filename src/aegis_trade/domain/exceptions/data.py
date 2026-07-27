class DataProviderError(Exception):
    """Raised when a data provider encounters an error (e.g. network issue, API limit)."""
    pass

class ValidationError(Exception):
    """Raised when data validation fails (e.g. missing values, NaN, incorrect types)."""
    pass

class NormalizationError(Exception):
    """Raised when data normalization fails."""
    pass

class CacheError(Exception):
    """Raised when a cache operation fails."""
    pass

class StorageError(Exception):
    """Raised when a storage (e.g. Parquet data lake) operation fails."""
    pass

class PipelineError(Exception):
    """Raised when the overall pipeline execution fails unexpectedly."""
    pass

class ConfigurationError(Exception):
    """Raised when there is a configuration issue, such as a missing provider."""
    pass

class FeatureValidationError(ValidationError):
    """Raised when quantitative features fail integrity checks."""
    pass
