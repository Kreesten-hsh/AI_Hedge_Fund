"""Script d'audit rigoureux et reproductible des sources de données Or (Gold) externes vs Deriv D1.

Compare Deriv `frxXAUUSD` D1 à:
- yfinance: `GC=F` (Futures Gold COMEX), `GLD` (SPDR Gold ETF), `IAU` (iShares Gold ETF)
- FRED (St. Louis Fed): `GOLDAMGBD228NLBM` (Fixing Or LBMA Matin) et `GOLDPMGBD228NLBM` (Fixing Or LBMA Après-midi)

Effectue :
1. Le test de shift temporel (-2 à +2 jours).
2. L'identification des 10 pires jours d'écart (outliers / jours fériés US).
3. Le recalcul de la corrélation post-filtrage des jours d'aberration.
"""

from __future__ import annotations

import asyncio
import os
import logging
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import requests
import yfinance as yf

from aegis_trade.providers.deriv.historical_data import DerivHistoricalData

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("GoldDataAudit")

OUTPUT_DOC = "docs/research/GOLD_DATA_SOURCE_AUDIT.md"


async def fetch_deriv_d1() -> pd.DataFrame:
    client = DerivHistoricalData()
    df = await client.fetch_candles_paginated(symbol="frxXAUUSD", target_count=5000, granularity=86400)
    df["date"] = pd.to_datetime(df["timestamp"]).dt.date
    return df.sort_values("date").reset_index(drop=True)


def download_fred_gold(series_id: str) -> pd.DataFrame:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200 and "DATE" in res.text:
            df = pd.read_csv(pd.io.common.StringIO(res.text))
            df["date"] = pd.to_datetime(df["DATE"]).dt.date
            df["close"] = pd.to_numeric(df[series_id], errors="coerce")
            return df.dropna(subset=["close"]).sort_values("date").reset_index(drop=True)
    except Exception as e:
        logger.warning(f"FRED fetch exception for {series_id}: {e}")
    return pd.DataFrame()


def evaluate_shift_correlations(
    deriv_df: pd.DataFrame, ext_df: pd.DataFrame, ext_close_col: str = "Close"
) -> dict[int, dict[str, float]]:
    d_sub = deriv_df[["date", "close"]].rename(columns={"close": "close_deriv"})
    e_sub = ext_df[["date", ext_close_col]].rename(columns={ext_close_col: "close_ext"})

    merged = pd.merge(d_sub, e_sub, on="date").dropna().sort_values("date").reset_index(drop=True)

    results = {}
    if len(merged) < 20:
        return results

    merged["ret_deriv"] = merged["close_deriv"].pct_change()
    merged["ret_ext"] = merged["close_ext"].pct_change()

    for shift in [-2, -1, 0, 1, 2]:
        if shift == 0:
            s_ext_ret = merged["ret_ext"]
            s_ext_close = merged["close_ext"]
        elif shift > 0:
            s_ext_ret = merged["ret_ext"].shift(shift)
            s_ext_close = merged["close_ext"].shift(shift)
        else:
            s_ext_ret = merged["ret_ext"].shift(shift)
            s_ext_close = merged["close_ext"].shift(shift)

        valid = pd.DataFrame({"ret_deriv": merged["ret_deriv"], "ret_ext": s_ext_ret}).dropna()
        corr = valid["ret_deriv"].corr(valid["ret_ext"]) if len(valid) > 10 else np.nan

        price_valid = pd.DataFrame({"p_deriv": merged["close_deriv"], "p_ext": s_ext_close}).dropna()
        mae_pct = (np.abs(price_valid["p_deriv"] - price_valid["p_ext"]) / price_valid["p_deriv"]).mean() * 100.0 if len(price_valid) > 10 else np.nan

        results[shift] = {"correlation": float(corr), "mae_pct": float(mae_pct), "samples": len(valid)}

    return results


