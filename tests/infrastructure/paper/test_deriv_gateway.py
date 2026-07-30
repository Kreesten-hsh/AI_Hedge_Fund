import pytest
import os
from unittest.mock import patch

from aegis_trade.infrastructure.paper.deriv_gateway import DerivGateway, SecurityError

def test_deriv_gateway_rejects_prod_environment():
    with patch.dict(os.environ, {"AEGIS_ENV": "PROD"}):
        with pytest.raises(SecurityError) as exc:
            DerivGateway(token="dummy_token")
        
        assert "PROD" in str(exc.value)

@pytest.mark.anyio
async def test_deriv_gateway_stub_mode_connect():
    gateway = DerivGateway(token="demo_token_123")
    # By default, deriv_api is not installed or we can just let it fallback
    connected = await gateway.connect()
    assert connected is True
    assert gateway.api is None # Should fallback to stub mode if no deriv_api
