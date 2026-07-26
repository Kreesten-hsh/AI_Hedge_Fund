# Scripts
- `ingest_mt5.py`: Connects to MT5 to fetch raw historical OHLCV data.
- `ingest_openbb.py`: Connects to OpenBB SDK to fetch macro and fundamental data.
- `run_engine_backtest.py`: Runs a quick backtest for a single strategy on the Aegis Quant OS engine.
- `run_baselines.py`: Runs baseline benchmark testing over walk-forward windows on multiple assets.
- `generate_features.py`: Example script to run feature engineering pipelines.

Run `python scripts/<script_name>.py` with `PYTHONPATH="src"` set.
