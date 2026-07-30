import logging
import os
import sys
import psutil
import time
import pandas as pd
import numpy as np

# Adjust python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from aegis_trade.providers.kronos.model_factory import KronosModelFactory
from aegis_trade.providers.kronos.dataset_builder import KronosDatasetBuilder
from aegis_trade.providers.kronos.trainer import KronosFineTuner

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def get_memory_usage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # in MB

def generate_dummy_data(rows=5000):
    # generate random walk for price
    np.random.seed(42)
    returns = np.random.normal(0, 0.001, rows)
    close = 1000 * np.exp(np.cumsum(returns))
    open_p = close * np.random.normal(1, 0.001, rows)
    high = np.maximum(open_p, close) * np.random.normal(1.001, 0.001, rows)
    low = np.minimum(open_p, close) * np.random.normal(0.999, 0.001, rows)
    volume = np.random.lognormal(10, 1, rows)
    amount = volume * close
    
    # Generate random timestamps
    timestamps = pd.date_range(start='2020-01-01', periods=rows, freq='1min')
    
    return pd.DataFrame({
        'open': open_p,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
        'amount': amount,
        'datetime': timestamps
    })

def main():
    logging.info("Starting true Kronos-mini smoke test (Gold, 1 epoch)")
    
    mem_start = get_memory_usage()
    logging.info(f"Initial Memory Usage: {mem_start:.2f} MB")
    
    # 1. Load model
    factory = KronosModelFactory()
    predictor = factory.get_predictor()
    
    if predictor is None:
        logging.error("Failed to load true Kronos model.")
        return
        
    mem_after_load = get_memory_usage()
    logging.info(f"Memory after loading model: {mem_after_load:.2f} MB (Delta: {mem_after_load - mem_start:.2f} MB)")
    
    # 2. Prepare Data
    # For a smoke test on a CPU, let's keep the row count small, e.g. 1000 rows
    logging.info("Generating dummy data for GOLD...")
    df_gold = generate_dummy_data(1000)
    
    builder = KronosDatasetBuilder(lookback_window=90, predict_window=10)
    train_data, val_data = builder.prepare_datasets({"GOLD": df_gold})
    
    logging.info(f"Generated {len(train_data)} train samples and {len(val_data)} val samples.")
    
    mem_after_data = get_memory_usage()
    logging.info(f"Memory after data prep: {mem_after_data:.2f} MB")
    
    # 3. Fine-tune
    trainer = KronosFineTuner(tokenizer=predictor.tokenizer, model=predictor.model, output_dir="./models/kronos_smoke")
    
    start_time = time.time()
    metrics = trainer.train(train_data, val_data, epochs=1)
    end_time = time.time()
    
    mem_end = get_memory_usage()
    
    logging.info("=== SMOKE TEST RESULTS ===")
    logging.info(f"Epoch time: {end_time - start_time:.2f} seconds")
    logging.info(f"Final Memory Usage: {mem_end:.2f} MB")
    logging.info(f"Peak Delta (End - Start): {mem_end - mem_start:.2f} MB")
    logging.info(f"Metrics: {metrics}")

if __name__ == "__main__":
    main()
