"""Script d'analyse et de recherche de features de POSITIONNEMENT (CFTC COT & SPDR GLD ETF Flows).

Respecte strictement les leçons d'économétrie scellées à l'ADR 0030 :
1. Alignement causal strict : COT rapporté le mardi -> lag de 6 jours (disponible lundi 00:00 UTC), ZERO lookahead bias.
2. Test de stationnarité ADF préalable sur chaque niveau avant tout test de significativité.
3. Test de cointégration Engle-Granger obligatoire pour tout niveau I(1).
4. Contrôle des fausses découvertes via Benjamini-Hochberg (FDR q=0.05) et Bonferroni sur la famille de positionnement.
"""

from __future__ import annotations

import glob
import io
import json
import logging
import os
import subprocess
import urllib.request
import zipfile

import numpy as np
import pandas as pd
from scipy import stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("PositioningFeatureResearch")

OUTPUT_DOC = "docs/research/POSITIONING_FEATURE_RESEARCH_REPORT.md"


def load_dukascopy_gold(pattern: str) -> pd.DataFrame:
    files = glob.glob(pattern)
    if not files:
        return pd.DataFrame()
    df = pd.read_csv(files[0])
    ts_col = "timestamp" if "timestamp" in df.columns else df.columns[0]
    ts = df[ts_col]
    df["timestamp"] = pd.to_datetime(ts, unit="ms", utc=True) if ts.iloc[0] > 1e11 else pd.to_datetime(ts, utc=True)
    close_col = "close" if "close" in df.columns else ("Close" if "Close" in df.columns else df.columns[4])
    df["close"] = pd.to_numeric(df[close_col], errors="coerce")
    return df.dropna(subset=["close"]).sort_values("timestamp").reset_index(drop=True)


def download_cftc_gold_cot() -> pd.DataFrame:
    """Télécharge l'historique complet 2015-2026 du rapport CFTC Commitment of Traders (COMEX Gold 088691)."""
    dfs = []
    logger.info("Téléchargement des rapports hebdomadaires CFTC COT (2015-2026)...")
    for yr in range(2015, 2027):
        url = f"https://www.cftc.gov/files/dea/history/deacot{yr}.zip"
        z_name = f"cot_{yr}.zip"
        cmd = f'curl -s -L "{url}" -o {z_name}'
        try:
            subprocess.check_call(cmd, shell=True)
            with zipfile.ZipFile(z_name) as z:
                fname = z.namelist()[0]
                with z.open(fname) as f:
                    df = pd.read_csv(f, low_memory=False)
                    gold_df = df[df.iloc[:, 0].astype(str).str.contains("GOLD", case=False, na=False)].copy()
                    dfs.append(gold_df)
        except Exception as e:
            logger.warning(f"Erreur chargement CFTC COT {yr}: {e}")

    if not dfs:
        return pd.DataFrame()

    full = pd.concat(dfs, ignore_index=True)
    
    # Identification des colonnes CFTC
    date_col = [c for c in full.columns if "YYYY-MM-DD" in c or "Form YYYY-MM-DD" in c][0]
    long_col = [c for c in full.columns if "Noncommercial Positions-Long" in c][0]
    short_col = [c for c in full.columns if "Noncommercial Positions-Short" in c][0]
    oi_col = [c for c in full.columns if "Open Interest" in c][0]

    full["date_tuesday"] = pd.to_datetime(full[date_col], utc=True)
    full["cot_long"] = pd.to_numeric(full[long_col], errors="coerce")
    full["cot_short"] = pd.to_numeric(full[short_col], errors="coerce")
    full["cot_open_interest"] = pd.to_numeric(full[oi_col], errors="coerce")

    # Calcul des variables de positionnement net spéculatif
    full["cot_net_spec"] = full["cot_long"] - full["cot_short"]
    full["cot_net_spec_ratio"] = full["cot_net_spec"] / (full["cot_open_interest"] + 1e-9)

    # ALIGNEMENT CAUSAL STRICT : les données du mardi sont publiées le vendredi -> utilisables à partir du LUNDI suivant
    # Lag de 6 jours calendaires par rapport au mardi (Mardi + 6j = Lundi suivant)
    full["date_usable"] = full["date_tuesday"] + pd.Timedelta(days=6)

    res = full[["date_usable", "cot_net_spec", "cot_net_spec_ratio"]].dropna().sort_values("date_usable").reset_index(drop=True)
    res = res[~res["date_usable"].duplicated(keep="last")]
    logger.info(f"Série CFTC Gold COT construite : {len(res)} semaines historiques de 2015 à 2026.")
    return res


