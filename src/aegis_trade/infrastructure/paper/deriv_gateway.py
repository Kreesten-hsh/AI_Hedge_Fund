import logging
from typing import Any, Dict
from decimal import Decimal
from datetime import datetime, timezone
import os

from aegis_trade.application.paper_trading.interfaces import IPaperBroker
from aegis_trade.domain.core import Tick
from aegis_trade.domain.paper.models import (
    PaperOrder, PaperExecutionReport, PaperExecution, PaperFill, ActionType
)
from aegis_trade.engine.risk_gate import recorded_decision

logger = logging.getLogger(__name__)

class SecurityError(Exception):
    pass


class NoMarketDataError(Exception):
    """Aucun prix réel disponible pour exécuter.

    Levée plutôt que compensée par une valeur par défaut : un prix inventé
    produit un P&L faux, donc un drawdown faux, donc un kill switch aveugle.
    """

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
        self.api: Any = None
        self._last_ticks: Dict[str, Tick] = {}

    def _validate_token_security(self) -> None:
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

        Le prix d'exécution vient du marché — réponse de l'API si elle est
        branchée, sinon dernière cotation observée. En l'absence des deux, on
        lève : un prix inventé produirait un P&L faux, donc une décision de
        risque fausse.
        """
        logger.info(f"DerivGateway submitting order: {order.order_id} ({order.action.value} {order.volume} {order.symbol.name})")

        # Double verification defensive check
        if self.api is not None and not self._is_virtual_confirmed:
            raise SecurityError("SECURITY ALERT: Attempted to submit order without virtual account confirmation.")

        start_time = datetime.now(timezone.utc)
        requested_price = self._last_price(order)
        fill_price = requested_price

        if self.api:
            response = await self.api.buy(self._build_buy_request(order, requested_price))
            fill_price = self._extract_fill_price(response, order)

        latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        execution = PaperExecution(
            execution_id=f"EXEC-{order.order_id}",
            order_id=order.order_id,
            timestamp=datetime.now(timezone.utc),
            requested_price=requested_price,
            execution_price=fill_price,
            slippage=fill_price - requested_price,
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
            risk_decision=self._risk_decision_for(order),
            execution=execution,
            fills=[fill]
        )

    def observe_tick(self, tick: Tick) -> None:
        """Enregistre la dernière cotation réelle reçue du flux de marché.

        C'est la seule voie par laquelle un prix entre dans ce broker hors
        réponse d'API. Sans appel à cette méthode, `submit_order` refuse.
        """
        self._last_ticks[tick.symbol.name] = tick

    def _last_price(self, order: PaperOrder) -> Decimal:
        """Prix d'exécution attendu : ask à l'achat, bid à la vente.

        Traverser le spread dans le bon sens n'est pas un détail cosmétique :
        exécuter un achat au bid offrirait au backtest un demi-spread gratuit
        à chaque ordre, ce qui suffit à rendre rentable une stratégie qui perd.
        """
        tick = self._last_ticks.get(order.symbol.name)
        if tick is None:
            raise NoMarketDataError(
                f"Aucune cotation observée pour {order.symbol.name}. Le broker "
                f"refuse d'exécuter : un prix par défaut fausserait le P&L et "
                f"donc le calcul de drawdown qui arme le kill switch."
            )
        return tick.ask if order.action == ActionType.BUY else tick.bid

    def _risk_decision_for(self, order: PaperOrder) -> str:
        """Décision de risque réellement portée par l'ordre.

        Le `RiskGate` inscrit sa décision dans `context_features` au moment de
        l'autorisation. La lecture est mutualisée avec les autres brokers pour
        qu'aucun d'eux ne puisse en donner sa propre version optimiste.
        """
        return recorded_decision(order.context_features)

    def _build_buy_request(self, order: PaperOrder, price: Decimal) -> Dict[str, Any]:
        return {
            "buy": 1,
            "price": float(price),
            "parameters": {
                "amount": float(order.volume),
                "basis": "stake",
                "contract_type": "CALL" if order.action == ActionType.BUY else "PUT",
                "currency": "USD",
                "symbol": order.symbol.name,
                "duration": 5,
                "duration_unit": "t",
            },
        }

    def _extract_fill_price(self, response: Any, order: PaperOrder) -> Decimal:
        buy = response.get("buy") if isinstance(response, dict) else None
        if not isinstance(buy, dict) or "buy_price" not in buy:
            raise NoMarketDataError(
                f"Réponse Deriv sans `buy_price` pour {order.order_id} : "
                f"impossible d'établir le prix de fill réel."
            )
        return Decimal(str(buy["buy_price"]))

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
        self.api: Any = None
        self._last_ticks: Dict[str, Tick] = {}
        self._validate_token_security_for_live()

    def _validate_token_security_for_live(self) -> None:
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
