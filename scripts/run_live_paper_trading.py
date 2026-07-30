#!/usr/bin/env python3
import asyncio
import os
import logging
import sys
from aegis_trade.infrastructure.paper.deriv_gateway import DerivGateway
from aegis_trade.application.paper_trading.orchestrator import PaperTradingOrchestrator
from aegis_trade.engine.global_risk import GlobalRiskManager
from aegis_trade.engine.portfolio import Portfolio
from aegis_trade.application.council.aggregator import VoteAggregator
from aegis_trade.application.council.resolver import ConflictResolver
from aegis_trade.application.council.council import MultiAgentCouncil
from aegis_trade.infrastructure.rl.policy_checkpoint_store import PolicyCheckpointStore
from decimal import Decimal

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("run_live_paper_trading")

async def main():
    logger.info("Initializing Live Paper Trading Runner (Demo Environment)...")
    
    # 1. Environment and Config
    # We enforce non-PROD to ensure we are using Deriv demo account
    if os.environ.get("AEGIS_ENV", "").upper() == "PROD":
        logger.error("Cannot run paper trading in PROD environment.")
        sys.exit(1)
        
    deriv_token = os.environ.get("DERIV_DEMO_TOKEN")
    if not deriv_token:
        logger.error("DERIV_DEMO_TOKEN is not set in environment.")
        sys.exit(1)
        
    # 2. Infrastructure Initialization
    gateway = DerivGateway(token=deriv_token)
    connected = await gateway.connect()
    if not connected:
        logger.error("Failed to connect to DerivGateway.")
        sys.exit(1)
        
    policy_store = PolicyCheckpointStore(storage_dir="data/rl/checkpoints")
    risk_manager = GlobalRiskManager(max_drawdown=Decimal("0.05"))
    portfolio = Portfolio(initial_capital=Decimal("1000.0"))
    
    council = MultiAgentCouncil(
        aggregator=VoteAggregator(),
        resolver=ConflictResolver()
    )
    
    orchestrator = PaperTradingOrchestrator(
        broker=gateway,
        risk_manager=risk_manager,
        portfolio=portfolio,
        council=council,
        policy_store=policy_store
    )
    
    # 3. Main Loop
    logger.info("Starting PaperTradingOrchestrator loop. Waiting for market ticks...")
    logger.info("Target: 200 trades AND 2 weeks duration.")
    
    # In a real setup, this loop would listen to a WebSocket feed for market ticks
    # and call orchestrator.process_signal() whenever a new state/signal arrives.
    try:
        while True:
            # Placeholder for WebSocket receive loop
            # signal = await websocket.recv()
            # await orchestrator.process_signal(signal)
            await asyncio.sleep(1) # Keep alive
    except KeyboardInterrupt:
        logger.info("Live Paper Trading interrupted by user.")
    except Exception as e:
        logger.error(f"Live Paper Trading error: {e}")
        
    logger.info("Live Paper Trading Runner stopped.")

if __name__ == "__main__":
    asyncio.run(main())
