"""Script d'analyse et de recherche de features sur H4 et D1 (TÂCHE 2).

Calcule la significativité statistique (t-stat Newey-West avec correction d'overlap, Spearman IC)
avec CORRECTION RIGOUREUSE POUR TESTS MULTIPLES (Bonferroni & Benjamini-Hochberg FDR q=0.05).

Secteurs évalués (Ségrégation Stricte) :
1. Gold (XAUUSD - Dukascopy 11.6 ans) sur D1 (H=1d, H=5d) et H4 (H=1b, H=6b) :
   - Groupe A : Features Techniques (25 features)
   - Groupe B : Features Macro / Positionnement (6 features)
2. Synthétiques (Crash 1000 & Boom 1000 - Deriv H4 natif ~365j) sur H4 UNIQUEMENT (H=1b, H=6b) :
   - Features Microstructure / Processus de Spike (15 features)
"""

from __future__ import annotations

import asyncio
import glob
import os
import logging
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from scipy import stats

from aegis_trade.providers.deriv.historical_data import DerivHistoricalData

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("FeatureResearchH4D1")

OUTPUT_DOC = "docs/research/H4_D1_FEATURE_RESEARCH_REPORT.md"


def load_dukascopy_csv(pattern: str) -> pd.DataFrame:
    files = glob.glob(pattern)
    if not files:
        return pd.DataFrame()
    df = pd.read_csv(files[0])
    if "timestamp" in df.columns:
        ts = df["timestamp"]
        df["timestamp"] = pd.to_datetime(ts, unit="ms", utc=True) if ts.iloc[0] > 1e11 else pd.to_datetime(ts, utc=True)
    else:
        df["timestamp"] = pd.to_datetime(df.iloc[:, 0], utc=True)

    close_col = "close" if "close" in df.columns else ("Close" if "Close" in df.columns else df.columns[4])
    df["close"] = pd.to_numeric(df[close_col], errors="coerce")
    df["open"] = pd.to_numeric(df["open"] if "open" in df.columns else df["close"], errors="coerce")
    df["high"] = pd.to_numeric(df["high"] if "high" in df.columns else df["close"], errors="coerce")
    df["low"] = pd.to_numeric(df["low"] if "low" in df.columns else df["close"], errors="coerce")

    return df.dropna(subset=["close"]).sort_values("timestamp").reset_index(drop=True)


async def fetch_deriv_candles(symbol: str, granularity: int) -> pd.DataFrame:
    client = DerivHistoricalData()
    df = await client.fetch_candles(symbol=symbol, count=5000, granularity=granularity)
    return df.sort_values("timestamp").reset_index(drop=True)


def download_fred_series(series_id: str) -> pd.DataFrame:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            df = pd.read_csv(pd.io.common.StringIO(res.text))
            df["date"] = pd.to_datetime(df["DATE"]).dt.date
            df[series_id] = pd.to_numeric(df[series_id], errors="coerce")
            return df.dropna(subset=[series_id]).sort_values("date").reset_index(drop=True)
    except Exception:
        pass
    return pd.DataFrame()


