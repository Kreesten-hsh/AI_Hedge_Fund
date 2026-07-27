import os
import sys
import logging
from datetime import datetime, timezone

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from aegis_trade.domain.core import Symbol, AssetClass, TimeFrame
from aegis_trade.domain.research import ResearchMetadata
from aegis_trade.infrastructure.features.feature_store import FeatureStore
from aegis_trade.infrastructure.research.research_engine import ResearchEngine
from aegis_trade.infrastructure.research.research_report import ResearchReport

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("RunAlphaResearch")

def main():
    """
    Executes the Alpha Research process:
    1. Loads features from the Local Data Lake (Feature Store)
    2. Runs the Research Engine to compute IC, IR, and Stability
    3. Generates the JSON Report
    """
    logger.info("Starting Alpha Research Evaluation")
    
    # 1. Setup
    symbol = Symbol("BTCUSD", AssetClass.CRYPTO)
    timeframe = TimeFrame.D1
    store = FeatureStore()
    
    # 2. Load Features
    logger.info(f"Loading features for {symbol.name} {timeframe.value}...")
    features = store.load_features(symbol, timeframe)
    
    if not features:
        logger.error(f"No features found in the Feature Store for {symbol.name}. Run FE-01 first.")
        return
        
    logger.info(f"Loaded {len(features)} periods.")
    
    start_time = features[0].timestamp
    end_time = features[-1].timestamp
    
    # 3. Setup Metadata
    metadata = ResearchMetadata(
        symbol=symbol,
        timeframe=timeframe,
        start_time=start_time,
        end_time=end_time,
        forward_returns_lag=1
    )
    
    # 4. Evaluate
    engine = ResearchEngine()
    logger.info("Running Research Engine (Information Coefficient, IR, Stability)...")
    result = engine.evaluate(features, metadata)
    
    # 5. Report
    report_path = os.path.join(
        os.path.dirname(__file__), '..', 'data', 'reports', 
        f'alpha_research_{symbol.name}_{metadata.computation_timestamp.strftime("%Y%m%d_%H%M%S")}.json'
    )
    
    json_output = ResearchReport.generate_json(result, filepath=report_path)
    
    # Print summary
    logger.info("Evaluation Complete.")
    logger.info(f"Top 5 Features by Final Score (IR * Stability):")
    for feat in result.top_features[:5]:
        score = result.feature_scores[feat]
        logger.info(f" - {feat}: IC Mean = {score.ic_mean:.4f}, IR = {score.ic_information_ratio:.4f}, Stability = {score.stability:.2f}, Score = {score.final_score:.4f}")
        
    logger.info(f"Full JSON report saved to: {report_path}")

if __name__ == "__main__":
    main()
