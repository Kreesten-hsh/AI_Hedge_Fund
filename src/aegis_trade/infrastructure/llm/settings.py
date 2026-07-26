import os
import yaml
from typing import Any, Dict, Optional
from aegis_trade.exceptions import ConfigurationError

class LLMSettings:
    """
    Central configuration class for LLM Infrastructure.
    Responsible for reading, validating, and exposing LLM settings.
    """
    
    _instance = None
    
    def __init__(self, config_path: str = "config/llm.yaml"):
        self.config_path = config_path
        self._raw_config: Dict[str, Any] = {}
        self.active_profile: str = ""
        self.provider: str = ""
        self.model: str = ""
        self.temperature: float = 0.0
        self.format: Optional[str] = None
        self.timeout: int = 120
        self.keep_alive: int = 0
        
        self.load()
        
    @classmethod
    def get_instance(cls, config_path: str = "config/llm.yaml") -> 'LLMSettings':
        if cls._instance is None:
            cls._instance = cls(config_path)
        return cls._instance
        
    def load(self):
        if not os.path.exists(self.config_path):
            raise ConfigurationError(f"Missing configuration file: {self.config_path}")
            
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            raise ConfigurationError(f"Failed to parse YAML from {self.config_path}: {e}")
            
        if not data or "llm" not in data:
            raise ConfigurationError(f"Invalid YAML structure: missing 'llm' root key in {self.config_path}")
            
        llm_config = data["llm"]
        
        self.active_profile = llm_config.get("active_profile")
        if not self.active_profile:
            raise ConfigurationError("Missing 'active_profile' in configuration.")
            
        profiles = llm_config.get("profiles", {})
        if self.active_profile not in profiles:
            raise ConfigurationError(f"Active profile '{self.active_profile}' not found in 'profiles'.")
            
        profile_data = profiles[self.active_profile]
        
        # Validation
        self.provider = profile_data.get("provider")
        if not self.provider:
            raise ConfigurationError("Profile is missing 'provider'.")
            
        self.model = profile_data.get("model")
        if not self.model:
            raise ConfigurationError("Profile is missing 'model'.")
            
        try:
            self.temperature = float(profile_data.get("temperature", 0.0))
            if not (0.0 <= self.temperature <= 1.0):
                raise ValueError()
        except ValueError:
            raise ConfigurationError("Temperature must be a float between 0.0 and 1.0.")
            
        self.format = profile_data.get("format")
        if self.format and self.format not in ("json", "text"):
            raise ConfigurationError("Format must be 'json' or 'text'.")
            
        try:
            self.timeout = int(profile_data.get("timeout", 120))
            if self.timeout <= 0:
                raise ValueError()
        except ValueError:
            raise ConfigurationError("Timeout must be a positive integer.")
            
        try:
            self.keep_alive = int(profile_data.get("keep_alive", 0))
            if self.keep_alive < 0:
                raise ValueError()
        except ValueError:
            raise ConfigurationError("Keep_alive must be a non-negative integer.")
            
        self._raw_config = data
        
    def reload(self):
        self.load()