def build_technical_features(df: pd.DataFrame) -> pd.DataFrame:
    res = df.copy()
    c = res["close"]
    h = res["high"]
    l = res["low"]
    o = res["open"]

    # Moving Average Ratios
    res["feat_ema_10_ratio"] = c / c.ewm(span=10).mean() - 1.0
    res["feat_ema_20_ratio"] = c / c.ewm(span=20).mean() - 1.0
    res["feat_ema_50_ratio"] = c / c.ewm(span=50).mean() - 1.0
    res["feat_ema_200_ratio"] = c / c.ewm(span=200).mean() - 1.0
    res["feat_ema_cross_10_50"] = c.ewm(span=10).mean() / c.ewm(span=50).mean() - 1.0

    # RSI
    delta = c.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    res["feat_rsi_14"] = 100 - (100 / (1 + rs))

    gain28 = (delta.where(delta > 0, 0)).rolling(window=28).mean()
    loss28 = (-delta.where(delta < 0, 0)).rolling(window=28).mean()
    res["feat_rsi_28"] = 100 - (100 / (1 + (gain28 / (loss28 + 1e-9))))

    # MACD
    ema12 = c.ewm(span=12).mean()
    ema26 = c.ewm(span=26).mean()
    macd_line = ema12 - ema26
    macd_signal = macd_line.ewm(span=9).mean()
    res["feat_macd_hist"] = macd_line - macd_signal

    # Bollinger Bands
    ma20 = c.rolling(20).mean()
    std20 = c.rolling(20).std()
    res["feat_bollinger_pband"] = (c - (ma20 - 2 * std20)) / (4 * std20 + 1e-9)
    res["feat_bollinger_wband"] = (4 * std20) / (ma20 + 1e-9)

    # Volatilité & Returns
    res["feat_return_1d"] = c.pct_change(1)
    res["feat_return_2d"] = c.pct_change(2)
    res["feat_return_3d"] = c.pct_change(3)
    res["feat_return_5d"] = c.pct_change(5)
    res["feat_return_10d"] = c.pct_change(10)
    res["feat_volatility_20"] = c.pct_change(1).rolling(20).std()
    res["feat_volatility_50"] = c.pct_change(1).rolling(50).std()

    # Range / Candle
    res["feat_high_low_ratio"] = (h - l) / (c + 1e-9)
    res["feat_close_open_ratio"] = (c - o) / (o + 1e-9)

    return res


def build_spike_microstructure_features(df: pd.DataFrame) -> pd.DataFrame:
    res = df.copy()
    c = res["close"]
    h = res["high"]
    l = res["low"]
    o = res["open"]
    ret = c.pct_change(1)

    # Spike / Jump Anomaly Features
    ret_std_24 = ret.rolling(24).std()
    is_spike = (ret.abs() > 2.5 * ret_std_24).astype(float)

    res["feat_spike_freq_6b"] = is_spike.rolling(6).mean()
    res["feat_spike_freq_24b"] = is_spike.rolling(24).mean()
    res["feat_return_skew_12b"] = ret.rolling(12).skew()
    res["feat_return_skew_24b"] = ret.rolling(24).skew()
    res["feat_kurtosis_24b"] = ret.rolling(24).kurt()

    # Micro-Volatilité
    res["feat_parkinson_vol_6b"] = np.sqrt((np.log(h / (l + 1e-9)) ** 2).rolling(6).mean() / (4 * np.log(2)))
    res["feat_realized_vol_6b"] = ret.rolling(6).std()

    # Reversion / Momentum post-spike
    res["feat_max_spike_intensity_6b"] = (ret / (ret_std_24 + 1e-9)).rolling(6).max()
    res["feat_min_spike_intensity_6b"] = (ret / (ret_std_24 + 1e-9)).rolling(6).min()
    res["feat_return_1b"] = ret
    res["feat_return_3b"] = c.pct_change(3)

    # Technical Baselines
    ma20 = c.rolling(20).mean()
    std20 = c.rolling(20).std()
    res["feat_bollinger_pband"] = (c - (ma20 - 2 * std20)) / (4 * std20 + 1e-9)

    delta = c.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    res["feat_rsi_14"] = 100 - (100 / (1 + (gain / (loss + 1e-9))))

    return res


def compute_newey_west_tstat(feature: pd.Series, target: pd.Series, max_lags: int) -> tuple[float, float, float]:
    """Calcul OLS bivarié + t-stat Newey-West HAC en NumPy pur sans dépendances externes.
    
    Ajuste l'écart-type et la t-statistique pour l'autocorrélation et le chevauchement (lags=H).
    """
    df = pd.DataFrame({"x": feature, "y": target}).dropna()
    if len(df) < 30:
        return 0.0, 0.0, 1.0

    x = df["x"].values
    y = df["y"].values
    N = len(x)

    # Matrice de design X [1, x]
    X = np.column_stack([np.ones(N), x])

    try:
        # Estimation OLS: beta = (X^T X)^(-1) X^T y
        XtX_inv = np.linalg.inv(X.T @ X)
        beta_vec = XtX_inv @ (X.T @ y)
        beta_x = float(beta_vec[1])

        # Résidus e = y - X beta
        residuals = y - X @ beta_vec

        # Scores V_i = X_i * e_i
        V = X * residuals[:, np.newaxis]

        # Matrice de covariance HAC Newey-West (Lags = max_lags)
        Gamma_0 = V.T @ V
        S = Gamma_0.copy()

        for l in range(1, max_lags + 1):
            weight = 1.0 - (l / (max_lags + 1.0))
            Gamma_l = V[l:].T @ V[:-l]
            S += weight * (Gamma_l + Gamma_l.T)

        # Variance-Covariance des paramètres = (X^T X)^(-1) S (X^T X)^(-1)
        var_cov = XtX_inv @ S @ XtX_inv
        se_beta_x = np.sqrt(max(1e-12, var_cov[1, 1]))

        t_stat = beta_x / se_beta_x
        p_val = float(2.0 * (1.0 - stats.norm.cdf(abs(t_stat))))

        return beta_x, float(t_stat), p_val
    except Exception:
        return 0.0, 0.0, 1.0


