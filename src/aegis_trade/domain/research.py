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
