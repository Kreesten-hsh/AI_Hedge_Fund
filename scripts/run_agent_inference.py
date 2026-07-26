import os
import sys
import pandas as pd
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from aegis_trade.dataset.repository import StorageDatasetRepository
from aegis_trade.dataset.resolver import DatasetResolver
from aegis_trade.agents.regime_analyst import RegimeAnalyst

def main():
    print("Initializing Regime Analyst Inference Script...")
    repo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "datasets")
    repo = StorageDatasetRepository(repo_path)
    resolver = DatasetResolver(repo)

    print("Loading XAUUSD H1 and DXY D1 datasets...")
    dataset_xau = resolver.resolve_latest("XAUUSD", "H1")
    dataset_dxy = resolver.resolve_latest("DXY", "D1")

    if not dataset_xau or not dataset_dxy:
        print("Error: Missing datasets.")
        return

    xau_bars = resolver.load_data(dataset_xau)
    dxy_bars = resolver.load_data(dataset_dxy)

    # Convert to DataFrames
    df_xau = pd.DataFrame([
        {"timestamp": b.timestamp, "close": float(b.close), "high": float(b.high), "low": float(b.low)}
        for b in xau_bars
    ]).set_index("timestamp")

    df_dxy = pd.DataFrame([
        {"timestamp": b.timestamp, "dxy_close": float(b.close)}
        for b in dxy_bars
    ]).set_index("timestamp")

    # Align and calculate basic features for context
    df_dxy["dxy_sma5"] = df_dxy["dxy_close"].rolling(5).mean()
    df_dxy["dxy_trend"] = df_dxy.apply(
        lambda row: 1 if row["dxy_close"] > row["dxy_sma5"] else (-1 if row["dxy_close"] < row["dxy_sma5"] else 0),
        axis=1
    )

    df_merged = df_xau.join(df_dxy, how="outer")
    df_merged["dxy_close"] = df_merged["dxy_close"].ffill()
    df_merged["dxy_trend"] = df_merged["dxy_trend"].ffill()

    # Drop back to XAU index
    df_xau = df_merged.loc[df_xau.index].copy()

    # Get the last 5 bars
    last_5_bars = df_xau.tail(5)

    print("\nPreparing Macro Context...")
    context = {
        "asset": "XAUUSD",
        "current_timestamp": str(last_5_bars.index[-1]),
        "current_price": last_5_bars["close"].iloc[-1],
        "dxy_trend_filter": int(last_5_bars["dxy_trend"].iloc[-1]),
        "recent_price_action": [
            {"timestamp": str(idx), "close": row["close"], "dxy_close": row["dxy_close"]}
            for idx, row in last_5_bars.iterrows()
        ]
    }

    print(json.dumps(context, indent=2))
    
    print("\nInstantiating RegimeAnalyst (Model: llama3.1)...")
    analyst = RegimeAnalyst(model="llama3.1")
    
    print("Calling Ollama API (localhost:11434)...")
    try:
        report = analyst.analyze(context)
        print("\n" + "="*50)
        print("REGIME ANALYST REPORT")
        print("="*50)
        print(json.dumps(report, indent=2))
        print("="*50)
        print("\nSuccess! The LLM successfully parsed the data and returned a typed JSON response.")
    except Exception as e:
        print(f"\nInference Failed: {e}")

if __name__ == "__main__":
    main()
