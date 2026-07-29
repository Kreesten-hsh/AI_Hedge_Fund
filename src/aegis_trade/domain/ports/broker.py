from abc import ABC, abstractmethod
from typing import Any

# Future live broker interfaces for LIVE-02

class IBrokerGateway(ABC):
    @abstractmethod
    async def connect(self):
        pass
        
    @abstractmethod
    async def disconnect(self):
        pass

class IMarketGateway(ABC):
    @abstractmethod
    async def subscribe_market_data(self, symbol: str):
        pass

class IExecutionGateway(ABC):
    @abstractmethod
    async def send_order(self, order: Any):
        pass

class ILiveBroker(ABC):
    @property
    @abstractmethod
    def market_gateway(self) -> IMarketGateway:
        pass
        
    @property
    @abstractmethod
    def execution_gateway(self) -> IExecutionGateway:
        pass
