import os
import sys
import logging
from decimal import Decimal
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from aegis_trade.domain import Symbol, AssetClass
from aegis_trade.engine.events import SignalEvent, SignalIntent, OrderEvent, OrderAction, MarketEvent
from aegis_trade.providers.vnpy_adapter import VnpyAdapter

# Mock classes for vnpy if not installed
try:
    from vnpy.trader.engine import MainEngine, EventEngine
except ImportError:
    MainEngine = type("MainEngine", (), {"send_order": lambda self, req, gw: "mock_vt_order_id_123"})
    EventEngine = type("EventEngine", (), {"register": lambda self, event, cb: None})

logging.basicConfig(level=logging.INFO, format="%(message)s")

def main():
    print("==========================================================")
    print("AEGIS QUANT OS - VN.PY PAPER TRADING SIMULATION")
    print("==========================================================")
    
    print("\n[1] Initializing Aegis Infrastructure...")
    
    # Instantiate mocked vn.py engines
    main_engine = MainEngine()
    event_engine = EventEngine()
    
    # 2. Instantiate the Adapter
    print("[2] Initializing VnpyAdapter (ACL)...")
    adapter = VnpyAdapter(main_engine=main_engine, event_engine=event_engine, gateway_name="PAPER")
    
    # 3. Simulate Council Signal
    print("[3] Simulating Council Validated SignalEvent (LONG)...")
    ts = datetime.now(timezone.utc)
    sym = Symbol("XAUUSD", AssetClass.COMMODITIES) # Corrected to COMMODITIES based on domain fix
    
    # We pretend the AI Decision Engine already processed this and output an OrderEvent
    # because VnpyAdapter takes OrderEvents (Broker interface).
    print("\n--- ROUTING TRACE ---")
    
    # Step A: Aegis Domain OrderEvent
    order_event = OrderEvent(
        timestamp=ts,
        symbol=sym,
        action=OrderAction.BUY,
        volume=Decimal("1.50"),
        strategy_id="Council_AI"
    )
    print(f"-> Aegis OrderEvent  : {order_event.action.value.upper()} {order_event.volume} {order_event.symbol.name}")
    
    # Step B: Pass to VnpyAdapter
    print(f"-> VnpyAdapter       : Intercepting OrderEvent, translating to vn.py OrderRequest...")
    
    # To catch what it sends to MainEngine, we can mock send_order
    original_send_order = main_engine.send_order
    
    def hook_send_order(req, gateway):
        print(f"-> vn.py OrderRequest: Exchange={req.exchange}, Direction={req.direction}, Volume={req.volume}, Type={req.type}")
        return original_send_order(req, gateway)
        
    main_engine.send_order = hook_send_order
    
    # Fire the event
    adapter.on_order_event(order_event, latest_market_event=None)
    
    print("\n[4] Execution successfully delegated to vn.py via Anti-Corruption Layer.")
    print("==========================================================")

if __name__ == "__main__":
    main()
