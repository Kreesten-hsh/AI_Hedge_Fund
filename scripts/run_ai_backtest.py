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

from aegis_trade.infrastructure.llm.settings import LLMSettings
from aegis_trade.infrastructure.llm.factory import LLMProviderFactory
from aegis_trade.agents.registry import AgentRegistry
from aegis_trade.agents.runner import AgentRunner
from aegis_trade.agents.council import CouncilOrchestrator
from aegis_trade.agents.synthesizer import CouncilSynthesizer
from aegis_trade.agents.regime_analyst import RegimeAnalyst
from aegis_trade.agents.macro_analyst import MacroAnalyst
from aegis_trade.agents.risk_analyst import RiskAnalyst

from aegis_trade.dataset.repository import StorageDatasetRepository
from aegis_trade.dataset.resolver import DatasetResolver

def main():
    print("==========================================================")
    print("AEGIS QUANT OS - AI-DRIVEN BACKTEST")
    print("==========================================================")

    # 1. Setup Agents & Cache
    print("[1] Initializing AI Agents and Cache...")
    settings = LLMSettings.get_instance()
    provider = LLMProviderFactory.create(settings)
    
    # Enable cache to avoid calling LLM hundreds of times
    runner = AgentRunner(provider=provider, use_cache=True)
    synthesizer = CouncilSynthesizer(provider=provider)
    
    registry = AgentRegistry()
    registry.register(RegimeAnalyst())
    registry.register(MacroAnalyst())
    registry.register(RiskAnalyst())
    
    orchestrator = CouncilOrchestrator(registry, runner, synthesizer)

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
    ai_engine = AiDecisionEngine(orchestrator=orchestrator, risk_pct=Decimal("0.10"), window_size=5)

    engine = TradingEngine(
        feed=feed,
        strategy=strategy,
        broker=broker,
        risk_engine=ai_engine,
        portfolio=portfolio
    )

    # 4. Execute Backtest
    print("\n[4] Running Backtest... (Signals will trigger cached LLM calls)")
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
