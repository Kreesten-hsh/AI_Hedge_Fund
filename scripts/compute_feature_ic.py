"""
Feature Predictive Validation — Research Phase 0

Evaluates the predictive quality of 3 features on XAUUSD H1 data
across ~46 bi-weekly windows, using only lookback data (no look-ahead bias).

Features:
  1. EMA20-EMA50 Spread (normalized by price)
  2. EMA20 Slope (10-bar regression)
  3. RSI14

Metrics per feature:
  - Pearson IC
  - Spearman Rank IC
  - Coverage
  - Sliding IC (window=10) + ICIR
  - Half-split stability
"""

import os
import sys
import numpy as np
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from aegis_trade.dataset.repository import StorageDatasetRepository
from aegis_trade.dataset.resolver import DatasetResolver


from aegis_trade.utils.math import (
    pearson_ic,
    spearman_rank_ic,
    sliding_ic,
    compute_ema,
    compute_rsi
)


def extract_features(lookback_closes: np.ndarray) -> dict[str, float]:
    """
    Given 200 close prices (the lookback), compute the 3 features
    at the end of the lookback. Returns NaN for any feature that
    cannot be computed.
    """
    if len(lookback_closes) < 50:
        return {"ema_spread": float("nan"), "ema_slope": float("nan"), "rsi14": float("nan")}

    ema20 = compute_ema(lookback_closes, 20)
    ema50 = compute_ema(lookback_closes, 50)
    last_price = lookback_closes[-1]

    # Feature 1: Normalized EMA spread
    ema_spread = (ema20[-1] - ema50[-1]) / last_price if last_price != 0 else float("nan")

    # Feature 2: EMA20 slope over last 10 bars
    if len(ema20) >= 10:
        ema_slope = (ema20[-1] - ema20[-10]) / ema20[-10] if ema20[-10] != 0 else float("nan")
    else:
        ema_slope = float("nan")

    # Feature 3: RSI14
    rsi14 = compute_rsi(lookback_closes, 14)

    return {"ema_spread": ema_spread, "ema_slope": ema_slope, "rsi14": rsi14}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

import argparse

