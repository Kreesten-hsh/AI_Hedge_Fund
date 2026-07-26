import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from aegis_trade.providers.qlib_adapter import QlibAdapter

def main():
    print("==========================================")
    print("AEGIS QUANT OS - QLIB ADAPTER DEMO")
    print("==========================================")
    
    print("[1] Instantiate QlibAdapter...")
    adapter = QlibAdapter()
    
    print(f"    Available before init? {adapter.is_available()}")
    
    print("\n[2] Initializing Qlib via ACL...")
    # Initialize without downloading massive data
    success = adapter.initialize(provider_uri="~/.qlib/qlib_data/cn_data")
    
    print(f"\n[3] Initialization result: {'SUCCESS' if success else 'FAILED'}")
    print(f"    Available after init? {adapter.is_available()}")
    
    print("==========================================")
    print("DEMO COMPLETE")
    print("==========================================")

if __name__ == "__main__":
    main()
