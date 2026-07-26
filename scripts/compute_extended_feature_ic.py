"""
Alpha Research Phase 1 — Extended Feature IC Evaluation

Evaluates 16 features across 5 families on XAUUSD H1 (2 years, ~48 bi-weekly windows).
Same methodology as compute_feature_ic.py: lookback-only, no look-ahead bias, deterministic.

Families:
  1. Volatility:  ATR14/Price, ATR50/ATR14, RollingStd20, RollingStd100
  2. Range:       DistToHigh50, DistToLow50, RangePosition
  3. Momentum:    Return5, Return20, Return100, MomentumAcceleration
  4. Structure:   TrendStrength, ADX14, CompressionRatio
  5. Time:        Hour, Session, DayOfWeek
"""

import os
import sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from aegis_trade.dataset.repository import StorageDatasetRepository
from aegis_trade.dataset.resolver import DatasetResolver


from aegis_trade.utils.math import (
    pearson_ic,
    spearman_rank_ic,
    sliding_ic,
    true_range,
    wilder_smooth,
    compute_atr,
    compute_adx
)


# ---------------------------------------------------------------------------
# Feature extraction — 16 features from lookback bars only
# ---------------------------------------------------------------------------

def extract_extended_features(
    closes: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    timestamps: list,  # list of datetime objects
    macro_data: dict[str, float] = None
) -> dict[str, float]:
    """
    Given lookback arrays (200 bars), compute all 16 features at the final bar.
    Returns NaN for any feature that cannot be computed.
    """
    n = len(closes)
    nan = float("nan")
    result: dict[str, float] = {}

    # --- FAMILY 1: Volatility ---

    # ATR14 / Price
    if n >= 15:
        atr14 = compute_atr(highs, lows, closes, 14)
        atr14_val = atr14[-1]
        result["atr14_norm"] = atr14_val / closes[-1] if closes[-1] > 0 and not np.isnan(atr14_val) else nan
    else:
        result["atr14_norm"] = nan

    # ATR50 / ATR14 (volatility regime)
    if n >= 51:
        atr50 = compute_atr(highs, lows, closes, 50)
        atr50_val = atr50[-1]
        if not np.isnan(atr14_val) and atr14_val > 0 and not np.isnan(atr50_val):
            result["atr_ratio"] = atr50_val / atr14_val
        else:
            result["atr_ratio"] = nan
    else:
        result["atr_ratio"] = nan

    # Rolling Std 20 (of returns)
    if n >= 21:
        rets = np.diff(closes) / closes[:-1]
        result["rstd20"] = float(rets[-20:].std())
    else:
        result["rstd20"] = nan

    # Rolling Std 100
    if n >= 101:
        result["rstd100"] = float(rets[-100:].std())
    else:
        result["rstd100"] = nan

    # --- FAMILY 2: Range ---

    # Distance to highest high over 50 bars (normalized)
    if n >= 50:
        high50 = highs[-50:].max()
        low50 = lows[-50:].min()
        range50 = high50 - low50
        result["dist_high50"] = (high50 - closes[-1]) / closes[-1] if closes[-1] > 0 else nan
        result["dist_low50"] = (closes[-1] - low50) / closes[-1] if closes[-1] > 0 else nan
        # Range position: 0 = at low, 1 = at high
        result["range_pos"] = (closes[-1] - low50) / range50 if range50 > 0 else nan
    else:
        result["dist_high50"] = nan
        result["dist_low50"] = nan
        result["range_pos"] = nan

    # --- FAMILY 3: Momentum ---

    # Return over N bars
    if n >= 6:
        result["ret5"] = (closes[-1] - closes[-6]) / closes[-6]
    else:
        result["ret5"] = nan

    if n >= 21:
        result["ret20"] = (closes[-1] - closes[-21]) / closes[-21]
    else:
        result["ret20"] = nan

    if n >= 101:
        result["ret100"] = (closes[-1] - closes[-101]) / closes[-101]
    else:
        result["ret100"] = nan

    # Momentum Acceleration: ret5 - ret20 (short-term vs medium-term)
    if n >= 21:
        result["mom_accel"] = result["ret5"] - result["ret20"]
    else:
        result["mom_accel"] = nan

    # --- FAMILY 4: Market Structure ---

    # Trend Strength: |close - SMA50| / ATR14 (how far price is from mean, in ATR units)
    if n >= 51 and not np.isnan(result.get("atr14_norm", nan)):
        sma50 = closes[-50:].mean()
        atr14_abs = result["atr14_norm"] * closes[-1]
        result["trend_str"] = abs(closes[-1] - sma50) / atr14_abs if atr14_abs > 0 else nan
    else:
        result["trend_str"] = nan

    # ADX14
    if n >= 30:
        adx = compute_adx(highs, lows, closes, 14)
        adx_val = adx[-1]
        result["adx14"] = adx_val if not np.isnan(adx_val) else nan
    else:
        result["adx14"] = nan

    # Compression Ratio: ATR14 / ATR50 (inverse of atr_ratio — low = compressed)
    if "atr_ratio" in result and not np.isnan(result["atr_ratio"]) and result["atr_ratio"] > 0:
        result["compress"] = 1.0 / result["atr_ratio"]
    else:
        result["compress"] = nan

    # --- FAMILY 5: Time ---

    last_ts = timestamps[-1]
    result["hour"] = float(last_ts.hour)

    # Session: 0=Asia (0-8 UTC), 1=London (8-13 UTC), 2=NY (13-21 UTC), 3=Off-hours
    h = last_ts.hour
    if 0 <= h < 8:
        result["session"] = 0.0
    elif 8 <= h < 13:
        result["session"] = 1.0
    elif 13 <= h < 21:
        result["session"] = 2.0
    else:
        result["session"] = 3.0

    result["dow"] = float(last_ts.weekday())  # 0=Monday ... 4=Friday

    # --- FAMILY 6: Macro ---
    if macro_data:
        result["dxy_mom5"] = macro_data.get("dxy_mom5", nan)
        result["dxy_mom20"] = macro_data.get("dxy_mom20", nan)
        result["us10y_chg"] = macro_data.get("us10y_spread_chg", nan)
        result["macro_corr"] = macro_data.get("macro_regime_corr", nan)
    else:
        result["dxy_mom5"] = nan
        result["dxy_mom20"] = nan
        result["us10y_chg"] = nan
        result["macro_corr"] = nan

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

