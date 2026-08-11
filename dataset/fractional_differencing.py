#!/usr/bin/env python3
"""
Fractional Differencing Analysis & Optimal d* Search Tool
====================================================================

This script performs Fixed-width Window Fractional Differentiation (FFD) on
volatility-normalized market data in `dataset/` following Marcos López de Prado's
*Advances in Financial Machine Learning* (Chapter 5).

Key Steps:
1. Load Normalized Data (`norm_price_index`) from `dataset/EURUSD_M30_volatility_normalized_bars.csv`
   and `dataset/MT5CurrencyHistory.h5`.
2. Grid Search candidate differencing parameters d in [0.0, 1.0] with step 0.01.
3. Compute Fixed-width Window Fractional Differentiation (FFD) series for each d using weight threshold tau = 1e-4.
4. Perform Augmented Dickey-Fuller (ADF) stationarity test on each transformed series.
5. Optimization Algorithm: Select optimal d* as min { d in [0.0, 1.0] | p_ADF <= 0.05 }, preserving
   maximum historical memory while achieving stationarity.
6. Export transformed series to CSV and HDF5, record change log, and generate diagnostic plots.

References:
    - López de Prado, M. (2018). *Advances in Financial Machine Learning*. John Wiley & Sons.
"""

import os
import sys
import argparse
import csv
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import h5py
import scipy.stats as stats
import matplotlib.pyplot as plt
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller

# Path definitions
SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parent
DEFAULT_HDF5_PATH = SCRIPT_DIR / "MT5CurrencyHistory.h5"
DEFAULT_CHANGE_LOG_PATH = SCRIPT_DIR / "MT5CurrencyHistory_change_log.csv"


# ==============================================================================
# 1. AUDIT LOGGING
# ==============================================================================

def get_git_username() -> str:
    """Get local git username for audit logging."""
    try:
        res = subprocess.run(["git", "config", "user.name"], stdout=subprocess.PIPE, text=True, check=True)
        name = res.stdout.strip()
        return name if name else "Unknown"
    except Exception:
        return "Unknown"


def append_change_log(hdf5_path: Path, action: str, symbol: str, timeframe: str = "M30", start_time: str = "", end_time: str = ""):
    """Record an audit entry in the CSV change log."""
    csv_path = hdf5_path.with_name(f"{hdf5_path.stem}_change_log.csv")
    is_new = not csv_path.exists()
    columns = ["LOG_TIME", "ACTION", "BY", "SYMBOL", "TIMEFRAME", "TCST", "TCET"]
    log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    by_user = get_git_username()

    row = [log_time, action, by_user, symbol, timeframe, str(start_time), str(end_time)]

    with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(columns)
        writer.writerow(row)
    print(f"<LOG> Logged '{action}' for {symbol} ({timeframe}) in {csv_path.name}.", flush=True)


# ==============================================================================
# 2. FRACTIONAL DIFFERENTIATION (FFD) ALGORITHMS
# ==============================================================================

def get_ffd_weights(d: float, thres: float = 1e-4) -> np.ndarray:
    """
    Compute weights for Fixed-width Window Fractional Differentiation (FFD).

    Parameters:
        d (float): Fractional differencing parameter (0.0 <= d <= 1.0).
        thres (float): Cutoff threshold for dropping insignificant weights.

    Returns:
        np.ndarray: Weight vector [w_0, w_1, ..., w_{l-1}].
    """
    w = [1.0]
    k = 1
    while True:
        w_k = -w[-1] / k * (d - k + 1)
        if abs(w_k) < thres:
            break
        w.append(w_k)
        k += 1
    return np.array(w, dtype=float)