def download_gld_etf_flows() -> pd.DataFrame:
    """Télécharge les données quotidiennes du GLD ETF via Yahoo Finance API."""
    logger.info("Téléchargement de l'historique daily du GLD ETF...")
    url = "https://query1.finance.yahoo.com/v8/finance/chart/GLD?range=10y&interval=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        result = data["chart"]["result"][0]
        ts = result["timestamp"]
        quote = result["indicators"]["quote"][0]
        df = pd.DataFrame({
            "timestamp": pd.to_datetime(ts, unit="s", utc=True),
            "gld_close": quote["close"],
            "gld_volume": quote["volume"]
        })
        df["gld_dollar_volume"] = df["gld_close"] * df["gld_volume"]
        df["date_usable"] = df["timestamp"].dt.floor("D") + pd.Timedelta(days=1) # Lag 1 jour pour pas de lookahead
        res = df[["date_usable", "gld_dollar_volume"]].dropna().sort_values("date_usable").reset_index(drop=True)
        res = res[~res["date_usable"].duplicated(keep="last")]
        logger.info(f"Série GLD ETF Flows construite : {len(res)} barres quotidiennes.")
        return res
    except Exception as e:
        logger.error(f"Erreur téléchargement GLD ETF: {e}")
        return pd.DataFrame()


def compute_adf_statistic(series: np.ndarray, max_lags: int = 4) -> float:
    """Calcul de la statistique t de Dickey-Fuller Augmentée (ADF) en NumPy pur."""
    y = np.asarray(series)
    dy = np.diff(y)
    n = len(dy)
    if n < 30:
        return 0.0

    y_lag = y[:-1]
    X_list = [np.ones(n - max_lags), y_lag[max_lags:]]
    for i in range(1, max_lags + 1):
        X_list.append(dy[max_lags - i : n - i])

    X = np.column_stack(X_list)
    Y = dy[max_lags:]

    try:
        XtX_inv = np.linalg.inv(X.T @ X)
        beta = XtX_inv @ (X.T @ Y)
        res = Y - X @ beta
        sigma_sq = (res.T @ res) / (len(Y) - X.shape[1])
        var_cov = sigma_sq * XtX_inv
        se_gamma = np.sqrt(max(1e-12, var_cov[1, 1]))
        t_stat = beta[1] / se_gamma
        return float(t_stat)
    except Exception:
        return 0.0


def compute_engle_granger_adf(y_series: np.ndarray, x_series: np.ndarray) -> float:
    """Test de Cointégration d'Engle-Granger en NumPy pur."""
    N = len(y_series)
    X = np.column_stack([np.ones(N), x_series])
    try:
        beta = np.linalg.inv(X.T @ X) @ (X.T @ y_series)
        res = y_series - X @ beta
        return compute_adf_statistic(res)
    except Exception:
        return 0.0


def compute_newey_west_tstat(feature: pd.Series, target: pd.Series, max_lags: int) -> tuple[float, float, float]:
    """Calcul OLS bivarié + t-stat Newey-West HAC en NumPy pur sans dépendances externes."""
    df = pd.DataFrame({"x": feature, "y": target}).dropna()
    if len(df) < 30:
        return 0.0, 0.0, 1.0

    x = df["x"].values
    y = df["y"].values
    N = len(x)

    X = np.column_stack([np.ones(N), x])

    try:
        XtX_inv = np.linalg.inv(X.T @ X)
        beta_vec = XtX_inv @ (X.T @ y)
        beta_x = float(beta_vec[1])

        residuals = y - X @ beta_vec
        V = X * residuals[:, np.newaxis]

        Gamma_0 = V.T @ V
        S = Gamma_0.copy()

        for l in range(1, max_lags + 1):
            weight = 1.0 - (l / (max_lags + 1.0))
            Gamma_l = V[l:].T @ V[:-l]
            S += weight * (Gamma_l + Gamma_l.T)

        var_cov = XtX_inv @ S @ XtX_inv
        se_beta_x = np.sqrt(max(1e-12, var_cov[1, 1]))

        t_stat = beta_x / se_beta_x
        p_val = float(2.0 * (1.0 - stats.norm.cdf(abs(t_stat))))

        return beta_x, float(t_stat), p_val
    except Exception:
        return 0.0, 0.0, 1.0


