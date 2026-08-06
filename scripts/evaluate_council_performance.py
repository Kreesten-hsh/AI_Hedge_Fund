"""Harnais de test et diagnostic quantitatif du MultiAgentCouncil (8 agents).

Évalue le consensus déterministe généré par le Council (Trend, Momentum, Volatility, etc.)
sur les barres réelles M1 (Gold, Crash 1000) et calcule l'espérance nette P&L face aux coûts réels mesurés.
"""

from __future__ import annotations

import logging
from decimal import Decimal
import pandas as pd
import numpy as np

from aegis_trade.domain.core import Symbol, AssetClass, TimeFrame, MarketBar
from aegis_trade.domain.council import MarketContext
from aegis_trade.engine.portfolio import Portfolio
from aegis_trade.infrastructure.features.technical_extractor import TechnicalFeatureExtractor

from aegis_trade.application.council.orchestrator import MultiAgentCouncil
from aegis_trade.application.council.agents.trend_agent import TrendAgent
from aegis_trade.application.council.agents.momentum_agent import MomentumAgent
from aegis_trade.application.council.agents.volatility_agent import VolatilityAgent
from aegis_trade.application.council.agents.liquidity_agent import LiquidityAgent
from aegis_trade.application.council.agents.pattern_agent import PatternAgent
from aegis_trade.application.council.agents.news_agent import NewsAgent
from aegis_trade.application.council.agents.execution_agent import ExecutionAgent
from aegis_trade.application.council.agents.portfolio_agent import PortfolioAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def build_council() -> MultiAgentCouncil:
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
    return MultiAgentCouncil(agents=agents)


def evaluate_council_on_parquet(
    parquet_path: str,
    symbol_name: str,
    cost_bps: float,
    horizon: int = 5,
):
    logger.info(f"Évaluation du Council sur {symbol_name} ({parquet_path}), Coût: {cost_bps} bps, Horizon: {horizon}m")
    df = pd.read_parquet(parquet_path)
    
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df.set_index("timestamp", inplace=True)
    elif not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, utc=True)
        
    df.sort_index(inplace=True)
    
    symbol = Symbol(name=symbol_name, asset_class=AssetClass.COMMODITIES)
    timeframe = TimeFrame.M1
    
    bars: list[MarketBar] = []
    for ts, row in df.iterrows():
        bars.append(
            MarketBar(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts,
                open=Decimal(str(row["open"])),
                high=Decimal(str(row["high"])),
                low=Decimal(str(row["low"])),
                close=Decimal(str(row["close"])),
                volume=Decimal(str(row.get("volume", 1.0))),
            )
        )

    logger.info(f"Extraction des features techniques pour {len(bars)} barres...")
    extractor = TechnicalFeatureExtractor()
    feature_sets = extractor.extract(bars)
    
    portfolio = Portfolio(initial_capital=Decimal("10000.0"))
    council = build_council()
    
    verdicts: list[str] = []
    confidences: list[float] = []
    multipliers: list[float] = []
    
    logger.info("Exécution séquentielle du Council à 8 agents...")
    for fset, bar in zip(feature_sets, bars):
        ctx = MarketContext(
            symbol=symbol,
            features=fset.features,
            portfolio=portfolio,
            latest_prices={symbol: bar.close},
            memory_score=0.0
        )
        verdict = council.evaluate(ctx)
        verdicts.append(verdict.final_vote)
        confidences.append(verdict.aggregated_confidence)
        multipliers.append(verdict.position_size_multiplier)

    df_eval = pd.DataFrame({
        "close": [float(b.close) for b in bars],
        "verdict": verdicts,
        "confidence": confidences,
        "multiplier": multipliers,
    }, index=[b.timestamp for b in bars])

    df_eval["forward_return"] = df_eval["close"].pct_change(horizon).shift(-horizon)
    
    buy_signals = df_eval[df_eval["verdict"] == "BUY"]
    sell_signals = df_eval[df_eval["verdict"] == "SELL"]
    wait_signals = df_eval[df_eval["verdict"] == "WAIT"]
    
    print("\n" + "=" * 80)
    print(f"  RÉSULTATS DE L'AUDIT DU COUNCIL SUR {symbol_name} (75 000 barres M1)")
    print("=" * 80)
    print(f"  Distribution des Verdicts du Council:")
    print(f"    - BUY  : {len(buy_signals):>6} ({len(buy_signals)/len(df_eval)*100:.2f} %)")
    print(f"    - SELL : {len(sell_signals):>6} ({len(sell_signals)/len(df_eval)*100:.2f} %)")
    print(f"    - WAIT : {len(wait_signals):>6} ({len(wait_signals)/len(df_eval)*100:.2f} %)")
    print("-" * 80)

    cost_frac = cost_bps / 10000.0
    
    if len(buy_signals) > 0:
        ret_buy_gross = buy_signals["forward_return"].dropna()
        ret_buy_net = ret_buy_gross - cost_frac
        print(f"  Signaux BUY (n={len(ret_buy_gross)}):")
        print(f"    - Rendement moyen BRUT : {ret_buy_gross.mean()*10000:.3f} bps")
        print(f"    - Rendement moyen NET  : {ret_buy_net.mean()*10000:.3f} bps (Coût: {cost_bps} bps)")
        print(f"    - Win Rate             : {(ret_buy_gross > 0).mean()*100:.2f} %")
        
    if len(sell_signals) > 0:
        ret_sell_gross = -sell_signals["forward_return"].dropna()
        ret_sell_net = ret_sell_gross - cost_frac
        print(f"  Signaux SELL (n={len(ret_sell_gross)}):")
        print(f"    - Rendement moyen BRUT : {ret_sell_gross.mean()*10000:.3f} bps")
        print(f"    - Rendement moyen NET  : {ret_sell_net.mean()*10000:.3f} bps (Coût: {cost_bps} bps)")
        print(f"    - Win Rate             : {(ret_sell_gross > 0).mean()*100:.2f} %")
        
    print("=" * 80)


if __name__ == "__main__":
    evaluate_council_on_parquet("data/market_data/xauusd.parquet", "frxXAUUSD", cost_bps=1.859, horizon=5)
    evaluate_council_on_parquet("data/market_data/crash1000.parquet", "CRASH1000", cost_bps=0.745, horizon=5)
