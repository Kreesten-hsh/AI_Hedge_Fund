from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
from aegis_trade.domain.core import Symbol, TimeFrame

@dataclass(frozen=True)
class FeatureScore:
    """
    Immutable representation of the evaluation metrics for a single quantitative feature.
    Contains no ML or array libraries (Pandas/Numpy), purely native Python types.
    """
    feature_name: str
    mean: float
    variance: float
    std_dev: float
    skewness: float
    kurtosis: float
    missing_rate: float
    
    # Information Coefficient metrics (Correlation with forward returns)
    ic_mean: float
    ic_std: float
    ic_information_ratio: float
    stability: float

    # Optional aggregate score combining IC, IR, and Stability
    final_score: float = 0.0

    # --- Significance block ---
    # `ic_mean` alone cannot answer "is there a signal": it is an average of
    # rolling windows with no dispersion budget attached. The fields below carry
    # that budget. They default to a null, non-significant state so that any
    # producer which does not compute them cannot silently claim significance.

    # Full-sample rank correlation between the feature at t and the forward
    # return at t+N. This is the headline IC; `ic_mean` is a rolling average and
    # will differ from it.
    ic_spearman: float = 0.0

    # Aligned, non-null (feature, forward return) pairs actually used.
    observations: int = 0

    # Observations corrected for forward-return overlap. Consecutive rows share
    # N-1 bars of their forward window, so the raw count overstates the
    # information available by roughly a factor N. Set to `observations // N`:
    # the size of the largest non-overlapping subsample.
    effective_observations: int = 0

    # Student t of `ic_spearman` against zero, computed on
    # `effective_observations`, not on `observations`.
    ic_t_stat: float = 0.0

    # |t| > 2 on the effective sample. Not a discovery claim: with dozens of
    # features tested at once, individual thresholds do not control the family
    # -wise error rate. A feature that fails this is out; one that passes it is
    # merely still in the running.
    is_significant: bool = False

@dataclass(frozen=True)
class ResearchMetadata:
    """
    Contextual information regarding the alpha research run.
    """
    symbol: Symbol
    timeframe: TimeFrame
    start_time: datetime
    end_time: datetime
    forward_returns_lag: int
    computation_timestamp: datetime = field(default_factory=lambda: datetime.utcnow())

@dataclass(frozen=True)
class AlphaResearchResult:
    """
    The final output of an Alpha Research Engine evaluation.
    Aggregates all feature scores, global correlations, and metadata.
    """
    metadata: ResearchMetadata
    feature_scores: Dict[str, FeatureScore]
    
    # Correlation matrix represented as nested dictionaries: dict[feature_x][feature_y] = correlation
    correlation_matrix: Dict[str, Dict[str, float]]
    
    # Ranked lists of features by their final score
    top_features: List[str]
    bottom_features: List[str]

from typing import Any
from uuid import uuid4
from enum import Enum
from aegis_trade.domain.validation import ValidationArtifact

class ExperimentStatus(str, Enum):
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"

class PromotionStatus(str, Enum):
    RESEARCH = "RESEARCH"
    VALIDATED = "VALIDATED"
    CANDIDATE = "CANDIDATE"
    APPROVED = "APPROVED"
    PAPER_TRADING = "PAPER_TRADING"

@dataclass(frozen=True)
class ExperimentMetadata:
    """
    Métadonnées immuables garantissant la traçabilité d'une expérience de recherche.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.utcnow())
    strategy_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    features: List[str] = field(default_factory=list)
    markets: List[str] = field(default_factory=list)
    timeframes: List[str] = field(default_factory=list)
    seed: int = 42
    git_commit: str = "unknown"
    config_version: str = "1.0"
    model_version: str = "1.0"
    parent_id: Optional[str] = None
    author: str = "system"

@dataclass(frozen=True)
class ExperimentConfig:
    """
    Configuration de l'expérience, incluant les paramètres pour le backtester et la validation.
    """
    strategy_class_name: str
    strategy_kwargs: Dict[str, Any]
    validation_config_dict: Dict[str, Any]
    data_sources: List[str]

@dataclass
class ExperimentResult:
    """
    Résultat d'une expérience contenant le rapport de validation.
    """
    validation_artifact: Optional[ValidationArtifact] = None
    execution_time_seconds: float = 0.0
    error_message: Optional[str] = None
    
    @property
    def passed(self) -> bool:
        if self.validation_artifact:
            return self.validation_artifact.report.is_approved
        return False
        
    @property
    def score(self) -> float:
        if self.validation_artifact:
            return self.validation_artifact.report.strategy_score
        return 0.0

@dataclass
class ResearchExperiment:
    """
    Agrégat métier principal du laboratoire de recherche.
    Combine Configuration, Métadonnées, et Résultats.
    """
    metadata: ExperimentMetadata
    config: ExperimentConfig
    result: ExperimentResult = field(default_factory=ExperimentResult)
    status: ExperimentStatus = ExperimentStatus.CREATED
    promotion_status: PromotionStatus = PromotionStatus.RESEARCH
    
    def transition_status(self, new_status: ExperimentStatus):
        """Vérifie que la transition est autorisée grossièrement."""
        # Simple gardien pour l'instant
        if self.status == ExperimentStatus.ARCHIVED:
            raise ValueError("Cannot transition out of ARCHIVED status.")
        self.status = new_status
        
    def transition_promotion(self, new_status: PromotionStatus):
        """Met à jour le statut de promotion."""
        if not self.result.passed and new_status in [PromotionStatus.CANDIDATE, PromotionStatus.APPROVED, PromotionStatus.PAPER_TRADING]:
            raise ValueError("Cannot promote an experiment that failed validation.")
        self.promotion_status = new_status

    def mark_completed(self, validation_artifact: ValidationArtifact, execution_time: float):
        self.result.validation_artifact = validation_artifact
        self.result.execution_time_seconds = execution_time
        self.transition_status(ExperimentStatus.COMPLETED)

    def mark_failed(self, error_message: str):
        self.result.error_message = error_message
        self.transition_status(ExperimentStatus.FAILED)