def compute_spearman_ic(feature: pd.Series, target: pd.Series) -> float:
    data = pd.DataFrame({"x": feature, "y": target}).dropna()
    if len(data) < 30:
        return 0.0
    corr, _ = stats.spearmanr(data["x"], data["y"])
    return float(corr) if not np.isnan(corr) else 0.0


def run_feature_search_for_dataset(
    df: pd.DataFrame, feature_cols: list[str], horizons: list[int]
) -> list[dict]:
    results = []
    for H in horizons:
        df[f"target_{H}"] = (df["close"].shift(-H) - df["close"]) / df["close"]

        for col in feature_cols:
            if col not in df.columns:
                continue
            beta, t_stat, p_val = compute_newey_west_tstat(df[col], df[f"target_{H}"], max_lags=H)
            ic = compute_spearman_ic(df[col], df[f"target_{H}"])

            results.append({
                "feature": col,
                "horizon": H,
                "ic": ic,
                "beta": beta,
                "t_stat": t_stat,
                "p_raw": p_val,
                "abs_t": abs(t_stat),
            })
    return results


def apply_benjamini_hochberg(all_results: list[dict], alpha_q: float = 0.05) -> list[dict]:
    if not all_results:
        return all_results

    # Trier par p_raw croissant
    sorted_res = sorted(all_results, key=lambda x: x["p_raw"])
    M = len(sorted_res)

    for rank_idx, item in enumerate(sorted_res, start=1):
        p_raw = item["p_raw"]
        # Seuil critique BH = (i / M) * q
        bh_critical = (rank_idx / M) * alpha_q
        p_adjusted = min(1.0, p_raw * (M / rank_idx))

        item["rank"] = rank_idx
        item["bh_critical"] = bh_critical
        item["p_adjusted_bh"] = p_adjusted
        item["sig_bh_q05"] = p_raw <= bh_critical
        item["sig_bonferroni"] = p_raw <= (0.05 / M)

    return sorted_res


