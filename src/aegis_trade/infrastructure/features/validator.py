import math
from typing import List

from aegis_trade.domain.features import FeatureSet
from aegis_trade.domain.exceptions.data import FeatureValidationError

class FeatureValidator:
    """
    Validates FeatureSets for mathematical and chronological integrity.
    Checks for unexpected NaNs, Infs, duplicate timestamps, and temporal ordering.
    """
    
    def validate(self, feature_sets: List[FeatureSet], burn_in_periods: int = 200) -> List[FeatureSet]:
        """
        Validates the extracted features.
        
        Args:
            feature_sets: The list of FeatureSets to validate.
            burn_in_periods: The number of initial periods where NaNs are acceptable 
                             due to rolling window calculations (e.g., EMA 200).
                             
        Raises:
            FeatureValidationError: If data is corrupted, misordered, or contains unexpected NaNs.
        """
        if not feature_sets:
            return []
            
        previous_ts = None
        
        for i, fs in enumerate(feature_sets):
            # 1. Temporal integrity
            if previous_ts is not None:
                if fs.timestamp <= previous_ts:
                    raise FeatureValidationError(
                        f"Temporal violation: {fs.timestamp} is not strictly after {previous_ts}"
                    )
            previous_ts = fs.timestamp
            
            # 2. Mathematical integrity (NaNs and Infs)
            for feat_name, val in fs.features.items():
                if val is None or math.isnan(val):
                    # It is normal to have NaNs during the burn-in period.
                    # Beyond that, NaNs imply a calculation bug or missing source data.
                    if i >= burn_in_periods:
                        raise FeatureValidationError(
                            f"Unexpected NaN in feature '{feat_name}' at index {i} ({fs.timestamp}). "
                            f"Burn-in period is {burn_in_periods}."
                        )
                elif math.isinf(val):
                    raise FeatureValidationError(
                        f"Unexpected Inf in feature '{feat_name}' at index {i} ({fs.timestamp})."
                    )

        return feature_sets
