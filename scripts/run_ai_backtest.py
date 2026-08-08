import os
import sys
import time
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from aegis_trade.engine.core import TradingEngine
from aegis_trade.engine.portfolio import Portfolio
from aegis_trade.engine.broker import SimulatedBroker
from aegis_trade.engine.feed import HistoricalReplayFeed
from aegis_trade.strategies.ema_cross import EmaCrossStrategy
from aegis_trade.engine.ai_decision_engine import AiDecisionEngine

from aegis_trade.application.council.orchestrator import MultiAgentCouncil
from aegis_trade.application.council.agents.trend_agent import TrendAgent
from aegis_trade.application.council.agents.momentum_agent import MomentumAgent
from aegis_trade.application.council.agents.volatility_agent import VolatilityAgent
from aegis_trade.application.council.agents.liquidity_agent import LiquidityAgent
from aegis_trade.application.council.agents.pattern_agent import PatternAgent
from aegis_trade.application.council.agents.news_agent import NewsAgent
from aegis_trade.application.council.agents.execution_agent import ExecutionAgent
from aegis_trade.application.council.agents.portfolio_agent import PortfolioAgent

from aegis_trade.dataset.repository import StorageDatasetRepository
from aegis_trade.dataset.resolver import DatasetResolver

def main():
    print("==========================================================")
    print("AEGIS QUANT OS - DETERMINISTIC COUNCIL BACKTEST")
    print("==========================================================")

    # 1. Setup MultiAgentCouncil (8 Deterministic Agents)
    print("[1] Initializing MultiAgentCouncil...")
    agents = [
        TrendAgent(),
        MomentumAgent(),
        VolatilityAgent(),
        LiquidityAgent(),
        PatternAgent(),
        NewsAgent(),
        ExecutionAgent(),
        PortfolioAgent(),
    ]
    council = MultiAgentCouncil(agents=agents)

    # 2. Setup Data Feed
    print("[2] Loading Market Data...")
    repo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "datasets")
    repo = StorageDatasetRepository(repo_path)
    resolver = DatasetResolver(repo)

    dataset_xau = resolver.resolve_latest("XAUUSD", "H1")
    if not dataset_xau:
        print("Error: Missing XAUUSD dataset.")
        return

    feed = HistoricalReplayFeed(dataset=dataset_xau, resolver=resolver)

    # 3. Setup Trading Engine
    print("[3] Configuring AI Decision Engine...")
    strategy = EmaCrossStrategy(symbol="XAUUSD", fast_period=20, slow_period=50)
    broker = SimulatedBroker(commission_per_unit=Decimal("0.0001"))
    portfolio = Portfolio(initial_capital=Decimal("100000"))
    ai_engine = AiDecisionEngine(council=council, risk_pct=Decimal("0.10"), window_size=5)

    engine = TradingEngine(
        feed=feed,
        strategy=strategy,
        broker=broker,
        risk_engine=ai_engine,
        portfolio=portfolio
    )

    # 4. Execute Backtest
    print("\n[4] Running Backtest...")
    t0 = time.time()
    report = engine.run()
    elapsed = time.time() - t0

    # 5. Results
    print(f"\n[5] Backtest Complete in {elapsed:.2f}s")
    print("\n" + "="*60)
    print("FINAL PORTFOLIO METRICS")
    print("="*60)
    for k, v in report.metrics.items():
        if isinstance(v, float):
            print(f"{k.upper():<20} : {v:.4f}")
        else:
            print(f"{k.upper():<20} : {v}")
    print("==========================================================")

if __name__ == "__main__":
    main()
