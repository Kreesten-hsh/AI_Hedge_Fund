import pytest
from unittest.mock import patch, MagicMock

from aegis_trade.providers.qlib_adapter import QlibAdapter

def test_qlib_adapter_initializes_successfully():
    adapter = QlibAdapter()
    assert adapter.is_available() is False
    
    # We mock qlib to simulate it being installed and working
    with patch("builtins.__import__") as mock_import:
        mock_qlib = MagicMock()
        mock_import.return_value = mock_qlib
        
        result = adapter.initialize(provider_uri="mock_uri")
        
        assert result is True
        assert adapter.is_available() is True
        mock_qlib.init.assert_called_once_with(provider_uri="mock_uri")

def test_qlib_adapter_handles_missing_qlib():
    adapter = QlibAdapter()
    
    # We simulate ImportError when trying to import qlib
    with patch("builtins.__import__", side_effect=ImportError("No module named 'qlib'")):
        result = adapter.initialize()
        
        assert result is False
        assert adapter.is_available() is False