def frac_diff_ffd(series: pd.Series, d: float, thres: float = 1e-4) -> pd.Series:
    """
    Apply Fixed-width Window Fractional Differentiation (FFD) to a 1D Pandas Series.

    Parameters:
        series (pd.Series): Raw or normalized price index series.
        d (float): Fractional differencing parameter.
        thres (float): Cutoff threshold for weights.

    Returns:
        pd.Series: Fractionally differenced time series.
    """
    w = get_ffd_weights(d, thres)
    l = len(w)
    s_vals = series.values
    
    if l > len(series):
        return pd.Series(np.nan, index=series.index)
        
    res = np.empty(len(series), dtype=float)
    res[:l-1] = np.nan
    res[l-1:] = np.convolve(s_vals, w, mode="valid")
    return pd.Series(res, index=series.index)


# ==============================================================================
# 3. OPTIMIZATION ALGORITHM FOR MINIMUM d*
# ==============================================================================

def grid_search_minimum_d(
    series: pd.Series,
    series_name: str = "Normalized Price Index",
    d_min: float = 0.0,
    d_max: float = 1.0,
    d_step: float = 0.01,
    p_threshold: float = 0.05,
    thres: float = 1e-4,
) -> tuple[float, pd.DataFrame]:
    """
    Grid search candidate d values to find optimal d* = min { d | p_ADF <= p_threshold }.

    Parameters:
        series (pd.Series): Time series to analyze (must be non-stationary price level).
        series_name (str): Label for logging.
        d_min (float): Minimum candidate d.
        d_max (float): Maximum candidate d.
        d_step (float): Step size for d sampling.
        p_threshold (float): ADF p-value significance threshold (default: 0.05).
        thres (float): Weight truncation threshold for FFD.

    Returns:
        tuple[float, pd.DataFrame]: Optimal d* and complete grid search DataFrame.
    """
    series_clean = series.dropna()
    d_candidates = np.round(np.arange(d_min, d_max + d_step / 2.0, d_step), 2)
    results = []

    print(f"\n<SEARCH> Running Fractional Differencing Grid Search for '{series_name}' across d in [{d_min:.2f}, {d_max:.2f}] (step={d_step:.2f})...", flush=True)

    for d in d_candidates:
        w = get_ffd_weights(d, thres=thres)
        l = len(w)
        
        ffd_s = frac_diff_ffd(series_clean, d=d, thres=thres).dropna()
        if len(ffd_s) < 20:
            results.append({
                "d": d,
                "adf_stat": np.nan,
                "p_val": 1.0,
                "corr_with_orig": np.nan,
                "memory_lost": np.nan,
                "weight_len": l,
                "n_obs": len(ffd_s),
                "is_stationary": False,
            })
            continue

        # Perform fast and accurate ADF test with autolag='AIC' or maxlag=1
        adf_res = adfuller(ffd_s, autolag="AIC") if len(series_clean) <= 2000 else adfuller(ffd_s, maxlag=1, autolag=None)
        adf_stat = float(adf_res[0])
        p_val = float(adf_res[1])

        # Pearson correlation with original series on overlapping indices
        overlap_orig = series_clean.loc[ffd_s.index]
        corr = float(np.corrcoef(overlap_orig, ffd_s)[0, 1]) if len(ffd_s) > 1 else np.nan
        mem_lost = 1.0 - corr if not np.isnan(corr) else np.nan
        is_stat = (p_val <= p_threshold)

        results.append({
            "d": d,
            "adf_stat": adf_stat,
            "p_val": p_val,
            "corr_with_orig": corr,
            "memory_lost": mem_lost,
            "weight_len": l,
            "n_obs": len(ffd_s),
            "is_stationary": is_stat,
        })

    grid_df = pd.DataFrame(results)
    
    # Find minimum d* where p_val <= p_threshold
    stationary_rows = grid_df[grid_df["is_stationary"]]
    if len(stationary_rows) > 0:
        opt_d = float(stationary_rows.iloc[0]["d"])
    else:
        opt_d = float(d_max)

    opt_row = grid_df[grid_df["d"] == opt_d].iloc[0]
    print(f"<OPTIMAL> Minimum d* for '{series_name}': {opt_d:.2f}", flush=True)
    print(f"          ADF Statistic : {opt_row['adf_stat']:.4f}", flush=True)
    print(f"          ADF p-value   : {opt_row['p_val']:.5f} (Threshold <= {p_threshold})", flush=True)
    print(f"          Pearson Corr  : {opt_row['corr_with_orig']:.4f} ({opt_row['corr_with_orig']*100:.2f}% Memory Retained)", flush=True)
    print(f"          Memory Lost   : {opt_row['memory_lost']:.4f} ({opt_row['memory_lost']*100:.2f}%)", flush=True)
    print(f"          FFD Window (l): {opt_row['weight_len']} bars", flush=True)

    return opt_d, grid_df


