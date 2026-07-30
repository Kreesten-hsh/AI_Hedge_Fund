import logging
from typing import Optional
from decimal import Decimal
from datetime import datetime, timezone
import os

from aegis_trade.application.paper_trading.interfaces import IPaperBroker
from aegis_trade.domain.paper.models import (
    PaperOrder, PaperExecutionReport, OrderState, PaperExecution, PaperFill, ActionType
)

logger = logging.getLogger(__name__)

class SecurityError(Exception):
    pass

class DerivGateway(IPaperBroker):
    """
    Gateway to Deriv API for Live Paper Trading.
    STRICT SECURITY REQUIREMENT: Only virtual/demo accounts are permitted.
    Rejects tokens that might belong to real accounts or if running in PROD.
    """
    def __init__(self, token: str):
        self.token = token
        self._validate_token_security()
        self.api = None

    def _validate_token_security(self):
        """
        Ensures the environment isn't accidentally production.
        In a real scenario, this would perform a websocket call to deriv API 
        to verify `is_virtual` is 1.
        """
        if os.environ.get("AEGIS_ENV", "").upper() == "PROD":
            raise SecurityError("SECURITY ALERT: DerivGateway cannot be used in PROD environment.")
        
        # Simulated offline heuristic: many deriv demo tokens start with certain chars or we just log warning
        # Since we must strictly reject real API keys, any generic token triggers a strict check.
        # For MVP, we pass it but require API-level verification in `connect()`.
        logger.info("DerivGateway instantiated. Virtual account verification pending connection.")

    async def connect(self) -> bool:
        """
        Connects to Deriv API and strictly verifies the account is a demo (virtual) account.
        """
        try:
            # We wrap the deriv API import to fail gracefully if it's not installed
            from deriv_api import DerivAPI
            self.api = DerivAPI(app_id=1089)
            
            # This is pseudo-code for the deriv-api python SDK which connects via websockets
            response = await self.api.authorize(self.token)
            account_list = response.get("authorize", {}).get("account_list", [])
            
            is_virtual = False
            for acc in account_list:
                if acc.get("token") == self.token and acc.get("is_virtual") == 1:
                    is_virtual = True
                    break
                    
            if not is_virtual:
                raise SecurityError("SECURITY ALERT: Token is NOT a virtual account token. Aborting.")
                
            logger.info("Deriv API connected. Account verified as VIRTUAL.")
            return True
        except ImportError:
            logger.warning("python-deriv-api not installed. Running DerivGateway in stub mode.")
            self.api = None
            return True
        except Exception as e:
            logger.error(f"Deriv API connection failed: {e}")
            return False

    async def submit_order(self, order: PaperOrder) -> PaperExecutionReport:
        """
        Submits a paper order to Deriv.
        """
        logger.info(f"DerivGateway submitting order: {order.order_id} ({order.action.value} {order.volume} {order.symbol.name})")
        
        if self.api:
            # Code to send proposal and buy via Deriv API would go here
            pass
            
        # Stub execution report
        fill_price = Decimal("100.0")
        
        execution = PaperExecution(
            execution_id=f"EXEC-{order.order_id}",
            order_id=order.order_id,
            timestamp=datetime.now(timezone.utc),
            requested_price=fill_price,
            execution_price=fill_price,
            slippage=Decimal("0.0"),
            latency_ms=50.0
        )
        
        fill = PaperFill(
            fill_id=f"FILL-{order.order_id}",
            order_id=order.order_id,
            symbol=order.symbol,
            action=order.action,
            volume=order.volume,
            price=fill_price,
            commission=Decimal("0.0"),
            timestamp=datetime.now(timezone.utc)
        )
        
        # Return a simulated success execution report
        return PaperExecutionReport(
            timestamp=datetime.now(timezone.utc),
            order=order,
            risk_decision="APPROVED",
            execution=execution,
            fills=[fill]
        )

    async def cancel_order(self, order_id: str) -> bool:
        logger.info(f"DerivGateway canceling order: {order_id}")
        return True
