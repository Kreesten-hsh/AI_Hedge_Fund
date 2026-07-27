import pytest
from datetime import datetime, timezone

from aegis_trade.domain.core import Symbol, TimeFrame, AssetClass
from aegis_trade.domain.features import FeatureSet
from aegis_trade.providers.qlib.dataset_builder import DatasetBuilder
from aegis_trade.providers.qlib.model_factory import ModelFactory
from aegis_trade.providers.qlib.trainer import QlibTrainer
from aegis_trade.providers.qlib.predictor import QlibPredictor
from aegis_trade.application.strategy.ml_strategy import MLStrategy

def test_qlib_adapter_pipeline():
    # 1. Dataset Builder
    builder = DatasetBuilder(target_feature="returns")
    features = [
        FeatureSet(
            symbol=Symbol("BTC", AssetClass.CRYPTO),
            timeframe=TimeFrame.H1,
            timestamp=datetime.now(timezone.utc),
            features={"returns": 0.05, "volatility": 0.01}
        )
    ]
    dataset = builder.build_from_features(features)
    assert len(dataset) == 1
    assert "volatility" in dataset.raw_data[0]
    
    # 2. Model Factory & Trainer
    model = ModelFactory.create_model("lightgbm", max_depth=5)
    trainer = QlibTrainer()
    train_result = trainer.train(model, dataset)
    assert train_result["status"] == "success"
    
    # 3. Predictor & Strategy
    predictor = QlibPredictor(model)
    strategy = MLStrategy(predictor=predictor, buy_threshold=0.5, sell_threshold=0.4)
    
    signals = strategy.generate_signals(features[0])
    
    # 4. Assertions on Signal
    # Our mock LightGBM returns 0.55, which is > buy_threshold (0.5), so it should BUY
    assert len(signals) == 1
    assert signals[0].direction == 1
    assert signals[0].symbol == Symbol("BTC", AssetClass.CRYPTO)