# ==============================================================================
# 4. DIAGNOSTIC PLOTTING (6-PANEL ANALYSIS)
# ==============================================================================

def generate_fractional_differencing_plots(
    grid_df: pd.DataFrame,
    opt_d: float,
    orig_series: pd.Series,
    ffd_opt_series: pd.Series,
    ffd_1_series: pd.Series,
    symbol: str,
    output_path: Path,
    series_label: str = "Volatility-Normalized Price Index",
):
    """
    Generate a comprehensive 6-panel diagnostic plot:
    1. Grid Search ADF p-value vs d with threshold p <= 0.05
    2. ADF Statistic vs d
    3. Memory Retention (Correlation) & Memory Loss vs d
    4. Time-Series Overlay: Original vs FFD(d*) vs First Diff (d=1.0)
    5. Histogram & Fitted Normal Overlay of FFD(d*)
    6. Q-Q Plot of FFD(d*) vs Gaussian Distribution
    """
    plt.style.use("seaborn-v0_8-darkgrid" if "seaborn-v0_8-darkgrid" in plt.style.available else "default")
    fig, axes = plt.subplots(3, 2, figsize=(16, 15))
    fig.suptitle(
        f"{symbol} M30 - Fractional Differencing Analysis & Optimization (Minimum d*)\n"
        f"Target Series: {series_label} | Optimal d* = {opt_d:.2f}",
        fontsize=16,
        fontweight="bold",
        y=0.98,
    )

    ds = grid_df["d"].values
    p_vals = grid_df["p_val"].values
    adf_stats = grid_df["adf_stat"].values
    corrs = grid_df["corr_with_orig"].values

    opt_row = grid_df[grid_df["d"] == opt_d].iloc[0]

    # --- Panel 1: Grid Search p-value vs d ---
    ax1 = axes[0, 0]
    ax1.plot(ds, p_vals, color="#1f77b4", linewidth=2.5, label="ADF p-value")
    ax1.axhline(0.05, color="#d62728", linestyle="--", linewidth=1.8, label="Significance Threshold (p = 0.05)")
    ax1.axvline(opt_d, color="#2ca02c", linestyle=":", linewidth=2, label=f"Minimum d* = {opt_d:.2f}")
    ax1.scatter([opt_d], [opt_row["p_val"]], color="#2ca02c", s=100, zorder=5)
    ax1.set_title("1. Augmented Dickey-Fuller (ADF) p-value vs. Candidate d", fontsize=12, fontweight="bold")
    ax1.set_xlabel("Differencing Parameter (d)", fontsize=10)
    ax1.set_ylabel("ADF p-value", fontsize=10)
    ax1.set_ylim(-0.02, 1.02)
    ax1.legend(loc="upper right", frameon=True)
    ax1.annotate(
        f"Optimal d* = {opt_d:.2f}\np = {opt_row['p_val']:.4f}",
        xy=(opt_d, opt_row["p_val"]),
        xytext=(opt_d + 0.08, opt_row["p_val"] + 0.15),
        arrowprops=dict(facecolor="#2ca02c", shrink=0.08, width=1.5, headwidth=6),
        fontsize=10,
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#e8f5e9", edgecolor="#2ca02c"),
    )

    # --- Panel 2: ADF Statistic vs d ---
    ax2 = axes[0, 1]
    ax2.plot(ds, adf_stats, color="#ff7f0e", linewidth=2.5, label="ADF t-Statistic")
    ax2.axvline(opt_d, color="#2ca02c", linestyle=":", linewidth=2, label=f"Minimum d* = {opt_d:.2f}")
    ax2.scatter([opt_d], [opt_row["adf_stat"]], color="#2ca02c", s=100, zorder=5)
    ax2.set_title("2. ADF Test Statistic (t-stat) vs. Candidate d", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Differencing Parameter (d)", fontsize=10)
    ax2.set_ylabel("ADF t-Statistic", fontsize=10)
    ax2.legend(loc="upper left", frameon=True)

    # --- Panel 3: Memory Retention & Memory Loss vs d ---
    ax3 = axes[1, 0]
    ax3.plot(ds, corrs, color="#2ca02c", linewidth=2.5, label="Pearson Corr (Memory Retained)")
    ax3.plot(ds, 1.0 - corrs, color="#d62728", linewidth=2.0, linestyle="--", label="Memory Lost (1 - Corr)")
    ax3.axvline(opt_d, color="#9467bd", linestyle=":", linewidth=2, label=f"d* = {opt_d:.2f}")
    ax3.scatter([opt_d], [opt_row["corr_with_orig"]], color="#2ca02c", s=100, zorder=5)
    ax3.set_title("3. Memory Retention vs. Stationary Differencing Trade-off", fontsize=12, fontweight="bold")
    ax3.set_xlabel("Differencing Parameter (d)", fontsize=10)
    ax3.set_ylabel("Correlation / Proportion", fontsize=10)
    ax3.set_ylim(-0.02, 1.05)
    ax3.legend(loc="center right", frameon=True)
    ax3.annotate(
        f"Memory Retained: {opt_row['corr_with_orig']*100:.1f}%",
        xy=(opt_d, opt_row["corr_with_orig"]),
        xytext=(opt_d - 0.25, opt_row["corr_with_orig"] - 0.2),
        arrowprops=dict(facecolor="#2ca02c", shrink=0.08, width=1.5, headwidth=6),
        fontsize=10,
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#ffffff", edgecolor="#2ca02c"),
    )

    # --- Panel 4: Comparative Time Series Overlay ---
    ax4 = axes[1, 1]
    valid_idx = ffd_opt_series.dropna().index
    orig_sub = orig_series.loc[valid_idx]
    ffd_opt_sub = ffd_opt_series.loc[valid_idx]
    ffd_1_sub = ffd_1_series.loc[valid_idx]

    # Normalize for comparison plot
    s_orig_norm = (orig_sub - orig_sub.mean()) / orig_sub.std()
    s_ffd_norm = (ffd_opt_sub - ffd_opt_sub.mean()) / ffd_opt_sub.std()
    s_diff_norm = (ffd_1_sub - ffd_1_sub.mean()) / ffd_1_sub.std()

    ax4.plot(s_orig_norm.values, color="#7f7f7f", alpha=0.5, linewidth=1.2, label=f"Original (d=0.0)")
    ax4.plot(s_ffd_norm.values, color="#1f77b4", linewidth=1.5, alpha=0.9, label=f"FFD Optimal (d*={opt_d:.2f})")
    ax4.plot(s_diff_norm.values, color="#d62728", linewidth=1.0, alpha=0.4, label=f"First Difference (d=1.0)")
    ax4.set_title("4. Normalized Time-Series Comparison (Standardized Units)", fontsize=12, fontweight="bold")
    ax4.set_xlabel("Bar Index", fontsize=10)
    ax4.set_ylabel("Standardized Value (Z-Score)", fontsize=10)
    ax4.legend(loc="upper right", frameon=True)

    # --- Panel 5: Distribution Histogram & Gaussian Overlay ---
    ax5 = axes[2, 0]
    clean_ffd = ffd_opt_series.dropna().values
    mu, std = stats.norm.fit(clean_ffd)
    n_bins = 50
    counts, bins, _ = ax5.hist(clean_ffd, bins=n_bins, density=True, alpha=0.6, color="#1f77b4", edgecolor="black", label=f"FFD(d*={opt_d:.2f}) Distribution")
    x_pdf = np.linspace(bins.min(), bins.max(), 300)
    pdf = stats.norm.pdf(x_pdf, mu, std)
    ax5.plot(x_pdf, pdf, "r-", linewidth=2.0, label=f"Gaussian Fit N({mu:.3f}, {std:.3f}^2)")
    
    # Calculate Jarque-Bera
    jb_stat, jb_pval = stats.jarque_bera(clean_ffd)
    skew = stats.skew(clean_ffd)
    kurt = stats.kurtosis(clean_ffd)

    ax5.set_title(f"5. FFD(d*={opt_d:.2f}) Value Distribution vs. Gaussian", fontsize=12, fontweight="bold")
    ax5.set_xlabel("FFD Transformed Value", fontsize=10)
    ax5.set_ylabel("Density", fontsize=10)
    ax5.legend(loc="upper right", frameon=True)
    ax5.text(
        0.03, 0.70,
        f"Skewness: {skew:.4f}\nExcess Kurt: {kurt:.4f}\nJB Stat: {jb_stat:.2f}\nJB p-val: {jb_pval:.2e}",
        transform=ax5.transAxes,
        fontsize=9,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#ffffff", alpha=0.8, edgecolor="#1f77b4"),
    )

    # --- Panel 6: Q-Q Plot ---
    ax6 = axes[2, 1]
    (osm, osr), (slope, intercept, r) = stats.probplot(clean_ffd, dist="norm", plot=ax6)
    ax6.get_lines()[0].set_markerfacecolor("#1f77b4")
    ax6.get_lines()[0].set_markeredgecolor("#1f77b4")
    ax6.get_lines()[0].set_markersize(4)
    ax6.get_lines()[1].set_color("#d62728")
    ax6.get_lines()[1].set_linewidth(2)
    ax6.set_title(f"6. Q-Q Plot for FFD(d*={opt_d:.2f}) Series", fontsize=12, fontweight="bold")
    ax6.set_xlabel("Theoretical Quantiles", fontsize=10)
    ax6.set_ylabel("Sample Quantiles", fontsize=10)

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"<PLOT> Saved 6-panel fractional differencing plot to: {output_path.name}", flush=True)


