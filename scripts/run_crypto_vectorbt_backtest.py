"""Script d'évaluation vectorisée (VectorBT-like) de la stratégie AegisCryptoTrendStrategy.

Exécute un backtest multi-actifs Crypto (BTC-USD, ETH-USD, SOL-USD) sur 2 ans d'historique
avec prise en compte stricte des frais de courtage (10 bps A/R).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import urllib.request
import json

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("CryptoVectorBTBacktest")

FEE_ROUND_TRIP_BPS = 10.0   # 0.10% (Frais standards Binance / Bybit Spot/Futures)
COST_FACTOR = FEE_ROUND_TRIP_BPS / 10000.0


def fetch_crypto_history(symbol: str, range_str: str = "2y") -> pd.DataFrame:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={range_str}&interval=1h"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        result = data["chart"]["result"][0]
        ts = result["timestamp"]
        quote = result["indicators"]["quote"][0]
        df = pd.DataFrame({
            "timestamp": pd.to_datetime(ts, unit="s", utc=True),
            "open": quote["open"],
            "high": quote["high"],
            "low": quote["low"],
            "close": quote["close"],
            "volume": quote["volume"],
        }).dropna().sort_values("timestamp").reset_index(drop=True)
        return df
    except Exception as e:
        logger.error(f"Erreur téléchargement Crypto {symbol}: {e}")
        return pd.DataFrame()


def run_trend_backtest_on_df(df: pd.DataFrame, symbol: str) -> dict:
    res = df.copy()
    close = res["close"]
    high = res["high"]
    low = res["low"]

    # Moyennes Mobiles
    ema_20 = close.ewm(span=20).mean()
    ema_50 = close.ewm(span=50).mean()
    ema_200 = close.ewm(span=200).mean()

    # Bollinger Bands
    ma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    bb_upper = ma20 + (2.0 * std20)

    # RSI
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi = 100 - (100 / (1 + (gain / (loss + 1e-9))))

    # Conditions d'entrée Long
    signal_entry = (close > ema_50) & (ema_50 > ema_200) & (rsi > 50) & (rsi < 70) & (close > bb_upper.shift(1))
    signal_exit = (close < ema_20) | (rsi < 40)

    position = 0
    trades = []
    entry_price = 0.0
    entry_idx = 0

    close_arr = close.values
    ts_arr = res["timestamp"].values
    entry_arr = signal_entry.values
    exit_arr = signal_exit.values

    for i in range(1, len(res)):
        if position == 0:
            if entry_arr[i-1]:  # Exécution au close de confirmation
                position = 1
                entry_price = close_arr[i]
                entry_idx = i
        elif position == 1:
            # Check Stop-loss 2.5%
            drawdown = (close_arr[i] - entry_price) / entry_price
            if drawdown <= -0.025 or exit_arr[i-1]:
                exit_price = close_arr[i]
                raw_return = (exit_price - entry_price) / entry_price
                net_return = raw_return - COST_FACTOR
                holding_bars = i - entry_idx
                trades.append({
                    "entry_time": ts_arr[entry_idx],
                    "exit_time": ts_arr[i],
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "net_return": net_return,
                    "holding_bars": holding_bars,
                })
                position = 0

    if not trades:
        return {"symbol": symbol, "total_trades": 0, "net_pnl_pct": 0.0, "win_rate": 0.0, "sharpe": 0.0, "max_drawdown": 0.0}

    df_trades = pd.DataFrame(trades)
    net_returns = df_trades["net_return"].values

    total_trades = len(trades)
    win_rate = float(np.mean(net_returns > 0)) * 100.0
    cumulative_return = float(np.prod(1.0 + net_returns) - 1.0) * 100.0

    # Curve d'équité
    equity = np.cumprod(1.0 + net_returns)
    peak = np.maximum.accumulate(equity)
    drawdown = (equity - peak) / peak
    max_dd = float(np.min(drawdown)) * 100.0

    mean_ret = np.mean(net_returns)
    std_ret = np.std(net_returns) + 1e-9
    sharpe = float((mean_ret / std_ret) * np.sqrt(365 * 24 / df_trades["holding_bars"].mean()))

    return {
        "symbol": symbol,
        "total_trades": total_trades,
        "net_pnl_pct": cumulative_return,
        "win_rate": win_rate,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
    }


def main():
    logger.info("=== BACKTEST VECTORISÉ STRATÉGIE CRYPTO FREQTRADE / VECTORBT ===")
    symbols = ["BTC-USD", "ETH-USD", "SOL-USD"]
    results = []

    for sym in symbols:
        df = fetch_crypto_history(sym, "2y")
        if not df.empty:
            res = run_trend_backtest_on_df(df, sym)
            results.append(res)
            logger.info(f"[{sym}] Trades: {res['total_trades']} | PnL Net: {res['net_pnl_pct']:+.2f}% | Win Rate: {res['win_rate']:.1f}% | Sharpe: {res['sharpe']:.2f} | MaxDD: {res['max_drawdown']:.2f}%")

    print("\n=========================================================================================")
    print("      SYNTHÈSE DU BACKTEST VECTORISÉ CRYPTO 24/7 (FRAIS 10 BPS DÉDUITS)")
    print("=========================================================================================\n")
    print("| Symbol | Total Trades | P&L Net Cumulé | Win Rate (%) | Ratio Sharpe | Max Drawdown (%) |")
    print("| :--- | :--- | :--- | :--- | :--- | :--- |")
    for r in results:
        print(f"| {r['symbol']:8s} | {r['total_trades']:12d} | **{r['net_pnl_pct']:+9.2f}%** | {r['win_rate']:10.1f}% | {r['sharpe']:12.2f} | **{r['max_drawdown']:14.2f}%** |")

if __name__ == "__main__":
    main()