def main():
    parser = argparse.ArgumentParser(description="Evaluate feature predictive quality.")
    parser.add_argument("--symbol", type=str, default="XAUUSD", help="Symbol to evaluate")
    parser.add_argument("--timeframe", type=str, default="H1", help="Timeframe (e.g., H1)")
    args = parser.parse_args()

    # Load dataset
    repo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "datasets")
    repo = StorageDatasetRepository(repo_path)
    resolver = DatasetResolver(repo)

    dataset = resolver.resolve_latest(args.symbol, args.timeframe)
    all_bars = resolver.load_data(dataset)
    closes = np.array([float(bar.close) for bar in all_bars])
    total_bars = len(closes)

    print(f"Dataset: {args.symbol} {args.timeframe} | {total_bars} bars | {all_bars[0].timestamp.date()} -> {all_bars[-1].timestamp.date()}")

    # Window parameters
    LOOKBACK = 200
    WINDOW_SIZE = 240  # ~2 weeks of H1
    SLIDING_IC_WINDOW = 10

    # Build windows
    feature_names = ["ema_spread", "ema_slope", "rsi14"]
    feature_labels = ["EMA Spread", "EMA Slope", "RSI14"]

    features_matrix = {name: [] for name in feature_names}  # feature -> list of values per window
    forward_returns = []
    window_labels = []
    window_count = 0

    idx = LOOKBACK
    while idx + WINDOW_SIZE <= total_bars:
        lookback_closes = closes[idx - LOOKBACK:idx]
        window_closes = closes[idx:idx + WINDOW_SIZE]

        # Forward return of the window
        fwd_ret = (window_closes[-1] - window_closes[0]) / window_closes[0]
        forward_returns.append(fwd_ret)

        # Features from lookback only (no look-ahead)
        feats = extract_features(lookback_closes)
        for name in feature_names:
            features_matrix[name].append(feats[name])

        window_count += 1
        window_labels.append(f"W{window_count} ({idx}-{idx + WINDOW_SIZE})")
        idx += WINDOW_SIZE

    forward_returns = np.array(forward_returns)
    n_windows = len(forward_returns)

    print(f"Windows: {n_windows} bi-weekly windows (size={WINDOW_SIZE}, lookback={LOOKBACK})")
    print()

    # ---------------------------------------------------------------------------
    # Compute metrics per feature
    # ---------------------------------------------------------------------------

    results = []

    for name, label in zip(feature_names, feature_labels):
        values = np.array(features_matrix[name])
        valid_mask = ~np.isnan(values)
        coverage = valid_mask.sum() / n_windows

        v = values[valid_mask]
        r = forward_returns[valid_mask]

        # IC and Rank IC
        ic = pearson_ic(v, r)
        rank_ic = spearman_rank_ic(v, r)

        # Sliding IC
        s_ic = sliding_ic(v, r, SLIDING_IC_WINDOW)
        valid_s_ic = s_ic[~np.isnan(s_ic)]

        if len(valid_s_ic) > 1:
            icir = valid_s_ic.mean() / valid_s_ic.std() if valid_s_ic.std() > 0 else float("nan")
        else:
            icir = float("nan")

        # Half-split stability
        half = len(v) // 2
        rank_ic_h1 = spearman_rank_ic(v[:half], r[:half])
        rank_ic_h2 = spearman_rank_ic(v[half:], r[half:])

        # Stability assessment
        if np.isnan(rank_ic_h1) or np.isnan(rank_ic_h2):
            stability = "N/A"
        elif np.sign(rank_ic_h1) == np.sign(rank_ic_h2):
            ratio = abs(rank_ic_h2) / abs(rank_ic_h1) if abs(rank_ic_h1) > 0.001 else float("inf")
            if ratio > 0.5:
                stability = "Stable"
            else:
                stability = "Weakening"
        else:
            stability = "Inverted"

        # Retention criteria
        retained = (
            abs(rank_ic) > 0.10
            and not np.isnan(icir) and icir > 0.30
            and coverage > 0.95
            and stability == "Stable"
        )

        results.append({
            "label": label,
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

    print("=" * 90)
    print("FEATURE PREDICTIVE QUALITY — XAUUSD H1 (2 years, bi-weekly windows)")
    print("=" * 90)
    print()

    # Summary table
    header = f"{'Feature':<12} | {'IC':>7} | {'Rank IC':>8} | {'Coverage':>8} | {'ICIR':>7} | {'RkIC H1':>8} | {'RkIC H2':>8} | {'Stable':<10} | {'Retained':<8}"
    print(header)
    print("-" * len(header))
    for res in results:
        ic_str = f"{res['ic']:.4f}" if not np.isnan(res['ic']) else "NaN"
        ric_str = f"{res['rank_ic']:.4f}" if not np.isnan(res['rank_ic']) else "NaN"
        cov_str = f"{res['coverage']:.1%}"
        icir_str = f"{res['icir']:.4f}" if not np.isnan(res['icir']) else "NaN"
        h1_str = f"{res['rank_ic_h1']:.4f}" if not np.isnan(res['rank_ic_h1']) else "NaN"
        h2_str = f"{res['rank_ic_h2']:.4f}" if not np.isnan(res['rank_ic_h2']) else "NaN"
        ret_str = "YES" if res['retained'] else "NO"
        print(f"{res['label']:<12} | {ic_str:>7} | {ric_str:>8} | {cov_str:>8} | {icir_str:>7} | {h1_str:>8} | {h2_str:>8} | {res['stability']:<10} | {ret_str:<8}")

    print()

    # Sliding IC series
    print("-" * 50)
    print("SLIDING IC (window=10)")
    print("-" * 50)
    for res in results:
        s = res['sliding_ic']
        formatted = ", ".join(f"{v:.3f}" for v in s) if len(s) > 0 else "(insufficient data)"
        print(f"\n{res['label']}:")
        print(f"  [{formatted}]")

    print()

    # ---------------------------------------------------------------------------
    # Decision
    # ---------------------------------------------------------------------------

    retained_features = [r for r in results if r['retained']]
    n_retained = len(retained_features)

    print("=" * 90)
    print("DECISION")
    print("=" * 90)
    print()

    if n_retained == 0:
        print("STOP")
        print()
        print("Les features actuelles ne présentent pas suffisamment de pouvoir prédictif.")
        print("Le développement du Research Council est suspendu.")
        print("La prochaine étape consiste à rechercher de nouvelles features.")
    elif n_retained == 1:
        print(f"Une feature est suffisamment robuste : {retained_features[0]['label']}")
        print()
        print("Le prochain développement sera un Regime Analyst unique.")
        print("Le Research Council complet reste suspendu.")
    else:
        names = ", ".join(r['label'] for r in retained_features)
        print(f"Les features présentent un pouvoir prédictif suffisant : {names}")
        print()
        print("Le projet peut démarrer un Research Council minimal :")
        print("  - Regime Analyst")
        print("  - Risk Analyst")
        print("  - Research Analyst")
        print()
        print("Aucun Execution Agent.")
        print("Aucun Portfolio Agent.")

    print()
    print("=" * 90)
    print(f"Retention criteria: |Rank IC| > 0.10, ICIR > 0.30, Coverage > 95%, Stable half-split")
    print(f"Observations: {n_windows} windows | Lookback: {LOOKBACK} bars | Window: {WINDOW_SIZE} bars")
    print("=" * 90)


if __name__ == "__main__":
    main()