def main() -> None:
    logger.info("Fermeture et extraction des données Deriv D1 Gold...")
    deriv_df = asyncio.run(fetch_deriv_d1())
    logger.info(f"Deriv D1 Gold: {len(deriv_df)} bougies du {deriv_df['date'].min()} au {deriv_df['date'].max()}")

    tickers = ["GC=F", "GLD", "IAU"]
    ext_data: dict[str, pd.DataFrame] = {}

    for t in tickers:
        logger.info(f"Téléchargement yfinance {t}...")
        yf_df = yf.download(t, start="2025-08-01", end="2026-08-07", interval="1d", progress=False)
        if not yf_df.empty:
            if isinstance(yf_df.columns, pd.MultiIndex):
                yf_df.columns = [c[0] for c in yf_df.columns]
            yf_df = yf_df.reset_index()
            yf_df["date"] = pd.to_datetime(yf_df["Date"]).dt.date
            ext_data[t] = yf_df

    # FRED
    for fred_id in ["GOLDAMGBD228NLBM", "GOLDPMGBD228NLBM"]:
        logger.info(f"Téléchargement FRED {fred_id}...")
        f_df = download_fred_gold(fred_id)
        if not f_df.empty:
            ext_data[fred_id] = f_df

    audit_summary: dict[str, dict] = {}
    head_tables: dict[str, pd.DataFrame] = {}
    outliers_tables: dict[str, pd.DataFrame] = {}
    filtered_corrs: dict[str, dict[str, float]] = {}

    for name, df in ext_data.items():
        close_col = "close" if "close" in df.columns else "Close"
        shift_res = evaluate_shift_correlations(deriv_df, df, close_col)
        audit_summary[name] = shift_res

        d_sub = deriv_df[["date", "close"]].rename(columns={"close": "close_deriv"})
        e_sub = df[["date", close_col]].rename(columns={close_col: f"close_{name}"})
        merged = pd.merge(d_sub, e_sub, on="date").dropna().sort_values("date").reset_index(drop=True)

        # Rendements
        merged["ret_deriv"] = merged["close_deriv"].pct_change()
        merged["ret_ext"] = merged[f"close_{name}"].pct_change()
        merged["diff_ret"] = np.abs(merged["ret_deriv"] - merged["ret_ext"])
        merged["diff_price_pct"] = np.abs(merged[f"close_{name}"] - merged["close_deriv"]) / merged["close_deriv"] * 100.0

        head_tables[name] = merged.head(15)

        # 10 pires jours par écart de rendement absolu
        worst_days = merged.dropna(subset=["diff_ret"]).sort_values("diff_ret", ascending=False).head(10)
        outliers_tables[name] = worst_days

        # Recalcul de la corrélation en excluant les 5% ou 10 pires jours
        clean_df = merged.drop(worst_days.index).dropna(subset=["ret_deriv", "ret_ext"])
        corr_raw = merged.dropna(subset=["ret_deriv", "ret_ext"])["ret_deriv"].corr(merged["ret_ext"])
        corr_clean = clean_df["ret_deriv"].corr(clean_df["ret_ext"])

        filtered_corrs[name] = {
            "corr_raw": float(corr_raw),
            "corr_clean_top10": float(corr_clean),
            "removed_count": len(worst_days),
            "total_samples": len(merged),
        }

    # Imprimer diagnostic console
    print("\n=======================================================")
    print("      DIAGNOSTIC DES 10 PIRES JOURS D'ÉCART (OUTLIERS)")
    print("=======================================================\n")
    for name, table in outliers_tables.items():
        print(f"--- Ticker/Source: {name} (Top 10 pires rendements décalés) ---")
        sub = table[["date", "close_deriv", f"close_{name}", "ret_deriv", "ret_ext", "diff_ret"]]
        print(sub.to_string(index=False))
        print(f"Corrélation Brute = {filtered_corrs[name]['corr_raw']:.4f} | Corrélation Nettoyée (hors Top 10) = {filtered_corrs[name]['corr_clean_top10']:.4f}")
        print("\n")

    # Génération du document Markdown docs/research/GOLD_DATA_SOURCE_AUDIT.md
    os.makedirs("docs/research", exist_ok=True)
    with open(OUTPUT_DOC, "w", encoding="utf-8") as f:
        f.write("# AUDIT QUANTITATIF DES SOURCES DE DONNÉES GOLD (OR) EXTERNES VS DERIV\n\n")
        f.write(f"**Date d'exécution** : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n")
        f.write(f"**Données Deriv D1** : {len(deriv_df)} bougies (`frxXAUUSD`) du {deriv_df['date'].min()} au {deriv_df['date'].max()}\n\n")

        f.write("## 1. Synthèse des Corrélations Brutes et Nettoyées des Outliers\n\n")
        f.write("| Source | Corrélation Brute (250j) | Corrélation Filtrée (Hors Top 10 Outliers) | MAE% Prix | Éligible (r >= 0.98) |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- |\n")

        for name, metrics in filtered_corrs.items():
            c_raw = metrics["corr_raw"]
            c_clean = metrics["corr_clean_top10"]
            eligible = "✅ OUI" if c_clean >= 0.98 else "❌ NON"

            if name in ["GLD", "IAU"]:
                mae_str = "N/A (Prix part ETF)"
            else:
                mae_str = f"{audit_summary[name][0]['mae_pct']:.4f}%"

            f.write(f"| **{name}** | {c_raw:.4f} | **{c_clean:.4f}** | {mae_str} | {eligible} |\n")

        f.write("\n\n## 2. Matrice des Shifts Temporels (-2 à +2 jours)\n\n")
        f.write("| Source | Shift -2d | Shift -1d | Shift 0d (Direct) | Shift +1d | Shift +2d | Meilleur r |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")

        for name, shifts in audit_summary.items():
            r_m2 = shifts.get(-2, {}).get("correlation", np.nan)
            r_m1 = shifts.get(-1, {}).get("correlation", np.nan)
            r_0 = shifts.get(0, {}).get("correlation", np.nan)
            r_p1 = shifts.get(1, {}).get("correlation", np.nan)
            r_p2 = shifts.get(2, {}).get("correlation", np.nan)
            best_r = max([r for r in [r_m2, r_m1, r_0, r_p1, r_p2] if not np.isnan(r)])
            f.write(f"| **{name}** | {r_m2:.4f} | {r_m1:.4f} | **{r_0:.4f}** | {r_p1:.4f} | {r_p2:.4f} | **{best_r:.4f}** |\n")

        f.write("\n\n## 3. Top 10 des Pires Jours d'Écart de Rendement (Analyse d'Outliers / Jours Fériés US)\n\n")
        for name, table in outliers_tables.items():
            f.write(f"### Source : `{name}`\n\n")
            f.write("| Date | Close Deriv | Close Ext | Ret Deriv | Ret Ext | Écart Rendement Absolu |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")
            for _, row in table.iterrows():
                f.write(f"| **{row['date']}** | {row['close_deriv']:.2f} | {row[f'close_{name}']:.2f} | {row['ret_deriv']:+.4f} | {row['ret_ext']:+.4f} | **{row['diff_ret']:.4f}** |\n")
            f.write("\n\n")

        f.write("## 4. Extraits Ligne par Ligne (15 Premiers Jours de Recouvrement)\n\n")
        for name, table in head_tables.items():
            f.write(f"### Source : `{name}`\n\n")
            f.write("| Date | Close Deriv | Close Ext | Diff % |\n")
            f.write("| :--- | :--- | :--- | :--- |\n")
            for _, row in table.iterrows():
                f.write(f"| {row['date']} | {row['close_deriv']:.2f} | {row[f'close_{name}']:.2f} | {row['diff_price_pct']:+.4f}% |\n")
            f.write("\n\n")

    logger.info(f"Rapport mis à jour dans {OUTPUT_DOC}")


if __name__ == "__main__":
    main()