# ==============================================================================
# 5. MAIN PROCESSING WORKFLOW
# ==============================================================================

def run_fractional_differencing_analysis(
    hdf5_path: Path,
    symbol: str = "EURUSD",
    d_min: float = 0.0,
    d_max: float = 1.0,
    d_step: float = 0.01,
    p_threshold: float = 0.05,
    export_csv: bool = True,
    generate_plot: bool = True,
):
    """Run full fractional differencing pipeline on dataset files."""
    csv_norm_path = SCRIPT_DIR / f"{symbol}_M30_volatility_normalized_bars.csv"

    if not csv_norm_path.exists():
        raise FileNotFoundError(f"Normalized CSV data file not found at: {csv_norm_path}")

    # 1. Load Normalized Data
    norm_df = pd.read_csv(csv_norm_path)
    if "norm_price_index" not in norm_df.columns:
        raise KeyError("Column 'norm_price_index' not found in normalized CSV file.")

    series_norm = norm_df["norm_price_index"]
    series_close = norm_df["close"]

    # 2. Optimization Algorithm for Minimum d* on Volatility-Normalized Price Index
    opt_d_norm, grid_df_norm = grid_search_minimum_d(
        series=series_norm,
        series_name="Volatility-Normalized Price Index",
        d_min=d_min,
        d_max=d_max,
        d_step=d_step,
        p_threshold=p_threshold,
    )

    # 3. Comparative Grid Search on Raw Volume Bar Close
    opt_d_close, grid_df_close = grid_search_minimum_d(
        series=series_close,
        series_name="Volume Bars (Raw Close)",
        d_min=d_min,
        d_max=d_max,
        d_step=d_step,
        p_threshold=p_threshold,
    )

    # 4. Comparative Grid Search on M30 Raw Time Bars (if available in HDF5)
    opt_d_m30 = np.nan
    grid_df_m30 = None
    if hdf5_path.exists():
        try:
            with h5py.File(hdf5_path, "r") as f:
                ds_path = f"TIMEFRAME/M30/{symbol}"
                if ds_path in f:
                    arr = f[ds_path][:]
                    m30_df = pd.DataFrame({n: arr[n] for n in arr.dtype.names})
                    opt_d_m30, grid_df_m30 = grid_search_minimum_d(
                        series=m30_df["close"],
                        series_name="M30 Time Bars (Raw Close)",
                        d_min=d_min,
                        d_max=d_max,
                        d_step=d_step,
                        p_threshold=p_threshold,
                    )
        except Exception as e:
            print(f"<WARNING> Could not process M30 HDF5 dataset: {e}", flush=True)

    # 5. Compute FFD Transformed Series at optimal d*
    ffd_opt_series = frac_diff_ffd(series_norm, d=opt_d_norm, thres=1e-4)
    ffd_1_series = frac_diff_ffd(series_norm, d=1.0, thres=1e-4)

    # Add to DataFrame
    norm_df["ffd_norm_price_index"] = ffd_opt_series
    norm_df["ffd_d_star"] = opt_d_norm

    # 6. Save Grid Search & Updated CSV Exports
    if export_csv:
        # Save grid search CSV
        grid_csv_path = SCRIPT_DIR / f"{symbol}_M30_fractional_differencing_grid_search.csv"
        grid_df_norm.to_csv(grid_csv_path, index=False)
        
        # Save updated normalized bars CSV
        norm_df.to_csv(csv_norm_path, index=False)
        print(f"<CSV> Updated {csv_norm_path.name} with 'ffd_norm_price_index' (d*={opt_d_norm:.2f}).", flush=True)
        print(f"<CSV> Exported grid search evaluation table to {grid_csv_path.name}.", flush=True)

    # 7. Update HDF5 Dataset
    if hdf5_path.exists():
        with h5py.File(hdf5_path, "a") as f:
            grp_name = f"FRACTIONAL_DIFFERENCED_BARS/M30/{symbol}"
            if grp_name in f:
                del f[grp_name]

            # Construct structured array for FFD dataset
            dt = np.dtype([
                ("time", "<i8"),
                ("norm_price_index", "<f8"),
                ("ffd_norm_price_index", "<f8"),
                ("ffd_d_star", "<f8"),
            ])
            
            # Convert time to timestamp seconds
            t_vals = pd.to_datetime(norm_df["time"]).astype("int64") // 10**9
            rec_arr = np.empty(len(norm_df), dtype=dt)
            rec_arr["time"] = t_vals.values
            rec_arr["norm_price_index"] = norm_df["norm_price_index"].values
            rec_arr["ffd_norm_price_index"] = norm_df["ffd_norm_price_index"].fillna(np.nan).values
            rec_arr["ffd_d_star"] = opt_d_norm

            f.create_dataset(grp_name, data=rec_arr)
            print(f"<HDF5> Stored FFD dataset in HDF5 under key '{grp_name}'.", flush=True)

    # 8. Log Change
    t_start = norm_df["time"].min() if len(norm_df) > 0 else ""
    t_end = norm_df["time"].max() if len(norm_df) > 0 else ""
    append_change_log(
        hdf5_path,
        action=f"Fractional Differencing FFD Search (d*={opt_d_norm:.2f})",
        symbol=symbol,
        timeframe="M30",
        start_time=t_start,
        end_time=t_end,
    )

    # 9. Comparative Summary Table Output
    print("\n" + "=" * 115, flush=True)
    print("      FRACTIONAL DIFFERENTIATION (FFD) OPTIMIZATION & COMPARATIVE ANALYSIS SUMMARY", flush=True)
    print("=" * 115, flush=True)
    print(f"{'Data Series / Bar Type':<40} | {'Optimal d*':<10} | {'ADF Stat':<10} | {'ADF p-val':<10} | {'Memory Retained':<16} | {'Memory Lost':<12}", flush=True)
    print("-" * 115, flush=True)

    row_norm = grid_df_norm[grid_df_norm["d"] == opt_d_norm].iloc[0]
    print(
        f"{'Volatility-Normalized Volume Bars':<40} | {opt_d_norm:<10.2f} | {row_norm['adf_stat']:<10.4f} | "
        f"{row_norm['p_val']:<10.5f} | {row_norm['corr_with_orig']*100:<15.2f}% | {row_norm['memory_lost']*100:<11.2f}%",
        flush=True,
    )

    row_close = grid_df_close[grid_df_close["d"] == opt_d_close].iloc[0]
    print(
        f"{'Raw Volume Bars (Close Price)':<40} | {opt_d_close:<10.2f} | {row_close['adf_stat']:<10.4f} | "
        f"{row_close['p_val']:<10.5f} | {row_close['corr_with_orig']*100:<15.2f}% | {row_close['memory_lost']*100:<11.2f}%",
        flush=True,
    )

    if grid_df_m30 is not None and not np.isnan(opt_d_m30):
        row_m30 = grid_df_m30[grid_df_m30["d"] == opt_d_m30].iloc[0]
        print(
            f"{'Raw M30 Time Bars (Close Price)':<40} | {opt_d_m30:<10.2f} | {row_m30['adf_stat']:<10.4f} | "
            f"{row_m30['p_val']:<10.5f} | {row_m30['corr_with_orig']*100:<15.2f}% | {row_m30['memory_lost']*100:<11.2f}%",
            flush=True,
        )

    print("=" * 115, flush=True)

    # 10. Generate Plot
    if generate_plot:
        plot_path = SCRIPT_DIR / f"{symbol}_M30_fractional_differencing_analysis.png"
        generate_fractional_differencing_plots(
            grid_df=grid_df_norm,
            opt_d=opt_d_norm,
            orig_series=series_norm,
            ffd_opt_series=ffd_opt_series,
            ffd_1_series=ffd_1_series,
            symbol=symbol,
            output_path=plot_path,
            series_label="Volatility-Normalized Price Index",
        )


