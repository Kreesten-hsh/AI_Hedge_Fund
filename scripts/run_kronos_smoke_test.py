import logging
import os
import sys
import psutil
import time
import pandas as pd
import numpy as np
import torch

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
    price = 1000 * np.exp(np.cumsum(returns))
    return pd.DataFrame({'close': price})

def main():
    logging.info("Starting Kronos-mini smoke test (Gold, 1 epoch)")
    
    mem_start = get_memory_usage()
    logging.info(f"Initial Memory Usage: {mem_start:.2f} MB")
    
    # 1. Load model
    factory = KronosModelFactory()
    pipeline = factory.get_pipeline()
    
    if pipeline is None:
        logging.error("Failed to load Kronos pipeline. Make sure chronos is installed.")
        return
        
    mem_after_load = get_memory_usage()
    logging.info(f"Memory after loading model: {mem_after_load:.2f} MB (Delta: {mem_after_load - mem_start:.2f} MB)")
    
    # 2. Prepare Data
    logging.info("Generating dummy data for GOLD (since we don't have local csv)...")
    df_gold = generate_dummy_data(105000)
    
    builder = KronosDatasetBuilder(context_length=2048)
    train_data, val_data = builder.prepare_datasets({"GOLD": df_gold})
    
    logging.info(f"Generated {len(train_data)} train windows and {len(val_data)} val windows.")
    
    mem_after_data = get_memory_usage()
    logging.info(f"Memory after data prep: {mem_after_data:.2f} MB")
    
    # 3. Fine-tune
    trainer = KronosFineTuner(pipeline=pipeline, output_dir="./models/kronos_smoke")
    
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
