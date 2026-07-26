import pytest
import os
import tempfile
import yaml
from aegis_trade.infrastructure.llm.settings import LLMSettings
from aegis_trade.exceptions import ConfigurationError

def create_temp_yaml(data: dict) -> str:
    fd, path = tempfile.mkstemp(suffix=".yaml")
    with os.fdopen(fd, 'w') as f:
        yaml.dump(data, f)
    return path

def test_valid_yaml():
    data = {
        "llm": {
            "active_profile": "test_profile",
            "profiles": {
                "test_profile": {
                    "provider": "mock",
                    "model": "test-model",
                    "temperature": 0.5,
                    "timeout": 100,
                    "format": "json",
                    "keep_alive": 5
                }
            }
        }
    }
    path = create_temp_yaml(data)
    try:
        settings = LLMSettings(config_path=path)
        assert settings.provider == "mock"
        assert settings.model == "test-model"
        assert settings.temperature == 0.5
        assert settings.timeout == 100
        assert settings.format == "json"
        assert settings.keep_alive == 5
    finally:
        os.remove(path)

def test_missing_configuration():
    with pytest.raises(ConfigurationError, match="Missing configuration file"):
        LLMSettings(config_path="non_existent_file.yaml")

def test_invalid_yaml_format():
    fd, path = tempfile.mkstemp(suffix=".yaml")
    with os.fdopen(fd, 'w') as f:
        f.write("llm: [invalid yaml\n")
    try:
        with pytest.raises(ConfigurationError, match="Failed to parse YAML"):
            LLMSettings(config_path=path)
    finally:
        os.remove(path)

def test_missing_llm_root():
    data = {"wrong_root": {}}
    path = create_temp_yaml(data)
    try:
        with pytest.raises(ConfigurationError, match="missing 'llm' root key"):
            LLMSettings(config_path=path)
    finally:
        os.remove(path)

def test_missing_active_profile():
    data = {"llm": {"profiles": {}}}
    path = create_temp_yaml(data)
    try:
        with pytest.raises(ConfigurationError, match="Missing 'active_profile'"):
            LLMSettings(config_path=path)
    finally:
        os.remove(path)

def test_invalid_profile():
    data = {
        "llm": {
            "active_profile": "unknown",
            "profiles": {
                "test_profile": {}
            }
        }
    }
    path = create_temp_yaml(data)
    try:
        with pytest.raises(ConfigurationError, match="Active profile 'unknown' not found"):
            LLMSettings(config_path=path)
    finally:
        os.remove(path)

def test_missing_provider():
    data = {
        "llm": {
            "active_profile": "test",
            "profiles": {
                "test": {
                    "model": "model_a"
                }
            }
        }
    }
    path = create_temp_yaml(data)
    try:
        with pytest.raises(ConfigurationError, match="Profile is missing 'provider'"):
            LLMSettings(config_path=path)
    finally:
        os.remove(path)

def test_invalid_temperature():
    data = {
        "llm": {
            "active_profile": "test",
            "profiles": {
                "test": {
                    "provider": "mock",
                    "model": "m1",
                    "temperature": 1.5
                }
            }
        }
    }
    path = create_temp_yaml(data)
    try:
        with pytest.raises(ConfigurationError, match="Temperature must be a float between 0.0 and 1.0"):
            LLMSettings(config_path=path)
    finally:
        os.remove(path)
