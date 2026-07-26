import os
import sys
import pandas as pd
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from aegis_trade.dataset.repository import StorageDatasetRepository
from aegis_trade.dataset.resolver import DatasetResolver
from aegis_trade.infrastructure.llm.settings import LLMSettings
from aegis_trade.infrastructure.llm.factory import LLMProviderFactory
from aegis_trade.agents.registry import AgentRegistry
from aegis_trade.agents.runner import AgentRunner
from aegis_trade.agents.council import CouncilOrchestrator
from aegis_trade.agents.synthesizer import CouncilSynthesizer
from aegis_trade.agents.regime_analyst import RegimeAnalyst
from aegis_trade.agents.macro_analyst import MacroAnalyst
from aegis_trade.agents.risk_analyst import RiskAnalyst
import aegis_trade.domain.reports

def main():
    print("="*60)
    print("AEGIS QUANT OS - RESEARCH COUNCIL DEMONSTRATION")
    print("="*60)

    # 1. Setup Infrastructure
    print("\n[1] Initializing Infrastructure...")
    settings = LLMSettings.get_instance()
    provider = LLMProviderFactory.create(settings)
    
    runner = AgentRunner(provider=provider)
    synthesizer = CouncilSynthesizer(provider=provider)
    
    registry = AgentRegistry()
    registry.register(RegimeAnalyst())
    registry.register(MacroAnalyst())
    registry.register(RiskAnalyst())
    print(f"    Registered Agents: {registry.capabilities()}")

    orchestrator = CouncilOrchestrator(registry, runner, synthesizer)

    # 2. Data Preparation
    print("\n[2] Loading Market Data Context...")
    repo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "datasets")
    repo = StorageDatasetRepository(repo_path)
    resolver = DatasetResolver(repo)

    dataset_xau = resolver.resolve_latest("XAUUSD", "H1")
    dataset_dxy = resolver.resolve_latest("DXY", "D1")

    if not dataset_xau or not dataset_dxy:
        print("Error: Missing datasets.")
        return

    xau_bars = resolver.load_data(dataset_xau)
    dxy_bars = resolver.load_data(dataset_dxy)

    df_xau = pd.DataFrame([
        {"timestamp": b.timestamp, "close": float(b.close), "high": float(b.high), "low": float(b.low)}
        for b in xau_bars
    ]).set_index("timestamp")

    df_dxy = pd.DataFrame([
        {"timestamp": b.timestamp, "dxy_close": float(b.close)}
        for b in dxy_bars
    ]).set_index("timestamp")

    df_dxy["dxy_sma5"] = df_dxy["dxy_close"].rolling(5).mean()
    df_dxy["dxy_trend"] = df_dxy.apply(
        lambda row: 1 if row["dxy_close"] > row["dxy_sma5"] else (-1 if row["dxy_close"] < row["dxy_sma5"] else 0),
        axis=1
    )

    df_merged = df_xau.join(df_dxy, how="outer")
    df_merged["dxy_close"] = df_merged["dxy_close"].ffill()
    df_merged["dxy_trend"] = df_merged["dxy_trend"].ffill()
    df_xau = df_merged.loc[df_xau.index].copy()

    # Create Context for the Runner
    last_5_bars = df_xau.tail(5)
    
    # Calculate dummy volatility/drawdown just for demonstration context
    atr_mock = (last_5_bars["high"] - last_5_bars["low"]).mean()
    volatility = f"{atr_mock:.2f} points"
    drawdown = "-1.5%"
    
    context = {
        "recent_price_action": json.dumps([
            {"timestamp": str(idx), "close": row["close"]}
            for idx, row in last_5_bars.iterrows()
        ]),
        "dxy_trend_filter": int(last_5_bars["dxy_trend"].iloc[-1]),
        "current_price": last_5_bars["close"].iloc[-1],
        "volatility": volatility,
        "drawdown": drawdown,
        "dxy_trend": "Bearish",
        "us10y_trend": "Falling",
        "atr": atr_mock,
        "avg_atr": atr_mock * 0.8,
        "volatility_regime": "elevated"
    }

    # 3. Execution
    print("\n[3] Executing Council Orchestrator...")
    print("    This will invoke the Regime Analyst, Risk Analyst, and Council Synthesizer via Ollama.")
    t0 = time.time()
    
    decision = orchestrator.generate_decision(context, intent="LONG")
    
    elapsed = time.time() - t0
    print(f"\n[4] Execution Complete in {elapsed:.2f}s")
    
    # 4. Results
    print("\n" + "="*60)
    print("FINAL COUNCIL DECISION")
    print("="*60)
    print(f"Action     : {decision.decision_type.upper()}")
    print(f"Confidence : {decision.confidence:.2f}")
    print(f"Multiplier : {decision.multiplier:.2f}")
    print(f"Reasoning  : {decision.reasoning}")
    print("\n--- SUPPORTING REPORTS ---")
    for r in decision.supporting_reports:
        print(f"\n[{r.capability.upper()} ANALYST]")
        print(json.dumps(r.data, indent=2))
    print("="*60)


if __name__ == "__main__":
    main()
