import os
import sys
from decimal import Decimal
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from aegis_trade.domain import Symbol, AssetClass
from aegis_trade.engine.events import OrderEvent, OrderAction, MarketEvent
from aegis_trade.domain import MarketBar
from aegis_trade.engine.portfolio import PortfolioEngine
from aegis_trade.engine.global_risk import GlobalRiskManager

def main():
    print("==========================================================")
    print("AEGIS QUANT OS - GLOBAL RISK GOVERNANCE DEMO (KILL SWITCH)")
    print("==========================================================")
    
    # 1. Initialize Portfolio and Risk Manager
    print("[1] Initializing PortfolioEngine with GlobalRiskManager...")
    risk_manager = GlobalRiskManager(max_drawdown=Decimal("0.05")) # 5% max drawdown
    portfolio = PortfolioEngine(initial_capital=10000.0, risk_manager=risk_manager)
    
    print(f"    Initial Capital: ${portfolio.initial_capital}")
    
    # 2. Simulate Market Price (XAUUSD at 2000.0)
    print("\n[2] Simulating Market Event (XAUUSD @ 2000.0)...")
    sym = Symbol("XAUUSD", AssetClass.COMMODITIES)
    bar = MarketBar(
        symbol=sym,
        timestamp=datetime.now(timezone.utc),
        open=Decimal("2000.0"),
        high=Decimal("2000.0"),
        low=Decimal("2000.0"),
        close=Decimal("2000.0"),
        volume=Decimal("100.0")
    )
    market_event = MarketEvent(bar=bar)
    portfolio.on_market_event(market_event)
    
    # 3. Simulate Drawdown
    print("\n[3] Simulating massive losses...")
    print("    Portfolio drops from $10,000 to $9,400 (6% Drawdown)")
    
    # Hack the equity to simulate the drop while keeping the High Water Mark
    # The portfolio tracks equity_curve for HWM.
    portfolio.equity = Decimal("9400.0")
    # In a real system, the equity curve updates automatically via MarketEvents and PnL.
    
    # 4. Simulate a "perfect" AI signal that we must block
    print("\n[4] AiDecisionEngine generates a 'Perfect' BUY order (1.0 XAUUSD)...")
    order = OrderEvent(
        timestamp=datetime.now(timezone.utc),
        symbol=sym,
        action=OrderAction.BUY,
        volume=Decimal("1.0"),
        strategy_id="Council_AI_Super_Signal"
    )
    
    # 5. PortfolioEngine intercepts the order
    print("\n[5] PortfolioEngine intercepts the order for Risk Validation:")
    is_approved, processed_event = portfolio.process_order(order)
    
    if is_approved:
        print("    [!] FATAL ERROR: Order was approved despite Kill Switch.")
    else:
        print(f"    [X] Order REJECTED!")
        print(f"    Audit Trace: {processed_event.message}")
        
    print("\n==========================================================")
    print("DEMO COMPLETE: Institution Shield Active.")
    print("==========================================================")

if __name__ == "__main__":
    main()
