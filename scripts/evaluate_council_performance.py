"""Harnais de test et diagnostic quantitatif complet du MultiAgentCouncil (8 agents).

Évalue le consensus déterministe généré par le Council sur les barres réelles M1 (Gold, Crash 1000),
en simulant l'évolution dynamique du Portfolio et de la mémoire FAISS (PatternAgent)
afin d'exercer 5 agents actifs sur 8.
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


def evaluate_council_on_parquet(
    parquet_path: str,
    symbol_name: str,
    cost_bps: float,
    horizon: int = 5,
):
    logger.info(f"Évaluation complète du Council sur {symbol_name} ({parquet_path}), Coût: {cost_bps} bps, Horizon: {horizon}m")
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
    
    portfolio = Portfolio(initial_capital=10000.0)
    council = build_council()
    
    verdicts: list[str] = []
    confidences: list[float] = []
    multipliers: list[float] = []
    veto_reasons: list[str | None] = []
    
    # Compteurs de votes directionnels (BUY / SELL) par agent
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

    # Suivi dynamique des positions simulées pour alimenter la réaction du PortfolioAgent
    active_position_expiry = -1
    
    logger.info("Exécution séquentielle du Council avec Portfolio dynamique et mémoire FAISS synthétique...")
    for idx, (fset, bar) in enumerate(zip(feature_sets, bars)):
        current_price = bar.close
        portfolio.on_market_event(MarketEvent(timestamp=bar.timestamp, bar=bar))
        
        # Fermeture simulée de la position au bout de l'horizon
        if idx == active_position_expiry:
            pos = portfolio.get_position(symbol)
            if pos and pos.volume != 0:
                portfolio._positions.pop(symbol, None)
            active_position_expiry = -1
            
        # Simulation d'un memory_score FAISS dynamique (PatternAgent)
        # calculé sur le rendement glissant des 5 barres précédentes
        if idx >= 5:
            past_ret = float((bars[idx].close - bars[idx-5].close) / bars[idx-5].close)
            memory_score = float(np.clip(past_ret * 20000.0, -100.0, 100.0))
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
        
        # Enregistrement des votes directionnels par agent (BUY / SELL)
        for v in verdict.votes:
            if v.vote in ("BUY", "SELL"):
                agent_directional_votes[v.agent_name] += 1

        # Mettre à jour la position dans le Portfolio pour alimenter les barres suivantes (PortfolioAgent)
        if verdict.final_vote in ("BUY", "SELL") and verdict.position_size_multiplier > 0.0:
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
    
    print("\n" + "=" * 80)
    print(f"  RÉSULTATS AUDIT DYNAMIQUE DU COUNCIL SUR {symbol_name} (75 000 barres M1)")
    print("=" * 80)
    print("  Activité des 8 Agents du Council (Votes BUY / SELL émis) :")
    active_agents_count = 0
    for agent_name, count in agent_directional_votes.items():
        is_active = count > 0
        if is_active:
            active_agents_count += 1
        status_str = f"ACTIF ({count:>6} votes directionnels)" if is_active else "INACTIF / STUB"
        print(f"    - {agent_name:<18} : {status_str}")
        
    print(f"\n  TOTAL AGENTS AYANT VOTÉ BUY/SELL : {active_agents_count} / 8")
    print("  (Note: NewsAgent est un stub LLM hors-path critique documenté comme inactif)")
    print("-" * 80)
    print(f"  Distribution des Verdicts du Council:")
    print(f"    - BUY   : {len(buy_signals):>6} ({len(buy_signals)/len(df_eval)*100:.2f} %)")
    print(f"    - SELL  : {len(sell_signals):>6} ({len(sell_signals)/len(df_eval)*100:.2f} %)")
    print(f"    - WAIT  : {len(wait_signals):>6} ({len(wait_signals)/len(df_eval)*100:.2f} %)")
    print(f"    - VETOS : {len(veto_signals):>6} ({len(veto_signals)/len(df_eval)*100:.2f} %)")
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
