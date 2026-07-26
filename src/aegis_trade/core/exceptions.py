"""
Aegis Quant OS - Core Exceptions

Unified exception hierarchy for the entire Aegis Quant OS.
"""

class AegisError(Exception):
    """Base exception for all Aegis errors."""
    pass


# ==========================================
# Data & Core Domain Exceptions
# ==========================================

class DataError(AegisError):
    """Base exception for data related errors."""
    pass

class DataFetchError(DataError):
    pass

class MissingData(DataError):
    pass

class CorruptedData(DataError):
    pass

class InvalidMarketBar(DataError):
    pass

class InvalidTick(DataError):
    pass

class MarketClosed(DataError):
    pass


# ==========================================
# Infrastructure & Providers Exceptions
# ==========================================

class InfrastructureError(AegisError):
    """Base exception for infrastructure and external provider errors."""
    pass

class AuthenticationError(InfrastructureError):
    pass

class RateLimitError(InfrastructureError):
    pass

class ProviderUnavailable(InfrastructureError):
    pass

class ConfigurationError(InfrastructureError):
    """Raised when configuration validation fails."""
    pass



# ==========================================
# Artifact Store Exceptions
# ==========================================

class ArtifactStoreError(AegisError):
    """Base exception for artifact store operations."""
    pass

class AliasNotFoundError(ArtifactStoreError):
    pass

class VersionNotFoundError(ArtifactStoreError):
    pass

class AmbiguousResolutionError(ArtifactStoreError):
    pass


# ==========================================
# State Machine & Lifecycle Exceptions
# ==========================================

class StateMachineError(AegisError):
    """Base exception for invalid state transitions."""
    pass

class StateTransitionError(StateMachineError):
    """Used by Experiment Tracking."""
    pass

class InvalidStateTransitionError(StateMachineError):
    """Used by Runtime."""
    pass

class RegistryTransitionError(StateMachineError):
    """Used by ML Inference Registry."""
    pass


# ==========================================
# Validation & Compilation Exceptions
# ==========================================

class ValidationError(AegisError):
    """Base exception for all validation errors."""
    pass

class RuntimeValidationError(ValidationError):
    pass

class GraphValidationError(ValidationError):
    pass

class ObservabilityValidationError(ValidationError):
    pass

class SchemaMismatchError(ValidationError):
    pass

class CompatibilityError(ValidationError):
    pass


# ==========================================
# Planner & Scheduler Exceptions
# ==========================================

class SchedulingError(AegisError):
    """Base exception for planning and scheduling."""
    pass

class ExecutionPlannerError(SchedulingError):
    pass
