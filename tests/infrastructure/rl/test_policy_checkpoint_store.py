"""
Tests for Policy Checkpoint Store.
"""

import os
import pytest
from src.aegis_trade.infrastructure.rl.policy_checkpoint_store import PolicyCheckpointStore

# Mock stable_baselines3 to avoid actual torch/SB3 initialization during unit tests
import sys
from unittest.mock import MagicMock
sys.modules['stable_baselines3'] = MagicMock()

def test_checkpoint_store_initialization(tmp_path):
    store_dir = str(tmp_path / "rl_models")
    store = PolicyCheckpointStore(storage_dir=store_dir)
    assert os.path.exists(store_dir)


def test_checkpoint_store_save(tmp_path):
    store_dir = str(tmp_path / "rl_models")
    store = PolicyCheckpointStore(storage_dir=store_dir)
    
    # Create dummy source file
    source_file = tmp_path / "dummy.zip"
    source_file.write_text("dummy content")
    
    store.save_policy("model_1", str(source_file))
    
    expected_dest = os.path.join(store_dir, "model_1.zip")
    assert os.path.exists(expected_dest)
