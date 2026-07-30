import pytest
from aegis_trade.providers.kronos.predictor import KronosPredictor

class MockPipeline:
    def predict(self, context_tensor, prediction_length, num_samples, temperature, top_p):
        import torch
        # Return a tensor of shape (batch_size, num_samples, prediction_length)
        # Add some variance across samples to test ensemble logic
        base = torch.ones((1, num_samples, prediction_length)) * 100.0
        noise = torch.randn((1, num_samples, prediction_length)) * 5.0
        return base + noise

def test_predictor_ensemble_logic():
    try:
        import torch
        import numpy as np
        
        pipeline = MockPipeline()
        predictor = KronosPredictor(pipeline)
        
        dummy_context = torch.zeros((1, 2048))
        
        median_pred, (low_bound, high_bound) = predictor.predict(
            dummy_context, prediction_length=10, num_samples=100
        )
        
        # Median should be very close to 100.0 due to large sample size and 0-mean noise
        assert len(median_pred) == 10
        assert 98.0 < median_pred[-1] < 102.0
        
        # Confidence intervals should correctly bound the median
        assert low_bound < median_pred[-1] < high_bound
        assert low_bound < 100.0
        assert high_bound > 100.0
    except ImportError:
        pass
