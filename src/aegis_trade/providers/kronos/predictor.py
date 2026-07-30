import torch
import numpy as np
import logging
from typing import List, Tuple, Any

logger = logging.getLogger(__name__)

class KronosPredictor:
    """
    Handles inference for Kronos-mini, including ensemble logic for confidence.
    """
    def __init__(self, pipeline: Any):
        self.pipeline = pipeline

    def predict(self, context_tensor: torch.Tensor, prediction_length: int = 10, num_samples: int = 10) -> Tuple[List[float], Tuple[float, float]]:
        """
        Runs inference and returns (median_prediction, (low_bound, high_bound)).
        Uses sampling (ensemble) to generate bounds.
        """
        if self.pipeline is None:
            logger.warning("Predictor called with None pipeline. Returning zeros.")
            return [0.0]*prediction_length, (0.0, 0.0)
            
        try:
            # Assuming context_tensor is shape (batch_size, context_length)
            # The chronos pipeline returns shape (batch_size, num_samples, prediction_length)
            forecast = self.pipeline.predict(
                context_tensor,
                prediction_length=prediction_length,
                num_samples=num_samples,
                temperature=1.0,
                top_p=0.9
            )
            
            # Extract first batch item (we usually predict for one symbol at a time in the background)
            # shape: (num_samples, prediction_length)
            samples = forecast[0].numpy()
            
            median_pred = np.median(samples, axis=0).tolist()
            
            # Confidence interval (e.g., 10th and 90th percentiles for the LAST predicted point or avg across horizon)
            low_bound = float(np.percentile(samples, 10, axis=0)[-1])
            high_bound = float(np.percentile(samples, 90, axis=0)[-1])
            
            return median_pred, (low_bound, high_bound)
            
        except Exception as e:
            logger.error(f"Inference failed: {e}")
            return [0.0]*prediction_length, (0.0, 0.0)
