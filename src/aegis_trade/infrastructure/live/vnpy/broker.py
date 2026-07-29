from aegis_trade.domain.ports.broker import ILiveBroker, IMarketGateway, IExecutionGateway
from .market_data import VnPyMarketGateway
from .execution import VnPyExecutionGateway

class VnPyBroker(ILiveBroker):
    def __init__(self, market_gateway: VnPyMarketGateway, execution_gateway: VnPyExecutionGateway):
        self._market_gateway = market_gateway
        self._execution_gateway = execution_gateway

    @property
    def market_gateway(self) -> IMarketGateway:
        return self._market_gateway
        
    @property
    def execution_gateway(self) -> IExecutionGateway:
        return self._execution_gateway
