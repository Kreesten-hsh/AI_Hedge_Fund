from __future__ import annotations

import os
from types import TracebackType
from typing import Any

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.gateway import BaseGateway


class VnPyEngineManager:
    """
    Manages the lifecycle of vn.py's MainEngine and EventEngine.
    This component handles the raw infrastructure connections.
    """

    def __init__(self) -> None:
        # vn.py's MainEngine.__init__ starts the EventEngine's two non-daemon
        # threads and chdir's into TRADER_DIR. Both are process-wide side
        # effects, so this object owns an explicit shutdown (see close()).
        self._cwd_before_init = os.getcwd()
        self.event_engine = EventEngine()
        self.main_engine = MainEngine(self.event_engine)
        self._is_connected = False
        self._is_closed = False

    def add_gateway(self, gateway_class: type[BaseGateway]) -> None:
        self.main_engine.add_gateway(gateway_class)

    def connect(self, gateway_name: str, settings: dict[str, Any]) -> None:
        """
        Connects to a specific gateway with the provided settings.
        Settings should be loaded from .env and passed here, keeping this class pure.
        """
        self.main_engine.connect(settings, gateway_name)
        self._is_connected = True

    def disconnect(self, gateway_name: str) -> None:
        self.close()

    def close(self) -> None:
        """
        Stops the EventEngine's non-daemon threads and closes every gateway.

        Without this, the interpreter never exits: EventEngine._run and
        _run_timer are non-daemon threads spawned by MainEngine.__init__, so
        any process that merely constructs this manager hangs at shutdown.
        Idempotent — EventEngine.stop() joins threads and would raise if
        called twice.
        """
        if self._is_closed:
            return
        self._is_closed = True
        self._is_connected = False
        try:
            self.main_engine.close()
        finally:
            os.chdir(self._cwd_before_init)

    def health_check(self) -> str:
        if self._is_connected:
            return "Connected"
        return "Disconnected"

    def __enter__(self) -> VnPyEngineManager:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
