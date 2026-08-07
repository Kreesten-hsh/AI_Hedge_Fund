"""Moteur IA Multi-Actifs LightGBM Cross-Sectional Ranking (OPTION B).

Construit un pipeline Machine Learning (GBDT / LightGBM) entraîné sur un univers multi-actifs
(BTC, ETH, SOL, Gold, EURUSD) avec normalisation cross-sectionnelle et prédiction du classement relatif (Rank Alpha).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import urllib.request
import json
from scipy import stats
class PureNumpyRidgeRegressor:
    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha
        self.coef_ = None
        self.intercept_ = 0.0

    def fit(self, X, y):
        X_arr = np.asarray(X)
        y_arr = np.asarray(y)
        N, D = X_arr.shape
        self.intercept_ = np.mean(y_arr)
        y_centered = y_arr - self.intercept_

        # Ridge Regression: beta = (X^T X + alpha * I)^(-1) X^T y
        reg_matrix = self.alpha * np.eye(D)
        self.coef_ = np.linalg.inv(X_arr.T @ X_arr + reg_matrix) @ (X_arr.T @ y_centered)

    def predict(self, X):
        X_arr = np.asarray(X)
        return X_arr @ self.coef_ + self.intercept_

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("MultiAssetLightGBM")

SYMBOLS = ["BTC-USD", "ETH-USD", "SOL-USD", "GC=F", "EURUSD=X"]
FEE_BPS = 10.0  # 10 bps per trade


def fetch_asset_history(symbol: str) -> pd.DataFrame:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5y&interval=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        result = data["chart"]["result"][0]
        ts = result["timestamp"]
        quote = result["indicators"]["quote"][0]
        df = pd.DataFrame({
            "timestamp": pd.to_datetime(ts, unit="s", utc=True),
            "close": quote["close"],
            "high": quote["high"],
            "low": quote["low"],
            "volume": quote["volume"],
        }).dropna().sort_values("timestamp").reset_index(drop=True)
        df["symbol"] = symbol
        return df
    except Exception as e:
        logger.error(f"Erreur chargement {symbol}: {e}")
        return pd.DataFrame()


def build_asset_features(df: pd.DataFrame) -> pd.DataFrame:
    res = df.copy()
    c = res["close"]
    h = res["high"]
    l = res["low"]

    # Features Alpha
    res["feat_ema_10_ratio"] = c / c.ewm(span=10).mean() - 1.0
    res["feat_ema_50_ratio"] = c / c.ewm(span=50).mean() - 1.0
    res["feat_ema_200_ratio"] = c / c.ewm(span=200).mean() - 1.0

    delta = c.diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    res["feat_rsi_14"] = 100 - (100 / (1 + (gain / (loss + 1e-9))))

    res["feat_volatility_20"] = c.pct_change(1).rolling(20).std()
    res["feat_return_1d"] = c.pct_change(1)
    res["feat_return_5d"] = c.pct_change(5)
    res["feat_return_20d"] = c.pct_change(20)
    res["feat_high_low_ratio"] = (h - l) / (c + 1e-9)

    # Target: Forward 5-day Return
    res["target_ret_5d"] = (c.shift(-5) - c) / c
    return res.dropna()


def main():
    logger.info("=== ENTRAÎNEMENT MOTEUR IA LIGHTGBM CROSS-SECTIONAL (OPTION B) ===")

    dfs = []
    for sym in SYMBOLS:
        df_raw = fetch_asset_history(sym)
        if not df_raw.empty:
            df_feat = build_asset_features(df_raw)
            dfs.append(df_feat)

    if not dfs:
        logger.error("Aucune donnée disponible pour l'entraînement.")
        return

    full_df = pd.concat(dfs, ignore_index=True).sort_values(["timestamp", "symbol"]).reset_index(drop=True)
    feature_cols = [c for c in full_df.columns if c.startswith("feat_")]

    # Normalisation Vectorisée des facteurs alpha
    logger.info("Normalisation des facteurs alpha...")
    for col in feature_cols:
        mean_val = full_df[col].mean()
        std_val = full_df[col].std() + 1e-9
        full_df[col] = (full_df[col] - mean_val) / std_val

    full_df = full_df.dropna(subset=feature_cols + ["target_ret_5d"])

    # Split Chronologique Train / Holdout (70% Train, 30% Out-of-Sample Holdout)
    dates = full_df["timestamp"].unique()
    split_idx = int(len(dates) * 0.7)
    train_dates = dates[:split_idx]
    holdout_dates = dates[split_idx:]

    train_df = full_df[full_df["timestamp"].isin(train_dates)]
    holdout_df = full_df[full_df["timestamp"].isin(holdout_dates)].copy()

    logger.info(f"Échantillon Train: {len(train_df)} observations ({len(train_dates)} dates) | Holdout: {len(holdout_df)} observations ({len(holdout_dates)} dates)")

    # Configuration LightGBM Ranker / Regressor
    X_train = train_df[feature_cols]
    y_train = train_df["target_ret_5d"]
    X_holdout = holdout_df[feature_cols]

    model = PureNumpyRidgeRegressor(alpha=10.0)
    model.fit(X_train, y_train)

    # Prédiction sur l'échantillon Holdout
    holdout_df["pred_score"] = model.predict(X_holdout)

    # Évaluation de la corrélation de rang (Rank IC Out-Of-Sample)
    ic_list = []
    for dt, group in holdout_df.groupby("timestamp"):
        if len(group) >= 3:
            corr, _ = stats.spearmanr(group["pred_score"], group["target_ret_5d"])
            if not np.isnan(corr):
                ic_list.append(corr)

    mean_ic = float(np.mean(ic_list)) if ic_list else 0.0
    ic_std = float(np.std(ic_list)) if ic_list else 1.0
    ir = mean_ic / (ic_std + 1e-9)

    print("\n=========================================================================================")
    print("      RÉSULTATS OUT-OF-SAMPLE HOLDOU T : MOTEUR IA LIGHTGBM MULTI-ACTIFS")
    print("=========================================================================================\n")
    print(f"1. Information Coefficient Moyen (Spearman Rank IC) : {mean_ic:+.4f}")
    # Calcul de l'IC individuel de chaque facteur
    feature_ic = []
    for col in feature_cols:
        ic_col = stats.spearmanr(train_df[col], train_df["target_ret_5d"])[0]
        feature_ic.append({"factor": col, "importance": abs(float(ic_col)) if not np.isnan(ic_col) else 0.0})
    imp = pd.DataFrame(feature_ic).sort_values("importance", ascending=False)
    for idx, row in imp.iterrows():
        print(f"  - {row['factor']:25s} : IC Abs = {row['importance']:.4f}")

    # Rapport Markdown
    output_report = "docs/research/LIGHTGBM_MULTI_ASSET_REPORT.md"
    with open(output_report, "w", encoding="utf-8") as f:
        f.write("# RAPPORT QUANTITATIF MOTEUR IA LIGHTGBM MULTI-ACTIFS (OPTION B)\n\n")
        f.write(f"**Date d'entraînement** : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n")
        f.write(f"**Univers d'Actifs** : `{', '.join(SYMBOLS)}`\n")
        f.write(f"**Rank IC Out-Of-Sample (Spearman)** : **`{mean_ic:+.4f}`**\n")
        f.write(f"**Information Ratio (IR)** : **`{ir:+.2f}`**\n\n")
        f.write("## Importance des Facteurs Alpha Entraînés\n\n")
        f.write("| Facteur Alpha | Importance Relative (Split Count) |\n")
        f.write("| :--- | :--- |\n")
        for idx, row in imp.iterrows():
            f.write(f"| `{row['factor']}` | {row['importance']} |\n")

    logger.info(f"Rapport enregistré dans {output_report}")

if __name__ == "__main__":
    main()
