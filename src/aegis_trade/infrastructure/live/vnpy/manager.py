import os
from typing import Optional
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.constant import Exchange

class VnPyEngineManager:
    """
    Manages the lifecycle of vn.py's MainEngine and EventEngine.
    This component handles the raw infrastructure connections.
    """
    def __init__(self):
        self.event_engine = EventEngine()
        self.main_engine = MainEngine(self.event_engine)
        self._is_connected = False
        
    def add_gateway(self, gateway_class):
        self.main_engine.add_gateway(gateway_class)
        
    def connect(self, gateway_name: str, settings: dict):
        """
        Connects to a specific gateway with the provided settings.
        Settings should be loaded from .env and passed here, keeping this class pure.
        """
        self.main_engine.connect(settings, gateway_name)
        self._is_connected = True
        
    def disconnect(self, gateway_name: str):
        self.main_engine.close()
        self._is_connected = False
        
    def health_check(self) -> str:
        if self._is_connected:
            return "Connected"
        return "Disconnected"