def main():
    parser = argparse.ArgumentParser(
        description="Analyze normalized dataset with Fixed-width Window Fractional Differentiation (FFD) and Grid Search for optimal d*."
    )
    parser.add_argument("--hdf5", type=str, default=str(DEFAULT_HDF5_PATH), help="Path to HDF5 file.")
    parser.add_argument("--symbol", type=str, default="EURUSD", help="Symbol to process (default: EURUSD).")
    parser.add_argument("--d-min", type=float, default=0.0, help="Minimum d for grid search (default: 0.0).")
    parser.add_argument("--d-max", type=float, default=1.0, help="Maximum d for grid search (default: 1.0).")
    parser.add_argument("--d-step", type=float, default=0.01, help="Grid search step size (default: 0.01).")
    parser.add_argument("--p-threshold", type=float, default=0.05, help="ADF p-value threshold (default: 0.05).")
    parser.add_argument("--no-csv", action="store_true", help="Disable CSV export.")
    parser.add_argument("--no-plot", action="store_true", help="Disable plot generation.")

    args = parser.parse_args()
    hdf5_path = Path(args.hdf5)

    run_fractional_differencing_analysis(
        hdf5_path=hdf5_path,
        symbol=args.symbol,
        d_min=args.d_min,
        d_max=args.d_max,
        d_step=args.d_step,
        p_threshold=args.p_threshold,
        export_csv=not args.no_csv,
        generate_plot=not args.no_plot,
    )

    print("\n=================================================================================", flush=True)
    print(" FRACTIONAL DIFFERENTIATION (FFD) ANALYSIS & PLOTS COMPLETED SUCCESSFULLY", flush=True)
    print("=================================================================================\n", flush=True)


if __name__ == "__main__":
    main()
