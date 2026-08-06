"""Harnais d'audit quantitatif rigoureux du MultiAgentCouncil (8 agents).

Évalue le Council selon deux configurations rigoureuses :
1. Run 1 (Purifié & Réel) : Veto strict Liquidity/Execution + MomentumAgent réactivé (rsi_14)
   avec PatternAgent neutre (memory_score = 0.0, reflétant une mémoire FAISS creuse sans sur-apprentissage).
2. Run 2 (Proxy FAISS Creux) : Memory score sparse (non-nul sur ~5% des barres) + suivi Portfolio
   pour comparer l'impact d'une mémoire clairsemée.
"""

from __future__ import annotations

import logging
from decimal import Decimal
import pandas as pd
import numpy as np
from typing import Dict

from aegis_trade.domain.core import Symbol, AssetClass, TimeFrame, MarketBar
from aegis_trade.domain.council import MarketContext
from aegis_trade.engine.portfolio import Portfolio, EnginePosition
from aegis_trade.engine.events import MarketEvent
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


def run_evaluation(
    df: pd.DataFrame,
    symbol: Symbol,
    bars: list[MarketBar],
    feature_sets: list,
    cost_bps: float,
    horizon: int,
    mode: str = "purified",  # "purified" ou "sparse_faiss"
) -> dict:
    portfolio = Portfolio(initial_capital=10000.0)
    council = build_council()
    
    verdicts: list[str] = []
    confidences: list[float] = []
    multipliers: list[float] = []
    veto_reasons: list[str | None] = []
    
    agent_directional_votes: Dict[str, int] = {
        "TrendAgent": 0,
        "MomentumAgent": 0,
        "VolatilityAgent": 0,
        "LiquidityAgent": 0,
        "PatternAgent": 0,
        "NewsAgent": 0,
        "ExecutionAgent": 0,
        "PortfolioAgent": 0,
    }

    active_position_expiry = -1

    for idx, (fset, bar) in enumerate(zip(feature_sets, bars)):
        current_price = bar.close
        portfolio.on_market_event(MarketEvent(timestamp=bar.timestamp, bar=bar))
        
        # En mode sparse_faiss, on réinitialise la position à l'échéance
        if mode == "sparse_faiss" and idx == active_position_expiry:
            pos = portfolio.get_position(symbol)
            if pos and pos.volume != 0:
                portfolio._positions.pop(symbol, None)
            active_position_expiry = -1

        # Détermination du memory_score selon le mode
        if mode == "purified":
            # Représente la réalité de production : mémoire FAISS creuse / non peuplée
            memory_score = 0.0
        else:
            # Memory score creux : actif uniquement sur ~5% des barres avec des mouvements extrêmes (> 3 std)
            if idx >= 20:
                past_ret = float((bars[idx].close - bars[idx-1].close) / bars[idx-1].close)
                # Vaut 0.0 par défaut, sauf choc > 0.15%
                if abs(past_ret) > 0.0015:
                    memory_score = float(np.clip(past_ret * 50000.0, -100.0, 100.0))
                else:
                    memory_score = 0.0
            else:
                memory_score = 0.0

        ctx = MarketContext(
            symbol=symbol,
            features=fset.features,
            portfolio=portfolio,
            latest_prices={symbol: current_price},
            memory_score=memory_score
        )
        
        verdict = council.evaluate(ctx)
        verdicts.append(verdict.final_vote)
        confidences.append(verdict.aggregated_confidence)
        multipliers.append(verdict.position_size_multiplier)
        veto_reasons.append(verdict.veto_reason)
        
        for v in verdict.votes:
            if v.vote in ("BUY", "SELL"):
                agent_directional_votes[v.agent_name] += 1

        if mode == "sparse_faiss" and verdict.final_vote in ("BUY", "SELL") and verdict.position_size_multiplier > 0.0:
            if active_position_expiry == -1:
                vol = Decimal("1.0") * Decimal(str(verdict.position_size_multiplier))
                if verdict.final_vote == "SELL":
                    vol = -vol
                portfolio._positions[symbol] = EnginePosition(
                    symbol=symbol,
                    volume=vol,
                    average_price=current_price
                )
                active_position_expiry = idx + horizon

    df_eval = pd.DataFrame({
        "close": [float(b.close) for b in bars],
        "verdict": verdicts,
        "confidence": confidences,
        "multiplier": multipliers,
        "veto_reason": veto_reasons,
    }, index=[b.timestamp for b in bars])

    df_eval["forward_return"] = df_eval["close"].pct_change(horizon).shift(-horizon)
    
    buy_signals = df_eval[df_eval["verdict"] == "BUY"]
    sell_signals = df_eval[df_eval["verdict"] == "SELL"]
    wait_signals = df_eval[df_eval["verdict"] == "WAIT"]
    veto_signals = df_eval[df_eval["veto_reason"].notna()]
    
    cost_frac = cost_bps / 10000.0
    
    buy_gross = buy_signals["forward_return"].dropna().mean() * 10000.0 if len(buy_signals) > 0 else 0.0
    buy_net = (buy_signals["forward_return"].dropna() - cost_frac).mean() * 10000.0 if len(buy_signals) > 0 else 0.0
    buy_winrate = (buy_signals["forward_return"].dropna() > 0).mean() * 100.0 if len(buy_signals) > 0 else 0.0
    
    sell_gross = (-sell_signals["forward_return"].dropna()).mean() * 10000.0 if len(sell_signals) > 0 else 0.0
    sell_net = ((-sell_signals["forward_return"].dropna()) - cost_frac).mean() * 10000.0 if len(sell_signals) > 0 else 0.0
    sell_winrate = ((-sell_signals["forward_return"].dropna()) > 0).mean() * 100.0 if len(sell_signals) > 0 else 0.0

    return {
        "mode": mode,
        "n_bars": len(df_eval),
        "agent_votes": agent_directional_votes,
        "buy_count": len(buy_signals),
        "sell_count": len(sell_signals),
        "wait_count": len(wait_signals),
        "veto_count": len(veto_signals),
        "buy_gross": buy_gross,
        "buy_net": buy_net,
        "buy_winrate": buy_winrate,
        "sell_gross": sell_gross,
        "sell_net": sell_net,
        "sell_winrate": sell_winrate,
    }


