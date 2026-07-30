import os
import logging
from typing import Optional, Any
import torch

logger = logging.getLogger(__name__)

class KronosModelFactory:
    """
    Factory for loading the Kronos-mini model.
    Downloads from HuggingFace and manages local cache.
    """
    MODEL_NAME = "amazon/chronos-t5-mini"
    
    def __init__(self, cache_dir: str = "~/.cache/huggingface/hub"):
        self.cache_dir = os.path.expanduser(cache_dir)
        self.device = torch.device("cpu") # CPU only as per spec
        self._pipeline = None

    def get_pipeline(self) -> Any:
        """
        Loads and returns the ChronosPipeline.
        Returns None if loading fails to prevent crashing the system.
        """
        if self._pipeline is not None:
            return self._pipeline
            
        try:
            from chronos import ChronosPipeline
            logger.info(f"Loading {self.MODEL_NAME} to {self.device}...")
            self._pipeline = ChronosPipeline.from_pretrained(
                self.MODEL_NAME,
                device_map=self.device,
                torch_dtype=torch.float32,
            )
            logger.info("Kronos-mini loaded successfully.")
            return self._pipeline
        except ImportError:
            logger.error("chronos package is not installed. Run 'pip install chronos'.")
            return None
        except Exception as e:
            logger.error(f"Failed to load Kronos model: {e}")
            return None