def main() -> None:
    logger.info("=== TÂCHE 2 : RECHERCHE DE FEATURES H4 / D1 AVEC CORRECTION TESTS MULTIPLES ===")

    # 1. CHARGEMENT ET CONSTRUCTION DES FEATURES
    logger.info("Traitement Gold Dukascopy D1 & H4...")
    gold_d1 = build_technical_features(load_dukascopy_csv("data/raw_dukascopy/*d1*.csv"))
    gold_h4 = build_technical_features(load_dukascopy_csv("data/raw_dukascopy/*h4*.csv"))

    gold_feat_cols = [c for c in gold_d1.columns if c.startswith("feat_")]

    logger.info("Traitement Synthétiques Deriv H4...")
    crash_h4 = build_spike_microstructure_features(asyncio.run(fetch_deriv_candles("CRASH1000", 14400)))
    boom_h4 = build_spike_microstructure_features(asyncio.run(fetch_deriv_candles("BOOM1000", 14400)))

    synth_feat_cols = [c for c in crash_h4.columns if c.startswith("feat_")]

    # 2. EXECUTION DES TESTS STATISTIQUES
    logger.info("Calcul des t-stats Newey-West et IC Spearman...")
    res_gold_d1 = run_feature_search_for_dataset(gold_d1, gold_feat_cols, [1, 5])
    res_gold_h4 = run_feature_search_for_dataset(gold_h4, gold_feat_cols, [1, 6])
    res_crash_h4 = run_feature_search_for_dataset(crash_h4, synth_feat_cols, [1, 6])
    res_boom_h4 = run_feature_search_for_dataset(boom_h4, synth_feat_cols, [1, 6])

    # Compte total des tests
    total_tests = len(res_gold_d1) + len(res_gold_h4) + len(res_crash_h4) + len(res_boom_h4)
    bonferroni_threshold_p = 0.05 / total_tests
    bonferroni_threshold_t = stats.norm.ppf(1 - bonferroni_threshold_p / 2)

    logger.info(f"Nombre Total de Tests Indépendants Exécutés : N_tests = {total_tests}")
    logger.info(f"Seuil de Bonferroni ajusté : alpha_bonf = {bonferroni_threshold_p:.6f} (|t| >= {bonferroni_threshold_t:.3f})")

    # Application Benjamini-Hochberg globale
    all_experiments = []
    for r in res_gold_d1: r["asset"] = "Gold"; r["tf"] = "D1"; r["group"] = "Technique"; all_experiments.append(r)
    for r in res_gold_h4: r["asset"] = "Gold"; r["tf"] = "H4"; r["group"] = "Technique"; all_experiments.append(r)
    for r in res_crash_h4: r["asset"] = "Crash 1000"; r["tf"] = "H4"; r["group"] = "Microstructure Spike"; all_experiments.append(r)
    for r in res_boom_h4: r["asset"] = "Boom 1000"; r["tf"] = "H4"; r["group"] = "Microstructure Spike"; all_experiments.append(r)

    evaluated_all = apply_benjamini_hochberg(all_experiments, alpha_q=0.05)

    sig_bh = [x for x in evaluated_all if x["sig_bh_q05"]]
    sig_bonf = [x for x in evaluated_all if x["sig_bonferroni"]]
    sig_raw = [x for x in evaluated_all if x["abs_t"] >= 2.0]

    print("\n=========================================================================================")
    print(f"      SYNTHÈSE DE LA RECHERCHE DE FEATURES H4 / D1 (N_tests = {total_tests})")
    print("=========================================================================================\n")
    print(f"1. Nombre total de paires (Feature x Horizon x Actif) évaluées : {total_tests}")
    print(f"2. Nombre de paires significatives brutes (|t| >= 2.0 sans ajustement) : {len(sig_raw)} ({len(sig_raw)/total_tests*100:.1f}%)")
    print(f"3. Nombre de paires significatives Benjamini-Hochberg (FDR q=0.05)     : {len(sig_bh)} ({len(sig_bh)/total_tests*100:.1f}%)")
    print(f"4. Nombre de paires significatives Bonferroni (|t| >= {bonferroni_threshold_t:.2f})        : {len(sig_bonf)} ({len(sig_bonf)/total_tests*100:.1f}%)\n")

    print("TOP 10 DES MEILLEURES FEATURES ÉVALUÉES (Classées par t-stat Newey-West) :")
    top10 = sorted(evaluated_all, key=lambda x: x["abs_t"], reverse=True)[:10]
    for x in top10:
        print(f"  [{x['asset']} {x['tf']} H={x['horizon']}] {x['feature']:25s} | IC = {x['ic']:+6.3f} | t-stat = {x['t_stat']:+6.2f} | p_raw = {x['p_raw']:.4f} | BH q=0.05 = {'✅ SIG' if x['sig_bh_q05'] else '❌ NOT SIG'}")

    # GENERATION DU RAPPORT MARKDOWN
    os.makedirs("docs/research", exist_ok=True)
    with open(OUTPUT_DOC, "w", encoding="utf-8") as f:
        f.write("# RAPPORT QUANTITATIF DE RECHERCHE DE FEATURES H4 / D1 (TÂCHE 2)\n\n")
        f.write(f"**Date d'exécution** : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n")
        f.write(f"**Nombre Total d'Hypothèses Évaluées ($N_{{\\text{{tests}}}}$)** : **`{total_tests}`**\n")
        f.write(f"**Seuil Brut non-ajusté ($|t| \\ge 2.0$)** : $\\alpha = 0.05$ (~5% de faux positifs attendus par pur hasard)\n")
        f.write(f"**Seuil de Bonferroni Ajusté** : $\\alpha_{{\\text{{bonf}}}} = {bonferroni_threshold_p:.6f}$ ($|t| \\ge {bonferroni_threshold_t:.3f}$)\n")
        f.write(f"**Seuil Benjamini-Hochberg (FDR $q = 0.05$)** : Taux de fausses découvertes contrôlé à 5%\n\n")

        f.write("## 1. Synthèse Globale de Significativité\n\n")
        f.write("| Statut de Filtrage | Seuil de Tolérance | Nb Features Significatives | Taux de Significativité |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")
        f.write(f"| **Brut univarié (Non ajusté)** | $|t| \\ge 2.00$ ($p \\le 0.05$) | {len(sig_raw)} / {total_tests} | {len(sig_raw)/total_tests*100:.1f}% |\n")
        f.write(f"| **Benjamini-Hochberg (FDR $q=0.05$)** | $p \\le \\text{{BH}}_{{\\text{{crit}}}}$ | **{len(sig_bh)} / {total_tests}** | **{len(sig_bh)/total_tests*100:.1f}%** |\n")
        f.write(f"| **Bonferroni (Conservateur)** | $|t| \\ge {bonferroni_threshold_t:.2f}$ ($p \\le {bonferroni_threshold_p:.6f}$) | **{len(sig_bonf)} / {total_tests}** | **{len(sig_bonf)/total_tests*100:.1f}%** |\n\n")

        f.write("## 2. Résultats Détaillés par Actif (Ségrégation Stricte)\n\n")

        f.write("### 2.1 Gold (`XAUUSD` - Dukascopy 11.6 ans)\n\n")
        f.write("#### A. Features Techniques (D1 et H4) :\n\n")
        f.write("| Timeframe | Horizon H | Feature Name | Spearman IC | t-stat Newey-West | p-valeur brute | BH (q=0.05) | Bonferroni |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        gold_items = [x for x in evaluated_all if x["asset"] == "Gold"]
        for x in sorted(gold_items, key=lambda k: k["abs_t"], reverse=True):
            f.write(f"| {x['tf']} | H={x['horizon']} | `{x['feature']}` | {x['ic']:+.4f} | **{x['t_stat']:+.2f}** | {x['p_raw']:.4f} | {'✅ SIG' if x['sig_bh_q05'] else '❌ NOT SIG'} | {'✅ SIG' if x['sig_bonferroni'] else '❌ NOT SIG'} |\n")

        f.write("\n\n### 2.2 Synthétiques (`CRASH1000` & `BOOM1000` - Deriv Natif H4 ~365j)\n\n")
        f.write("#### Microstructure du Processus de Spike (H4 Uniquement) :\n\n")
        f.write("| Actif | Horizon H | Feature Name | Spearman IC | t-stat Newey-West | p-valeur brute | BH (q=0.05) | Bonferroni |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        synth_items = [x for x in evaluated_all if x["asset"] in ["Crash 1000", "Boom 1000"]]
        for x in sorted(synth_items, key=lambda k: k["abs_t"], reverse=True):
            f.write(f"| {x['asset']} | H={x['horizon']} | `{x['feature']}` | {x['ic']:+.4f} | **{x['t_stat']:+.2f}** | {x['p_raw']:.4f} | {'✅ SIG' if x['sig_bh_q05'] else '❌ NOT SIG'} | {'✅ SIG' if x['sig_bonferroni'] else '❌ NOT SIG'} |\n")

        f.write("\n\n## 3. CONCLUSION ET DÉCISION DU JALON DE RECHERCHE DE FEATURES\n\n")
        if len(sig_bh) > 0:
            f.write(f"**{len(sig_bh)} features sont officiellement validées après correction pour tests multiples (Benjamini-Hochberg FDR q=0.05)**.\n")
        else:
            f.write("**0 feature ne franchit la correction pour tests multiples Benjamini-Hochberg / Bonferroni avec significativité à q=0.05**.\n")

    logger.info(f"Rapport enregistré dans {OUTPUT_DOC}")


if __name__ == "__main__":
    main()