import argparse

def main():
    parser = argparse.ArgumentParser(description="Evaluate extended feature predictive quality.")
    parser.add_argument("--symbol", type=str, default="XAUUSD", help="Symbol to evaluate")
    parser.add_argument("--timeframe", type=str, default="H1", help="Timeframe (e.g., H1)")
    args = parser.parse_args()

    repo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "datasets")
    repo = StorageDatasetRepository(repo_path)
    resolver = DatasetResolver(repo)

    dataset = resolver.resolve_latest(args.symbol, args.timeframe)
    all_bars = resolver.load_data(dataset)

    # Load Macro Datasets
    try:
        ds_dxy = resolver.resolve_latest("DXY", "D1")
        dxy_bars = resolver.load_data(ds_dxy) if ds_dxy else []
    except Exception:
        dxy_bars = []
        
    try:
        ds_us10y = resolver.resolve_latest("US10Y", "D1")
        us10y_bars = resolver.load_data(ds_us10y) if ds_us10y else []
    except Exception:
        us10y_bars = []

    # Build DataFrame for alignment
    import pandas as pd
    df_xau = pd.DataFrame([
        {"timestamp": b.timestamp, "close": float(b.close), "high": float(b.high), "low": float(b.low)}
        for b in all_bars
    ]).set_index("timestamp")
    
    if dxy_bars:
        df_dxy = pd.DataFrame([{"timestamp": b.timestamp, "dxy_close": float(b.close)} for b in dxy_bars]).set_index("timestamp")
        df_dxy["dxy_mom5"] = df_dxy["dxy_close"].pct_change(5)
        df_dxy["dxy_mom20"] = df_dxy["dxy_close"].pct_change(20)
    else:
        df_dxy = pd.DataFrame(columns=["dxy_close", "dxy_mom5", "dxy_mom20"])
        
    if us10y_bars:
        df_us10y = pd.DataFrame([{"timestamp": b.timestamp, "us10y_close": float(b.close)} for b in us10y_bars]).set_index("timestamp")
        df_us10y["us10y_spread_chg"] = df_us10y["us10y_close"].diff(5)
    else:
        df_us10y = pd.DataFrame(columns=["us10y_close", "us10y_spread_chg"])

    # Outer join to preserve all macro timestamps for proper ffill
    df_merged = df_xau.join(df_dxy, how="outer").join(df_us10y, how="outer")
    
    # Forward-fill macro data
    df_merged["dxy_close"] = df_merged["dxy_close"].ffill()
    df_merged["dxy_mom5"] = df_merged["dxy_mom5"].ffill()
    df_merged["dxy_mom20"] = df_merged["dxy_mom20"].ffill()
    df_merged["us10y_close"] = df_merged["us10y_close"].ffill()
    df_merged["us10y_spread_chg"] = df_merged["us10y_spread_chg"].ffill()
    
    # Restrict back to original XAUUSD hourly index
    df_xau = df_merged.loc[df_xau.index].copy()
    
    # Macro regime: 20-day correlation between XAUUSD returns and DXY returns
    xau_daily = df_xau["close"].resample("D").last()
    xau_daily_ret = xau_daily.pct_change()
    
    dxy_daily = df_dxy["dxy_close"].resample("D").last()
    dxy_daily_ret = dxy_daily.pct_change()
    
    daily_corr = xau_daily_ret.rolling(20).corr(dxy_daily_ret)
    
    # Forward fill the daily correlation back to the hourly dataframe
    df_xau["macro_regime_corr"] = daily_corr.reindex(df_xau.index, method="ffill")

    closes = df_xau["close"].values
    highs = df_xau["high"].values
    lows = df_xau["low"].values
    timestamps = df_xau.index.tolist()
    dxy_mom5_arr = df_xau["dxy_mom5"].values
    dxy_mom20_arr = df_xau["dxy_mom20"].values
    us10y_chg_arr = df_xau["us10y_spread_chg"].values
    macro_corr_arr = df_xau["macro_regime_corr"].values

    total_bars = len(closes)

    print(f"Dataset: {args.symbol} {args.timeframe} | {total_bars} bars | {timestamps[0].date()} -> {timestamps[-1].date()}")
    print(f"Macro Data aligned: DXY ({len(dxy_bars)} bars), US10Y ({len(us10y_bars)} bars).")

    LOOKBACK = 200
    WINDOW_SIZE = 240
    SLIDING_IC_WINDOW = 10

    feature_names = [
        "atr14_norm", "atr_ratio", "rstd20", "rstd100",
        "dist_high50", "dist_low50", "range_pos",
        "ret5", "ret20", "ret100", "mom_accel",
        "trend_str", "adx14", "compress",
        "hour", "session", "dow",
        "dxy_mom5", "dxy_mom20", "us10y_chg", "macro_corr"
    ]
    feature_labels = [
        "ATR14/Price", "ATR50/ATR14", "RStd20", "RStd100",
        "DistHigh50", "DistLow50", "RangePos",
        "Return5", "Return20", "Return100", "MomAccel",
        "TrendStr", "ADX14", "Compress",
        "Hour", "Session", "DayOfWeek",
        "DXY Mom5", "DXY Mom20", "US10Y Chg", "Macro Regime"
    ]
    feature_families = [
        "Volatility", "Volatility", "Volatility", "Volatility",
        "Range", "Range", "Range",
        "Momentum", "Momentum", "Momentum", "Momentum",
        "Structure", "Structure", "Structure",
        "Time", "Time", "Time",
        "Macro", "Macro", "Macro", "Macro"
    ]

    features_matrix: dict[str, list[float]] = {name: [] for name in feature_names}
    forward_returns: list[float] = []
    window_count = 0

    idx = LOOKBACK
    while idx + WINDOW_SIZE <= total_bars:
        lb_closes = closes[idx - LOOKBACK:idx]
        lb_highs = highs[idx - LOOKBACK:idx]
        lb_lows = lows[idx - LOOKBACK:idx]
        lb_timestamps = timestamps[idx - LOOKBACK:idx]

        window_closes = closes[idx:idx + WINDOW_SIZE]
        fwd_ret = (window_closes[-1] - window_closes[0]) / window_closes[0]
        forward_returns.append(fwd_ret)

        macro_data = {
            "dxy_mom5": float(dxy_mom5_arr[idx - 1]),
            "dxy_mom20": float(dxy_mom20_arr[idx - 1]),
            "us10y_spread_chg": float(us10y_chg_arr[idx - 1]),
            "macro_regime_corr": float(macro_corr_arr[idx - 1]),
        }

        feats = extract_extended_features(lb_closes, lb_highs, lb_lows, lb_timestamps, macro_data=macro_data)
        for name in feature_names:
            features_matrix[name].append(feats.get(name, float("nan")))

        window_count += 1
        idx += WINDOW_SIZE

    forward_returns_arr = np.array(forward_returns)
    n_windows = len(forward_returns_arr)

    print(f"Windows: {n_windows} bi-weekly (size={WINDOW_SIZE}, lookback={LOOKBACK})")
    print()

    # ---------------------------------------------------------------------------
    # Compute metrics per feature
    # ---------------------------------------------------------------------------

    results = []

    for name, label, family in zip(feature_names, feature_labels, feature_families):
        values = np.array(features_matrix[name])
        
        # Calculate coverage by excluding initial NaNs (burn-in period)
        initial_nans = 0
        for val in values:
            if np.isnan(val):
                initial_nans += 1
            else:
                break
                
        adjusted_n_windows = n_windows - initial_nans
        valid_mask = ~np.isnan(values)
        coverage = valid_mask.sum() / adjusted_n_windows if adjusted_n_windows > 0 else 0.0

        v = values[valid_mask]
        r = forward_returns_arr[valid_mask]

        ic = pearson_ic(v, r)
        rank_ic = spearman_rank_ic(v, r)

        s_ic = sliding_ic(v, r, SLIDING_IC_WINDOW)
        valid_s_ic = s_ic[~np.isnan(s_ic)]

        if len(valid_s_ic) > 1:
            icir = valid_s_ic.mean() / valid_s_ic.std() if valid_s_ic.std() > 0 else float("nan")
        else:
            icir = float("nan")

        half = len(v) // 2
        rank_ic_h1 = spearman_rank_ic(v[:half], r[:half])
        rank_ic_h2 = spearman_rank_ic(v[half:], r[half:])

        if np.isnan(rank_ic_h1) or np.isnan(rank_ic_h2):
            stability = "N/A"
        elif np.sign(rank_ic_h1) == np.sign(rank_ic_h2):
            ratio = abs(rank_ic_h2) / abs(rank_ic_h1) if abs(rank_ic_h1) > 0.001 else float("inf")
            stability = "Stable" if ratio > 0.5 else "Weakening"
        else:
            stability = "Inverted"

        retained = (
            abs(rank_ic) > 0.10
            and not np.isnan(icir) and icir > 0.30
            and coverage > 0.95
            and stability == "Stable"
        )

        results.append({
            "label": label,
            "family": family,
            "ic": ic,
            "rank_ic": rank_ic,
            "coverage": coverage,
            "icir": icir,
            "rank_ic_h1": rank_ic_h1,
            "rank_ic_h2": rank_ic_h2,
            "stability": stability,
            "retained": retained,
            "sliding_ic": valid_s_ic,
        })

    # ---------------------------------------------------------------------------
    # Report
    # ---------------------------------------------------------------------------

    print("=" * 110)
    print("EXTENDED FEATURE PREDICTIVE QUALITY -- XAUUSD H1 (2 years, bi-weekly windows)")
    print("=" * 110)
    print()

    header = f"{'Family':<11} | {'Feature':<12} | {'IC':>7} | {'RankIC':>7} | {'Cov':>5} | {'ICIR':>7} | {'RkIC H1':>8} | {'RkIC H2':>8} | {'Stable':<10} | {'Keep':<4}"
    print(header)
    print("-" * len(header))

    current_family = ""
    for res in results:
        if res['family'] != current_family:
            if current_family:
                print("-" * len(header))
            current_family = res['family']

        def fmt(v: float, w: int = 7) -> str:
            return f"{v:{w}.4f}" if not np.isnan(v) else f"{'NaN':>{w}}"

        keep = "YES" if res['retained'] else ""
        print(
            f"{res['family']:<11} | {res['label']:<12} | "
            f"{fmt(res['ic'])} | {fmt(res['rank_ic'])} | "
            f"{res['coverage']:>4.0%} | {fmt(res['icir'])} | "
            f"{fmt(res['rank_ic_h1'], 8)} | {fmt(res['rank_ic_h2'], 8)} | "
            f"{res['stability']:<10} | {keep:<4}"
        )

    print()

    # Sliding IC for retained or near-retained features
    interesting = [r for r in results if abs(r['rank_ic']) > 0.08 or r['retained']]
    if interesting:
        print("-" * 50)
        print("SLIDING IC (window=10) -- features with |Rank IC| > 0.08")
        print("-" * 50)
        for res in interesting:
            s = res['sliding_ic']
            formatted = ", ".join(f"{v:.3f}" for v in s) if len(s) > 0 else "(insufficient data)"
            print(f"\n{res['label']} (family: {res['family']}):")
            print(f"  [{formatted}]")
        print()

    # ---------------------------------------------------------------------------
    # Decision
    # ---------------------------------------------------------------------------

    retained = [r for r in results if r['retained']]
    n_retained = len(retained)

    print("=" * 110)
    print("DECISION")
    print("=" * 110)
    print()

    if n_retained == 0:
        # Check if any are close
        near_miss = [r for r in results if abs(r['rank_ic']) > 0.10 and not r['retained']]
        print("STOP")
        print()
        print("Aucune feature ne satisfait les 4 criteres de retention simultanement.")
        print("Le Research Council reste suspendu.")
        print("Prochaine etape : explorer des features alternatives (microstructure, inter-marche, macro).")
        if near_miss:
            print()
            print(f"Features proches du seuil ({len(near_miss)}) :")
            for r in near_miss:
                reasons = []
                if np.isnan(r['icir']) or r['icir'] <= 0.30:
                    reasons.append(f"ICIR={r['icir']:.3f}" if not np.isnan(r['icir']) else "ICIR=NaN")
                if r['coverage'] <= 0.95:
                    reasons.append(f"Coverage={r['coverage']:.0%}")
                if r['stability'] != "Stable":
                    reasons.append(f"Stability={r['stability']}")
                print(f"  {r['label']:>12} | Rank IC={r['rank_ic']:+.4f} | Echec: {', '.join(reasons)}")

    elif n_retained == 1:
        f = retained[0]
        print(f"Une feature robuste trouvee : {f['label']} (famille: {f['family']})")
        print(f"  Rank IC = {f['rank_ic']:+.4f}, ICIR = {f['icir']:.3f}, Stability = {f['stability']}")
        print()
        print("Prochain developpement : Regime Analyst unique base sur cette feature.")
        print("Le Research Council complet reste suspendu.")

    elif n_retained <= 3:
        names = ", ".join(f"{r['label']} ({r['family']})" for r in retained)
        print(f"{n_retained} features robustes trouvees : {names}")
        print()
        for r in retained:
            print(f"  {r['label']:>12} | Rank IC={r['rank_ic']:+.4f} | ICIR={r['icir']:.3f} | {r['stability']}")
        print()
        print("Le projet peut demarrer un Research Council minimal :")
        print("  - Regime Analyst")
        print("  - Risk Analyst")
        print("  - Research Analyst")
        print()
        print("Aucun Execution Agent. Aucun Portfolio Agent.")

    else:
        names = ", ".join(r['label'] for r in retained)
        print(f"{n_retained} features robustes trouvees : {names}")
        print()
        for r in retained:
            print(f"  {r['label']:>12} | Rank IC={r['rank_ic']:+.4f} | ICIR={r['icir']:.3f} | {r['stability']}")
        print()
        print("Signal riche. Le Research Council peut demarrer avec des features solides.")

    print()
    print("=" * 110)
    print(f"Retention: |Rank IC| > 0.10, ICIR > 0.30, Coverage > 95%, Stable half-split")
    print(f"Observations: {n_windows} windows | Lookback: {LOOKBACK} bars | Window: {WINDOW_SIZE} bars")
    print("=" * 110)


if __name__ == "__main__":
    main()