def main() -> None:
    logger.info("=== RECHERCHE DE FEATURES DE POSITIONNEMENT (CFTC COT & GLD ETF FLOWS) ===")

    cot_df = download_cftc_gold_cot()
    gld_df = download_gld_etf_flows()
    gold_d1 = load_dukascopy_gold("data/raw_dukascopy/*d1*.csv")
    gold_h4 = load_dukascopy_gold("data/raw_dukascopy/*h4*.csv")

    # Merge causale des features de positionnement sur Gold D1
    gold_d1["date"] = pd.to_datetime(gold_d1["timestamp"], utc=True).dt.floor("D")
    
    # Forward fill des données hebdomadaires COT et daily GLD
    df_d1 = gold_d1.merge(cot_df, left_on="date", right_on="date_usable", how="left")
    df_d1 = df_d1.merge(gld_df, left_on="date", right_on="date_usable", how="left")
    
    df_d1["cot_net_spec"] = df_d1["cot_net_spec"].ffill()
    df_d1["cot_net_spec_ratio"] = df_d1["cot_net_spec_ratio"].ffill()
    df_d1["gld_dollar_volume"] = df_d1["gld_dollar_volume"].ffill()

    # Features de positionnement (Niveaux & Variations)
    df_d1["feat_pos_cot_net_spec_level"] = df_d1["cot_net_spec"]
    df_d1["feat_pos_cot_net_spec_change_1w"] = df_d1["cot_net_spec"].diff(5)
    df_d1["feat_pos_cot_net_spec_change_4w"] = df_d1["cot_net_spec"].diff(20)
    df_d1["feat_pos_cot_spec_ratio_level"] = df_d1["cot_net_spec_ratio"]

    df_d1["feat_pos_gld_volume_level"] = df_d1["gld_dollar_volume"]
    df_d1["feat_pos_gld_volume_change_1d"] = df_d1["gld_dollar_volume"].diff(1)
    df_d1["feat_pos_gld_volume_change_5d"] = df_d1["gld_dollar_volume"].diff(5)

    pos_feat_cols = [c for c in df_d1.columns if c.startswith("feat_pos_")]

    # 1. VERIFICATION DE STATIONNARITÉ ADF ET COINTÉGRATION DES NIVEAUX BRUTS
    logger.info("1. Tests de stationnarité ADF sur les 7 caractéristiques de positionnement...")
    adf_results = {}
    adf_crit_5pct = -2.86

    for col in pos_feat_cols:
        vals = df_d1[col].dropna().values
        adf_stat = compute_adf_statistic(vals)
        is_stat = adf_stat < adf_crit_5pct
        
        # Si non-stationnaire (niveau brut I(1)), calcul du test de cointégration Engle-Granger vs Gold close
        eg_stat = 0.0
        is_coint = False
        if not is_stat:
            sub_df = df_d1[["close", col]].dropna()
            eg_stat = compute_engle_granger_adf(sub_df["close"].values, sub_df[col].values)
            is_coint = eg_stat < -3.34

        adf_results[col] = {
            "adf_tstat": adf_stat,
            "is_stationary": is_stat,
            "eg_tstat": eg_stat,
            "is_cointegrated": is_coint
        }
        logger.info(f"Feature {col:32s} | ADF = {adf_stat:+.2f} ({'I(0) Stationnaire' if is_stat else 'I(1) Non-Stationnaire'}) | Engle-Granger ADF = {eg_stat:+.2f} ({'Cointégré' if is_coint else 'NON Cointégré'})")

    # 2. EXECUTION DES TESTS STATISTIQUES SUR GOLD D1 & H4
    logger.info("2. Exécution des tests de significativité (Newey-West HAC & Spearman IC)...")

    # Alignement temporel sur H4
    gold_h4["date"] = pd.to_datetime(gold_h4["timestamp"], utc=True).dt.floor("D")
    df_h4 = gold_h4.merge(cot_df, left_on="date", right_on="date_usable", how="left")
    df_h4 = df_h4.merge(gld_df, left_on="date", right_on="date_usable", how="left")
    
    for c in ["cot_net_spec", "cot_net_spec_ratio", "gld_dollar_volume"]:
        df_h4[c] = df_h4[c].ffill()

    df_h4["feat_pos_cot_net_spec_level"] = df_h4["cot_net_spec"]
    df_h4["feat_pos_cot_net_spec_change_1w"] = df_h4["cot_net_spec"].diff(30)
    df_h4["feat_pos_cot_net_spec_change_4w"] = df_h4["cot_net_spec"].diff(120)
    df_h4["feat_pos_cot_spec_ratio_level"] = df_h4["cot_net_spec_ratio"]

    df_h4["feat_pos_gld_volume_level"] = df_h4["gld_dollar_volume"]
    df_h4["feat_pos_gld_volume_change_1d"] = df_h4["gld_dollar_volume"].diff(6)
    df_h4["feat_pos_gld_volume_change_5d"] = df_h4["gld_dollar_volume"].diff(30)

    all_experiments = []

    def evaluate_dataset(df_target, tf_name, horizons):
        for H in horizons:
            df_target[f"target_{H}"] = (df_target["close"].shift(-H) - df_target["close"]) / df_target["close"]
            for col in pos_feat_cols:
                if col not in df_target.columns: continue
                
                df_pair = df_target[[col, f"target_{H}"]].dropna()
                if len(df_pair) < 30:
                    continue

                meta = adf_results[col]
                is_spurious = (not meta["is_stationary"]) and (not meta["is_cointegrated"])

                beta, t_stat, p_val = compute_newey_west_tstat(df_pair[col], df_pair[f"target_{H}"], max_lags=H)
                ic_val, _ = stats.spearmanr(df_pair[col], df_pair[f"target_{H}"])
                ic = float(ic_val) if not np.isnan(ic_val) else 0.0

                all_experiments.append({
                    "asset": "Gold",
                    "tf": tf_name,
                    "horizon": H,
                    "feature": col,
                    "ic": float(ic) if not np.isnan(ic) else 0.0,
                    "beta": beta,
                    "t_stat": t_stat if not is_spurious else 0.0,
                    "t_stat_raw": t_stat,
                    "p_raw": p_val if not is_spurious else 1.0,
                    "p_raw_unfiltered": p_val,
                    "abs_t": abs(t_stat) if not is_spurious else 0.0,
                    "is_stationary": meta["is_stationary"],
                    "is_spurious": is_spurious,
                })

    evaluate_dataset(df_d1, "D1", [1, 5])
    evaluate_dataset(df_h4, "H4", [1, 6])

    # CONTRÔLE DES TESTS MULTIPLES SUR LA FAMILLE DE POSITIONNEMENT
    N_pos = len(all_experiments)
    alpha_bonf_pos = 0.05 / N_pos
    bonf_t_pos = stats.norm.ppf(1 - alpha_bonf_pos / 2)

    # Tri par p_raw pour Benjamini-Hochberg
    sorted_experiments = sorted(all_experiments, key=lambda x: x["p_raw"])
    for rank_idx, item in enumerate(sorted_experiments, start=1):
        bh_crit = (rank_idx / N_pos) * 0.05
        item["bh_crit"] = bh_crit
        item["sig_bh"] = item["p_raw"] <= bh_crit
        item["sig_bonf"] = item["p_raw"] <= alpha_bonf_pos

    sig_raw = [x for x in sorted_experiments if abs(x["t_stat_raw"]) >= 2.0 and not x["is_spurious"]]
    sig_bh = [x for x in sorted_experiments if x["sig_bh"]]
    sig_bonf = [x for x in sorted_experiments if x["sig_bonf"]]
    spurious_items = [x for x in sorted_experiments if x["is_spurious"]]

    print("\n=========================================================================================")
    print(f"      SYNTHÈSE DE LA RECHERCHE SUR LE POSITIONNEMENT (N_pos = {N_pos})")
    print("=========================================================================================\n")
    print(f"1. Nombre total de paires évaluées (Feature x Horizon x TF) : {N_pos}")
    print(f"2. Features I(1) non-stationnaires identifiées : {[k for k, v in adf_results.items() if not v['is_stationary']]}")
    print(f"3. Features I(1) non-cointégrées rejetées pour Spurious Regression : {len(spurious_items)}")
    print(f"4. Paires significatives brutes (|t| >= 2.0 valides) : {len(sig_raw)} ({len(sig_raw)/N_pos*100:.1f}%)")
    print(f"5. Paires significatives Benjamini-Hochberg (FDR q=0.05) : {len(sig_bh)} ({len(sig_bh)/N_pos*100:.1f}%)")
    print(f"6. Paires significatives Bonferroni (|t| >= {bonf_t_pos:.2f})       : {len(sig_bonf)} ({len(sig_bonf)/N_pos*100:.1f}%)\n")

    print("DÉTAIL DE TOUTES LES FEATURES DE POSITIONNEMENT ÉVALUÉES :")
    for x in sorted_experiments:
        sp_flag = " [❌ REJETÉ SPURIOUS I(1)]" if x["is_spurious"] else ""
        print(f"  [Gold {x['tf']} H={x['horizon']}] {x['feature']:35s} | IC = {x['ic']:+6.3f} | t-stat = {x['t_stat_raw']:+6.2f} | p_raw = {x['p_raw_unfiltered']:.4f} | BH q=0.05 = {'✅ SIG' if x['sig_bh'] else '❌ NOT SIG'}{sp_flag}")

    # GENERATION DU RAPPORT MARKDOWN
    os.makedirs("docs/research", exist_ok=True)
    with open(OUTPUT_DOC, "w", encoding="utf-8") as f:
        f.write("# RAPPORT QUANTITATIF DE RECHERCHE DE FEATURES DE POSITIONNEMENT (CFTC COT & GLD ETF)\n\n")
        f.write(f"**Nombre Total d'Hypothèses Évaluées dans la Famille ($N_{{\\text{{pos}}}}$)** : **`{N_pos}`**\n")
        f.write(f"**Seuil de Bonferroni Ajusté sur la Famille** : $\\alpha = {alpha_bonf_pos:.6f}$ ($|t| \\ge {bonf_t_pos:.3f}$)\n")
        f.write(f"**Seuil Benjamini-Hochberg (FDR $q=0.05$)** : Taux de fausses découvertes contrôlé à 5%\n\n")

        f.write("## 1. Audit de Stationnarité ADF Préalable (Règle ADR 0030)\n\n")
        f.write("| Feature Name | Description | Nature de la Série | ADF t-stat | Engle-Granger ADF | Statut Économétrique |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for col, meta in adf_results.items():
            st_desc = "I(0) Stationnaire" if meta["is_stationary"] else "I(1) Non-Stationnaire"
            coint_desc = "Non Cointégré (Rejet Spurious)" if (not meta["is_stationary"] and not meta["is_cointegrated"]) else ("Cointégré" if meta["is_cointegrated"] else "N/A")
            f.write(f"| `{col}` | Positionnement / Flux | {st_desc} | **{meta['adf_tstat']:+.2f}** | {meta['eg_tstat']:+.2f} | **{coint_desc}** |\n")

        f.write("\n\n## 2. Résultats des Tests de Significativité (Newey-West & Spearman IC)\n\n")
        f.write("| Timeframe | Horizon H | Feature Name | Spearman IC | t-stat Newey-West | p-valeur brute | BH (q=0.05) | Bonferroni |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for x in sorted_experiments:
            st_bh = "✅ SIG" if x["sig_bh"] else "❌ NOT SIG"
            st_bonf = "✅ SIG" if x["sig_bonf"] else "❌ NOT SIG"
            if x["is_spurious"]:
                st_bh = "❌ SPURIOUS I(1)"
                st_bonf = "❌ SPURIOUS I(1)"
            f.write(f"| {x['tf']} | H={x['horizon']} | `{x['feature']}` | {x['ic']:+.4f} | **{x['t_stat_raw']:+.2f}** | {x['p_raw_unfiltered']:.4f} | {st_bh} | {st_bonf} |\n")

        f.write("\n\n## 3. CONCLUSION ET DÉCISION FINAL DE LA DERNIÈRE PISTE NON FALSIFIÉE\n\n")
        if len(sig_bh) > 0:
            f.write(f"**{len(sig_bh)} features de positionnement sont statistiquement significatives après correction pour tests multiples**.\n")
        else:
            f.write("**0 feature de positionnement (CFTC COT Net Speculative Position & GLD ETF Flows) ne franchit la correction pour tests multiples Benjamini-Hochberg FDR q=0.05 ou le filtre de régression fallacieuse**.\n")

    logger.info(f"Rapport d'analyse enregistré dans {OUTPUT_DOC}")


if __name__ == "__main__":
    main()
