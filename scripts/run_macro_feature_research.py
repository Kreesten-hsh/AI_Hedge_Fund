"""Recherche d'Alpha IC / IR / significativité sur les features Macroéconomiques FRED et Gold.

Exécute l'analyse d'information (IC Spearman, t-stat n_eff corrigé) sur les caractéristiques macro
(DFII10 Taux réel 10 ans, DXY Index) couplées aux barres Gold M1 sur des horizons tradables.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Sequence, Dict, List

import pandas as pd

from aegis_trade.domain.core import AssetClass, Symbol, TimeFrame
from aegis_trade.domain.features import FeatureSet
from aegis_trade.domain.research import ResearchMetadata, FeatureScore
from aegis_trade.infrastructure.research.research_engine import (
    SIGNIFICANCE_T,
    ResearchEngine,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("run_macro_feature_research")


def load_macro_feature_sets(parquet_path: str) -> list[FeatureSet]:
    logger.info(f"Chargement des FeatureSets Macro depuis {parquet_path}...")
    df = pd.read_parquet(parquet_path)
    
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df.set_index("timestamp", inplace=True)
    elif not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, utc=True)
        
    df.sort_index(inplace=True)
    
    # Calcul indispensable de return_1d pour le moteur de calcul des rendements forward
    if "return_1d" not in df.columns:
        df["return_1d"] = df["close"].pct_change().fillna(0.0)
        
    feature_cols = [c for c in df.columns if c.startswith("macro_") or c.startswith("feature_macro_")]
    feature_cols.append("return_1d")
    
    logger.info(f"Features Macro à analyser ({len(feature_cols)}): {feature_cols}")
    
    symbol = Symbol(name="frxXAUUSD", asset_class=AssetClass.COMMODITIES)
    timeframe = TimeFrame.M1
    
    feature_sets: list[FeatureSet] = []
    for ts, row in df.iterrows():
        feats = {col: float(row[col]) for col in feature_cols if not pd.isna(row[col])}
        dt = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts
        feature_sets.append(
            FeatureSet(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=dt,
                features=feats,
            )
        )
        
    logger.info(f"{len(feature_sets)} FeatureSets Macro construits.")
    return feature_sets


def evaluate_segment(
    feature_sets: Sequence[FeatureSet],
    symbol: Symbol,
    timeframe: TimeFrame,
    horizon: int,
) -> Dict[str, FeatureScore]:
    metadata = ResearchMetadata(
        symbol=symbol,
        timeframe=timeframe,
        start_time=feature_sets[0].timestamp,
        end_time=feature_sets[-1].timestamp,
        forward_returns_lag=horizon,
    )
    result = ResearchEngine().evaluate(list(feature_sets), metadata)
    return result.feature_scores


def main() -> int:
    parser = argparse.ArgumentParser(description="Recherche d'Alpha sur Features Macro Gold FRED.")
    parser.add_argument("--parquet", default="data/market_data/xauusd_macro.parquet")
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument(
        "--horizons",
        type=int,
        nargs="+",
        default=[5, 10, 15, 30, 60, 120, 240],
        help="Horizons forward (barres M1).",
    )
    parser.add_argument("--json-out", default="docs/measures/sig-02/features_gold_macro.json")
    args = parser.parse_args()

    fsets = load_macro_feature_sets(args.parquet)
    symbol = Symbol(name="frxXAUUSD", asset_class=AssetClass.COMMODITIES)
    timeframe = TimeFrame.M1
    
    cut = int(len(fsets) * args.train_ratio)
    train_sets, test_sets = fsets[:cut], fsets[cut:]
    logger.info(f"Split chronologique: {len(train_sets)} train / {len(test_sets)} test.")

    results_by_horizon: dict[int, list[dict]] = {}
    surviving_pairs: list[dict] = []

    for h in args.horizons:
        print("\n" + "=" * 80)
        print(f"  HORIZON MACRO {h} barres M1 ({h} minutes)")
        print("=" * 80)
        
        train_scores = evaluate_segment(train_sets, symbol, timeframe, horizon=h)
        test_scores = evaluate_segment(test_sets, symbol, timeframe, horizon=h)

        rows: list[dict] = []
        for name, score_test in test_scores.items():
            if name == "return_1d":
                continue  # Ne pas évaluer la base
            score_tr = train_scores.get(name)
            ic_tr = score_tr.ic_spearman if score_tr else 0.0
            ic_te = score_test.ic_spearman
            t_te = score_test.ic_t_stat
            
            # Un signal survecut s'il franchit |t| > 2.0 sur le TEST et conserve le même signe qu'en TRAIN
            survived = (
                abs(t_te) >= SIGNIFICANCE_T
                and (ic_tr * ic_te) > 0.0
            )
            
            verdict = "SURVIT" if survived else ""
            if survived:
                surviving_pairs.append({
                    "feature": name,
                    "horizon": h,
                    "ic_train": ic_tr,
                    "ic_test": ic_te,
                    "t_test": t_te,
                })
                
            rows.append({
                "feature": name,
                "ic_train": round(ic_tr, 4),
                "ic_test": round(ic_te, 4),
                "t_test": round(t_te, 2),
                "n_eff": score_test.effective_observations,
                "ir_test": round(score_test.ic_information_ratio, 3),
                "stability": round(score_test.stability, 2),
                "verdict": verdict,
            })

        rows.sort(key=lambda r: abs(r["t_test"]), reverse=True)
        results_by_horizon[h] = rows

        print(f"{'feature':<32} {'IC train':<10} {'IC test':<10} {'t test':<9} {'n_eff':<7} {'IR test':<9} {'stab':<6} {'verdict'}")
        print("-" * 95)
        for r in rows:
            print(
                f"{r['feature']:<32} {r['ic_train']:<+10.4f} {r['ic_test']:<+10.4f} "
                f"{r['t_test']:<+9.2f} {r['n_eff']:<7} {r['ir_test']:<+9.3f} "
                f"{r['stability']:<6.2f} {r['verdict']}"
            )
            
        n_surv = sum(1 for r in rows if r["verdict"] == "SURVIT")
        print(f"\n  {n_surv}/{len(rows)} features macro survivent au test.")

    print("\n" + "=" * 80)
    print("  VERDICT MACRO GLOBAL")
    print("=" * 80)
    print(f"  {len(surviving_pairs)} couple(s) feature/horizon survivent au test de significativité (|t| > 2.0).")

    out_path = Path(args.json_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "surviving_pairs": surviving_pairs,
        "horizons": results_by_horizon,
    }, indent=2))
    logger.info(f"Rapport Macro écrit: {out_path}")
    return 0


if __name__ == "__main__":
    main()