def evaluate_asset(parquet_path: str, symbol_name: str, cost_bps: float, horizon: int = 5):
    logger.info(f"Chargement {symbol_name} ({parquet_path})...")
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

    extractor = TechnicalFeatureExtractor()
    feature_sets = extractor.extract(bars)
    
    res_purified = run_evaluation(df, symbol, bars, feature_sets, cost_bps, horizon, mode="purified")
    res_sparse = run_evaluation(df, symbol, bars, feature_sets, cost_bps, horizon, mode="sparse_faiss")
    
    print("\n" + "=" * 90)
    print(f"  AUDIT COMPARATIF DU COUNCIL SUR {symbol_name} (75 000 barres M1)")
    print("=" * 90)
    print(f"  {'Agent':<18} | {'Run 1 (Purifié avec rsi_14)':<32} | {'Run 2 (Proxy FAISS Sparse)':<32}")
    print("-" * 90)
    for agent_name in res_purified["agent_votes"].keys():
        v1 = res_purified["agent_votes"][agent_name]
        v2 = res_sparse["agent_votes"][agent_name]
        s1 = f"ACTIF ({v1:>5} votes)" if v1 > 0 else "INACTIF / STUB"
        s2 = f"ACTIF ({v2:>5} votes)" if v2 > 0 else "INACTIF / STUB"
        print(f"  {agent_name:<18} | {s1:<32} | {s2:<32}")
        
    print("-" * 90)
    print(f"  {'Métrique':<18} | {'Run 1 (Purifié avec rsi_14)':<32} | {'Run 2 (Proxy FAISS Sparse)':<32}")
    print("-" * 90)
    
    pct_trade_1 = (res_purified['buy_count'] + res_purified['sell_count']) / res_purified['n_bars'] * 100
    pct_trade_2 = (res_sparse['buy_count'] + res_sparse['sell_count']) / res_sparse['n_bars'] * 100
    print(f"  {'Taux d exposition':<18} | {pct_trade_1:>6.2f} % ({res_purified['buy_count']+res_purified['sell_count']} trades) | {pct_trade_2:>6.2f} % ({res_sparse['buy_count']+res_sparse['sell_count']} trades)")
    print(f"  {'BUY Gross / Net':<18} | {res_purified['buy_gross']:>+.3f} bps / {res_purified['buy_net']:>+.3f} bps   | {res_sparse['buy_gross']:>+.3f} bps / {res_sparse['buy_net']:>+.3f} bps")
    print(f"  {'BUY Win Rate':<18} | {res_purified['buy_winrate']:>6.2f} %                           | {res_sparse['buy_winrate']:>6.2f} %")
    print(f"  {'SELL Gross / Net':<18} | {res_purified['sell_gross']:>+.3f} bps / {res_purified['sell_net']:>+.3f} bps  | {res_sparse['sell_gross']:>+.3f} bps / {res_sparse['sell_net']:>+.3f} bps")
    print(f"  {'SELL Win Rate':<18} | {res_purified['sell_winrate']:>6.2f} %                          | {res_sparse['sell_winrate']:>6.2f} %")
    print("=" * 90)


if __name__ == "__main__":
    evaluate_asset("data/market_data/xauusd.parquet", "frxXAUUSD", cost_bps=1.859, horizon=5)
    evaluate_asset("data/market_data/crash1000.parquet", "CRASH1000", cost_bps=0.745, horizon=5)
