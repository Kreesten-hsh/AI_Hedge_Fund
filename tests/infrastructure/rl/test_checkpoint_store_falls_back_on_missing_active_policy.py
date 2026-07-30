import os
import tempfile
import pytest

from aegis_trade.infrastructure.rl.policy_checkpoint_store import PolicyCheckpointStore

def test_checkpoint_store_falls_back_on_missing_active_policy():
    """
    Verifies that load_active_policy returns None and fails gracefully if 
    the active_policy.json meta file is missing, corrupt, or invalid.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        store = PolicyCheckpointStore(storage_dir=tmpdir)
        
        # 1. Missing file -> should return None
        policy = store.load_active_policy()
        assert policy is None, "Should fallback to None if active_policy.json is missing"
        
        # 2. Invalid/Corrupt file -> should return None
        meta_path = os.path.join(tmpdir, "active_policy.json")
        with open(meta_path, "w") as f:
            f.write("{invalid_json:")
            
        policy = store.load_active_policy()
        assert policy is None, "Should fallback to None if active_policy.json is corrupt"
        
        # 3. Valid JSON but missing model_id -> should return None
        with open(meta_path, "w") as f:
            f.write('{"promoted_at": "2026-07-30T00:00:00"}')
            
        policy = store.load_active_policy()
        assert policy is None, "Should fallback to None if active_policy.json is missing model_id"

        # 4. Valid JSON with model_id but actual zip missing -> should return None
        with open(meta_path, "w") as f:
            f.write('{"model_id": "ppo_missing_123"}')
            
        policy = store.load_active_policy()
        assert policy is None, "Should fallback to None if active_policy.json points to missing zip file"
