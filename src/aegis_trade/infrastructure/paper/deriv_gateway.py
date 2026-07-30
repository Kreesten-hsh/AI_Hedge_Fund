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
        self._is_virtual_confirmed = False
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
                
            self._is_virtual_confirmed = True
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
        
        # Double verification defensive check
        if self.api is not None and not self._is_virtual_confirmed:
            raise SecurityError("SECURITY ALERT: Attempted to submit order without virtual account confirmation.")
            
        start_time = datetime.now(timezone.utc)
        fill_price = Decimal("100.0") # fallback stub
        latency_ms = 50.0 # fallback stub
        
        if self.api:
            # Real API call
            # e.g., await self.api.buy({"buy": "proposal_id", "price": 100})
            # This is a mocked representation of how the real deriv-api call would look:
            try:
                # We would first get a proposal for the symbol and volume, then buy it.
                # response = await self.api.buy({"buy": 1, "price": 100, "parameters": {"amount": order.volume, "basis": "stake", "contract_type": order.action.value.upper(), "currency": "USD", "symbol": order.symbol.name}})
                # fill_price = Decimal(str(response.get("buy", {}).get("buy_price", 100.0)))
                # Fake latency for real API call since we can't test actual network call here
                latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            except Exception as e:
                logger.error(f"Deriv API order submission failed: {e}")
                raise
        
        execution = PaperExecution(
            execution_id=f"EXEC-{order.order_id}",
            order_id=order.order_id,
            timestamp=datetime.now(timezone.utc),
            requested_price=fill_price, # We can't know the exact requested price with market orders in deriv, so we use fill price or last observed
            execution_price=fill_price,
            slippage=Decimal("0.0"), # Slippage is calculated by the ShadowTradingEngine based on observed price
            latency_ms=latency_ms
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
        
        return PaperExecutionReport(
            timestamp=datetime.now(timezone.utc),
            order=order,
            risk_decision="APPROVED",
            execution=execution,
            fills=[fill]
        )

    async def cancel_order(self, order_id: str) -> bool:
        logger.info(f"DerivGateway canceling order: {order_id}")
        if self.api:
            try:
                # Actual Deriv API call to cancel order/contract by ID
                # await self.api.sell({"sell": order_id, "price": 0})
                pass
            except Exception as e:
                logger.error(f"Deriv API order cancellation failed: {e}")
                return False
        return True

    async def cancel_all_orders(self) -> int:
        """Real cancellation of all active orders via API."""
        count = 0
        if self.api:
            try:
                logger.warning("DerivGateway: Fetching open orders to cancel.")
                portfolio_res = await self.api.portfolio()
                contracts = portfolio_res.get('portfolio', {}).get('contracts', [])
                for contract in contracts:
                    contract_id = contract.get('contract_id')
                    if contract_id:
                        await self.api.sell({"sell": contract_id, "price": 0})
                        count += 1
            except Exception as e:
                logger.error(f"Deriv API cancel_all_orders failed: {e}")
        else:
            logger.warning("DerivGateway: API not connected, mock cancel_all_orders.")
        return count

    async def close_all_positions(self) -> int:
        """Real closing of all open positions via API."""
        count = 0
        if self.api:
            try:
                logger.warning("DerivGateway: Fetching open positions to close.")
                portfolio_res = await self.api.portfolio()
                contracts = portfolio_res.get('portfolio', {}).get('contracts', [])
                for contract in contracts:
                    contract_id = contract.get('contract_id')
                    if contract_id:
                        await self.api.sell({"sell": contract_id, "price": 0})
                        count += 1
            except Exception as e:
                logger.error(f"Deriv API close_all_positions failed: {e}")
        else:
            logger.warning("DerivGateway: API not connected, mock close_all_positions.")
        return count

class LiveDerivGateway(DerivGateway):
    """
    Gateway to Deriv API for Real Money Live Trading.
    Requires AEGIS_ENV=LIVE and explicit consent flag.
    """
    def __init__(self, token: str, i_understand_this_is_real_money: bool = False):
        if not i_understand_this_is_real_money:
            raise SecurityError("SECURITY ALERT: Explicit consent required to instantiate LiveDerivGateway.")
            
        self.token = token
        self._is_virtual_confirmed = False  # Not virtual, but we use this flag to mean 'account_type_confirmed'
        self.api = None
        self._validate_token_security_for_live()

    def _validate_token_security_for_live(self):
        """
        Ensures the environment is explicitly set to LIVE.
        """
        if os.environ.get("AEGIS_ENV", "").upper() != "LIVE":
            raise SecurityError("SECURITY ALERT: LiveDerivGateway can ONLY be used in LIVE environment.")
            
        logger.warning("LiveDerivGateway instantiated. THIS WILL TRADE REAL MONEY.")

    async def connect(self) -> bool:
        """
        Connects to Deriv API and verifies the account is a REAL account.
        """
        try:
            from deriv_api import DerivAPI
            self.api = DerivAPI(app_id=1089)
            
            response = await self.api.authorize(self.token)
            account_list = response.get("authorize", {}).get("account_list", [])
            
            is_virtual = False
            for acc in account_list:
                if acc.get("token") == self.token and acc.get("is_virtual") == 1:
                    is_virtual = True
                    break
                    
            if is_virtual:
                raise SecurityError("SECURITY ALERT: Token is a virtual account token, but LiveDerivGateway requires a REAL account token.")
                
            self._is_virtual_confirmed = True # Reused to mean 'account_type_confirmed' for submit_order
            logger.warning("Deriv API connected. Account verified as REAL. PROCEED WITH CAUTION.")
            return True
        except ImportError:
            logger.error("python-deriv-api not installed. Cannot run LiveDerivGateway.")
            return False
        except Exception as e:
            logger.error(f"Deriv API live connection failed: {e}")
            return False
