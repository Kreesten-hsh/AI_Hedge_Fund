import os
import logging
from typing import Optional, Any, Tuple
import torch
from .shiyu_model.kronos import KronosTokenizer, Kronos, KronosPredictor

logger = logging.getLogger(__name__)

class KronosModelFactory:
    """
    Factory for loading the true Kronos model from shiyu-coder.
    Downloads from HuggingFace and manages local cache.
    """
    TOKENIZER_NAME = "NeoQuasar/Kronos-Tokenizer-base"
    MODEL_NAME = "NeoQuasar/Kronos-mini"
    
    def __init__(self, cache_dir: str = "~/.cache/huggingface/hub"):
        self.cache_dir = os.path.expanduser(cache_dir)
        self.device = "cpu" # CPU only as per spec
        self._predictor = None

    def get_predictor(self) -> Optional[KronosPredictor]:
        """
        Loads and returns the KronosPredictor instance.
        Returns None if loading fails to prevent crashing the system.
        """
        if self._predictor is not None:
            return self._predictor
            
        try:
            logger.info(f"Loading tokenizer {self.TOKENIZER_NAME} to {self.device}...")
            tokenizer = KronosTokenizer.from_pretrained(self.TOKENIZER_NAME).to(self.device)
            
            logger.info(f"Loading model {self.MODEL_NAME} to {self.device}...")
            model = Kronos.from_pretrained(self.MODEL_NAME).to(self.device)
            
            # Put models in eval mode
            tokenizer.eval()
            model.eval()
            
            self._predictor = KronosPredictor(
                model=model,
                tokenizer=tokenizer,
                device=self.device,
                max_context=512,
                clip=5
            )
            
            logger.info("Kronos-mini loaded successfully.")
            return self._predictor
        except Exception as e:
            logger.error(f"Failed to load Kronos model: {e}")
            return None
