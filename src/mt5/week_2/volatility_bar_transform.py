#!/usr/bin/env python3
"""
M30 Market Data Transformation & Diagnostic Normality Plotting Tool
====================================================================

This script processes M30 market data from `dataset/MT5CurrencyHistory.h5` to construct:
1. Time Bars (Raw M30 time-series)
2. Volume Bars (Sampled based on cumulative volume threshold)
3. Vol-Std Volume Bars (Volume bars with returns standardized by local rolling volatility)

Deletes D1 data from HDF5 and filesystem as requested, leaving only M30 data and outputs.

Generates a 6-panel diagnostic plot comparing:
- Return Distributions (Histograms with standard normal N(0,1) overlay) for Time Bars (M30), Volume Bars, and Vol-Std Volume Bars.
- Q-Q Plots for each of the 3 bar types to test for Gaussian return normality.

References:
    - López de Prado, M. (2018). *Advances in Financial Machine Learning*. John Wiley & Sons.
"""

import os
import sys
import argparse
import json
import csv
import glob
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import h5py
import scipy.stats as stats
import matplotlib.pyplot as plt
import statsmodels.api as sm

# Define default paths relative to workspace root
SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parent
DEFAULT_HDF5_PATH = SCRIPT_DIR / "MT5CurrencyHistory.h5"
DEFAULT_CHANGE_LOG_PATH = SCRIPT_DIR / "MT5CurrencyHistory_change_log.csv"


# ==============================================================================
# 1. HDF5 CLEANUP & AUDIT LOGGING
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
    print(f"<LOG> Logged '{action}' for {symbol} ({timeframe}) in {csv_path.name}.")


def clean_non_m30_data(hdf5_path: Path):
    """Purge D1 and non-M30 datasets from HDF5 file and remove any D1 CSV/PNG files."""
    if not hdf5_path.exists():
        return

    with h5py.File(hdf5_path, "a") as f:
        for group_name in list(f.keys()):
            grp = f[group_name]
            for tf_name in list(grp.keys()):
                if tf_name.upper() != "M30":
                    print(f"<CLEAN> Purging non-M30 dataset: {group_name}/{tf_name}...")
                    del grp[tf_name]

    # Remove D1 generated CSV and PNG files in dataset/
    for pattern in [str(SCRIPT_DIR / "*_D1_*"), str(SCRIPT_DIR / "*_MN1_*"), str(SCRIPT_DIR / "*_W1_*")]:
        for filepath in glob.glob(pattern):
            print(f"<CLEAN> Deleting file: {Path(filepath).name}")
            try:
                os.remove(filepath)
            except Exception:
                pass


def load_m30_hdf5_data(hdf5_path: Path, symbol: str) -> pd.DataFrame:
    """Load M30 price history from HDF5 under 'TIMEFRAME/M30/<symbol>'."""
    dataset_path = f"TIMEFRAME/M30/{symbol}"
    with h5py.File(hdf5_path, "r") as f:
        if dataset_path not in f:
            raise KeyError(f"M30 dataset path '{dataset_path}' not found in HDF5 file '{hdf5_path}'.")
        arr = f[dataset_path][:]

    df = pd.DataFrame({name: arr[name] for name in arr.dtype.names})
    if "time" in df.columns:
        if pd.api.types.is_numeric_dtype(df["time"]):
            df["time"] = pd.to_datetime(df["time"], unit="s")
        else:
            df["time"] = pd.to_datetime(df["time"])
    return df.sort_values(by="time").reset_index(drop=True)


# ==============================================================================
# 2. BAR SAMPLING: VOLUME BARS & VOL-STD VOLUME BARS
# ==============================================================================

def build_volume_bars(
    df: pd.DataFrame,
    volume_col: str = "tick_volume",
    multiplier: float = 10.0,
) -> pd.DataFrame:
    """Sample Volume Bars from M30 time-series OHLCV data based on cumulative volume threshold."""
    if volume_col not in df.columns or df[volume_col].sum() == 0:
        volume_col = "tick_volume"

    volumes = df[volume_col].values
    vol_threshold = float(np.mean(volumes) * multiplier)
    vol_threshold = max(vol_threshold, 1.0)
    
    bar_records = []
    curr_open = None
    curr_high = -np.inf
    curr_low = np.inf
    curr_tick_vol = 0
    curr_real_vol = 0
    curr_count = 0
    start_time = None

    for idx, row in df.iterrows():
        if curr_count == 0:
            start_time = row["time"]
            curr_open = row["open"]
            curr_high = row["high"]
            curr_low = row["low"]
        
        curr_high = max(curr_high, row["high"])
        curr_low = min(curr_low, row["low"])
        curr_close = row["close"]
        curr_tick_vol += row.get("tick_volume", 0)
        curr_real_vol += row.get("real_volume", 0)
        curr_count += 1

        acc_vol = curr_tick_vol if volume_col == "tick_volume" else curr_real_vol
        if acc_vol >= vol_threshold:
            end_time = row["time"]
            duration = (end_time - start_time).total_seconds() if isinstance(end_time, pd.Timestamp) and isinstance(start_time, pd.Timestamp) else 0

            bar_records.append({
                "time": end_time,
                "start_time": start_time,
                "open": curr_open,
                "high": curr_high,
                "low": curr_low,
                "close": curr_close,
                "tick_volume": curr_tick_vol,
                "real_volume": curr_real_vol,
                "num_time_bars": curr_count,
                "duration_seconds": duration,
            })

            curr_count = 0
            curr_high = -np.inf
            curr_low = np.inf
            curr_tick_vol = 0
            curr_real_vol = 0

    vol_df = pd.DataFrame(bar_records)
    print(f"<BARS> Sampled {len(vol_df)} Volume Bars from {len(df)} M30 time bars (Threshold = {vol_threshold:,.2f}).")
    return vol_df


def compute_volatility_normalized_volume_bars(vol_df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """Compute volatility-normalized returns and OHLC features for Volume Bars."""
    df = vol_df.copy()
    df["raw_log_return"] = np.log(df["close"] / df["close"].shift(1)).fillna(0.0)

    eff_window = min(window, max(3, len(df) // 4))
    rolling_vol = df["raw_log_return"].rolling(window=eff_window, min_periods=2).std()
    sigma = rolling_vol.fillna(df["raw_log_return"].std() if df["raw_log_return"].std() > 0 else 1e-4)
    sigma = np.maximum(sigma, 1e-6)

    df["volatility_sigma"] = sigma
    df["norm_return"] = df["raw_log_return"] / sigma
    sigma_price = sigma * df["open"]

    df["norm_open"] = 0.0
    df["norm_high"] = (df["high"] - df["open"]) / sigma_price
    df["norm_low"] = (df["low"] - df["open"]) / sigma_price
    df["norm_close"] = (df["close"] - df["open"]) / sigma_price
    df["norm_range"] = (df["high"] - df["low"]) / sigma_price
    df["norm_body"] = (df["close"] - df["open"]) / sigma_price
    
    mean_sigma = sigma.mean() if sigma.mean() > 0 else 1e-4
    df["norm_price_index"] = 100.0 + np.cumsum(df["norm_return"] * mean_sigma * 100.0)

    return df


# ==============================================================================
# 3. STATISTICAL EVALUATION & 6-PANEL DIAGNOSTIC PLOT
# ==============================================================================

def calculate_normality_stats(time_rets: np.ndarray, vol_rets: np.ndarray, vol_std_rets: np.ndarray):
    """Print clean statistical metrics comparing Time Bars vs Volume Bars vs Vol-Std Volume Bars for M30."""
    methods = {
        "Time Bars (M30)": time_rets,
        "Volume Bars (Raw)": vol_rets,
        "Vol-Std Volume Bars": vol_std_rets,
    }

    print("\n" + "=" * 115)
    print("      STATISTICAL COMPARISON & GAUSSIAN NORMALITY TESTS [M30 DATASET]")
    print("=" * 115)
    print(f"{'Method Name':<28} | {'Obs':<6} | {'Mean':<9} | {'Std Dev':<9} | {'Skewness':<9} | {'Excess Kurt':<12} | {'JB Stat':<10} | {'JB p-val':<10}")
    print("-" * 115)

    for name, data in methods.items():
        clean = data[~np.isnan(data)]
        if len(clean) < 3:
            continue
        n_obs = len(clean)
        mean_v = np.mean(clean)
        std_v = np.std(clean)
        skew_v = stats.skew(clean)
        kurt_v = stats.kurtosis(clean)
        jb_stat, jb_pval = stats.jarque_bera(clean)

        jb_p_str = f"{jb_pval:.2e}" if jb_pval > 1e-300 else "< 1e-300"
        print(f"{name:<28} | {n_obs:<6} | {mean_v:<9.5f} | {std_v:<9.5f} | {skew_v:<9.4f} | {kurt_v:<12.4f} | {jb_stat:<10.2f} | {jb_p_str:<10}")

    print("=" * 115)


def generate_3way_comparison_plots(
    time_rets: np.ndarray,
    vol_rets: np.ndarray,
    vol_std_rets: np.ndarray,
    symbol: str,
    save_path: Path,
    start_date: str = "2020-12-21",
    end_date: str = "2021-12-21",
):
    """Generate 6-panel diagnostic plot for M30 dataset: Return Distributions & Q-Q Plots."""
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))

    t_data = time_rets[~np.isnan(time_rets)]
    v_data = vol_rets[~np.isnan(vol_rets)]
    vs_data = vol_std_rets[~np.isnan(vol_std_rets)]

    t_std = (t_data - np.mean(t_data)) / (np.std(t_data) or 1.0)
    v_std = (v_data - np.mean(v_data)) / (np.std(v_data) or 1.0)
    vs_std = (vs_data - np.mean(vs_data)) / (np.std(vs_data) or 1.0)

    x_axis = np.linspace(-5, 5, 500)
    gaussian_pdf = stats.norm.pdf(x_axis, 0, 1)

    t_kurt, t_jb_p = stats.kurtosis(t_data), stats.jarque_bera(t_data)[1]
    v_kurt, v_jb_p = stats.kurtosis(v_data), stats.jarque_bera(v_data)[1]
    vs_kurt, vs_jb_p = stats.kurtosis(vs_data), stats.jarque_bera(vs_data)[1]

    t_p_str = f"{t_jb_p:.2e}" if t_jb_p > 1e-300 else "< 1e-300"
    v_p_str = f"{v_jb_p:.2e}" if v_jb_p > 1e-300 else "< 1e-300"
    vs_p_str = f"{vs_jb_p:.2e}" if vs_jb_p > 1e-300 else "< 1e-300"

    c_time = "navy"
    c_vol = "teal"
    c_vol_std = "purple"

    # ==========================================================================
    # ROW 1: RETURN DISTRIBUTIONS (HISTOGRAMS)
    # ==========================================================================

    axes[0, 0].hist(t_std, bins=50, density=True, alpha=0.6, color=c_time, edgecolor="black", label="M30 Time Returns")
    axes[0, 0].plot(x_axis, gaussian_pdf, "k--", linewidth=2.0, label="Normal N(0,1)")
    axes[0, 0].set_xlim([-5, 5])
    axes[0, 0].set_title(f"1. Time Bars (M30) Distribution\n(Kurtosis: {t_kurt:.2f} | JB p-val: {t_p_str})", fontsize=11, fontweight="bold")
    axes[0, 0].set_xlabel("Standardized Log Return")
    axes[0, 0].set_ylabel("Density")
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)

    axes[0, 1].hist(v_std, bins=50, density=True, alpha=0.6, color=c_vol, edgecolor="black", label="Volume Returns")
    axes[0, 1].plot(x_axis, gaussian_pdf, "k--", linewidth=2.0, label="Normal N(0,1)")
    axes[0, 1].set_xlim([-5, 5])
    axes[0, 1].set_title(f"2. Volume Bars Distribution\n(Kurtosis: {v_kurt:.2f} | JB p-val: {v_p_str})", fontsize=11, fontweight="bold")
    axes[0, 1].set_xlabel("Standardized Log Return")
    axes[0, 1].set_ylabel("Density")
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)

    axes[0, 2].hist(vs_std, bins=50, density=True, alpha=0.6, color=c_vol_std, edgecolor="black", label="Vol-Std Volume Returns")
    axes[0, 2].plot(x_axis, gaussian_pdf, "k--", linewidth=2.0, label="Normal N(0,1)")
    axes[0, 2].set_xlim([-5, 5])
    axes[0, 2].set_title(f"3. Vol-Std Volume Bars Distribution\n(Kurtosis: {vs_kurt:.2f} | JB p-val: {vs_p_str})", fontsize=11, fontweight="bold")
    axes[0, 2].set_xlabel("Standardized Log Return")
    axes[0, 2].set_ylabel("Density")
    axes[0, 2].legend()
    axes[0, 2].grid(True, alpha=0.3)

    # ==========================================================================
    # ROW 2: NORMAL Q-Q PLOTS
    # ==========================================================================

    sm.qqplot(t_std, line="45", ax=axes[1, 0], marker=".", markerfacecolor=c_time, markeredgecolor=c_time, alpha=0.4)
    axes[1, 0].set_title("Q-Q Plot: M30 Time Bars", fontsize=11, fontweight="bold")
    axes[1, 0].grid(True, alpha=0.3)

    sm.qqplot(v_std, line="45", ax=axes[1, 1], marker=".", markerfacecolor=c_vol, markeredgecolor=c_vol, alpha=0.4)
    axes[1, 1].set_title("Q-Q Plot: Volume Bars", fontsize=11, fontweight="bold")
    axes[1, 1].grid(True, alpha=0.3)

    sm.qqplot(vs_std, line="45", ax=axes[1, 2], marker=".", markerfacecolor=c_vol_std, markeredgecolor=c_vol_std, alpha=0.4)
    axes[1, 2].set_title("Q-Q Plot: Vol-Std Volume Bars", fontsize=11, fontweight="bold")
    axes[1, 2].grid(True, alpha=0.3)

    qq_xlim = (
        min(axes[1, 0].get_xlim()[0], axes[1, 1].get_xlim()[0], axes[1, 2].get_xlim()[0]),
        max(axes[1, 0].get_xlim()[1], axes[1, 1].get_xlim()[1], axes[1, 2].get_xlim()[1]),
    )
    qq_ylim = (
        min(axes[1, 0].get_ylim()[0], axes[1, 1].get_ylim()[0], axes[1, 2].get_ylim()[0]),
        max(axes[1, 0].get_ylim()[1], axes[1, 1].get_ylim()[1], axes[1, 2].get_ylim()[1]),
    )
    for col in range(3):
        axes[1, col].set_xlim(qq_xlim)
        axes[1, col].set_ylim(qq_ylim)

    plt.suptitle(
        f"Return Distributions & Normality Q-Q Plots [{symbol} - M30 Dataset ({start_date} to {end_date})]\n"
        f"(Time Bars vs Volume Bars vs Volatility-Normalized Volume Bars)",
        fontsize=13, fontweight="bold", y=0.995
    )
    plt.tight_layout()

    save_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=300)
    plt.close()
    print(f"<PLOTS> Saved 6-panel diagnostic plot to: {save_path.name}")



# ==============================================================================
# 4. HDF5 STORAGE & MAIN PIPELINE
# ==============================================================================

def save_m30_to_hdf5(hdf5_path: Path, symbol: str, vol_df: pd.DataFrame, norm_vol_df: pd.DataFrame):
    """Save Volume Bars and Volatility-Normalized Volume Bars into HDF5 under M30."""
    with h5py.File(hdf5_path, "a") as f:
        # 1. VOLUME_BARS/M30/<symbol>
        grp_vol = f.require_group("VOLUME_BARS/M30")
        if symbol in grp_vol:
            del grp_vol[symbol]
            
        dtype_list_vol = [
            ("time", "i8"),
            ("open", "f8"),
            ("high", "f8"),
            ("low", "f8"),
            ("close", "f8"),
            ("tick_volume", "i8"),
            ("real_volume", "i8"),
            ("num_time_bars", "i8"),
            ("duration_seconds", "f8"),
        ]
        struct_dtype_vol = np.dtype(dtype_list_vol)
        arr_vol = np.empty(len(vol_df), dtype=struct_dtype_vol)
        for col, _ in dtype_list_vol:
            if col == "time":
                time_s = pd.to_datetime(vol_df["time"])
                arr_vol["time"] = time_s.values.astype("datetime64[s]").astype("int64")
            elif col in vol_df.columns:
                arr_vol[col] = vol_df[col].fillna(0.0).values
            else:
                arr_vol[col] = 0.0

        grp_vol.create_dataset(symbol, data=arr_vol, compression="gzip", compression_opts=4)

        # 2. VOLATILITY_NORMALIZED_BARS/M30/<symbol>
        grp_norm = f.require_group("VOLATILITY_NORMALIZED_BARS/M30")
        if symbol in grp_norm:
            del grp_norm[symbol]
        
        dtype_list_norm = [
            ("time", "i8"),
            ("norm_open", "f8"),
            ("norm_high", "f8"),
            ("norm_low", "f8"),
            ("norm_close", "f8"),
            ("norm_return", "f8"),
            ("norm_range", "f8"),
            ("norm_body", "f8"),
            ("norm_price_index", "f8"),
            ("volatility_sigma", "f8"),
            ("open", "f8"),
            ("high", "f8"),
            ("low", "f8"),
            ("close", "f8"),
            ("tick_volume", "i8"),
            ("real_volume", "i8"),
        ]
        struct_dtype_norm = np.dtype(dtype_list_norm)
        arr_norm = np.empty(len(norm_vol_df), dtype=struct_dtype_norm)
        for col, _ in dtype_list_norm:
            if col == "time":
                time_s = pd.to_datetime(norm_vol_df["time"])
                arr_norm["time"] = time_s.values.astype("datetime64[s]").astype("int64")
            elif col in norm_vol_df.columns:
                arr_norm[col] = norm_vol_df[col].fillna(0.0).values
            else:
                arr_norm[col] = 0.0
        
        grp_norm.create_dataset(symbol, data=arr_norm, compression="gzip", compression_opts=4)

    print(f"<HDF5> Updated M30 datasets in {hdf5_path.name}.")


def process_m30_bars_and_generate_plots(
    hdf5_path: Path,
    symbol: str = "EURUSD",
    multiplier: float = 10.0,
    export_csv: bool = True,
    generate_plot: bool = True,
):
    """Main M30 processing workflow."""
    print(f"\n=================================================================================")
    print(f" PROCESSING M30 DATASET & GENERATING COMPARISON PLOTS: {symbol}")
    print(f"=================================================================================")

    # 1. Clean D1 and non-M30 datasets
    clean_non_m30_data(hdf5_path)

    # 2. Load M30 Time Bars
    time_df = load_m30_hdf5_data(hdf5_path, symbol)
    print(f"<LOAD> Loaded {len(time_df)} M30 time bars.")

    # 3. Construct Volume Bars from M30
    vol_df = build_volume_bars(time_df, volume_col="tick_volume", multiplier=multiplier)

    # 4. Construct Volatility-Normalized Volume Bars
    norm_vol_df = compute_volatility_normalized_volume_bars(vol_df)

    # 5. Extract Log Returns
    time_rets = np.log(time_df["close"] / time_df["close"].shift(1)).dropna().to_numpy()
    vol_rets = np.log(vol_df["close"] / vol_df["close"].shift(1)).dropna().to_numpy()
    vol_std_rets = norm_vol_df["norm_return"].dropna().to_numpy()

    # 6. Statistical Comparison Output
    calculate_normality_stats(time_rets, vol_rets, vol_std_rets)

    # 7. Save to HDF5 under M30
    save_m30_to_hdf5(hdf5_path, symbol, vol_df, norm_vol_df)

    # 8. Append Change Log
    t_start = time_df["time"].min() if len(time_df) > 0 else ""
    t_end = time_df["time"].max() if len(time_df) > 0 else ""
    append_change_log(hdf5_path, "Vol-Std Volume Bar Transformation & Plotting", symbol, timeframe="M30", start_time=t_start, end_time=t_end)

    # 9. CSV Exports
    if export_csv:
        csv_vol = SCRIPT_DIR / f"{symbol}_M30_volume_bars.csv"
        vol_df.to_csv(csv_vol, index=False)
        
        csv_norm = SCRIPT_DIR / f"{symbol}_M30_volatility_normalized_bars.csv"
        norm_vol_df.to_csv(csv_norm, index=False)
        print(f"<CSV> Exported M30 volume bars and volatility-normalized bars CSVs.")

    # 10. Generate 6-panel plot
    if generate_plot:
        plot_path = SCRIPT_DIR / f"{symbol}_M30_return_distributions_and_qq_plots.png"
        s_date = time_df["time"].min().strftime("%Y-%m-%d") if len(time_df) > 0 else "2020-12-21"
        e_date = time_df["time"].max().strftime("%Y-%m-%d") if len(time_df) > 0 else "2021-12-21"
        generate_3way_comparison_plots(time_rets, vol_rets, vol_std_rets, symbol, plot_path, start_date=s_date, end_date=e_date)



def main():
    parser = argparse.ArgumentParser(
        description="Process M30 dataset, remove D1 data, and generate Return Distribution Histograms and Q-Q Plots."
    )
    parser.add_argument("--hdf5", type=str, default=str(DEFAULT_HDF5_PATH), help="Path to HDF5 file.")
    parser.add_argument("--symbol", type=str, default="EURUSD", help="Symbol to process (default: EURUSD).")
    parser.add_argument("--multiplier", type=float, default=10.0, help="Volume bar multiplier for M30.")
    parser.add_argument("--no-csv", action="store_true", help="Disable CSV export.")
    parser.add_argument("--no-plot", action="store_true", help="Disable plot generation.")

    args = parser.parse_args()
    hdf5_path = Path(args.hdf5)

    if not hdf5_path.exists():
        print(f"<ERROR> HDF5 file not found at: {hdf5_path}")
        sys.exit(1)

    process_m30_bars_and_generate_plots(
        hdf5_path=hdf5_path,
        symbol=args.symbol,
        multiplier=args.multiplier,
        export_csv=not args.no_csv,
        generate_plot=not args.no_plot,
    )

    print("\n=================================================================================")
    print(" M30 ANALYSIS & DIAGNOSTIC PLOTS COMPLETED SUCCESSFULLY")
    print("=================================================================================\n")


if __name__ == "__main__":
    main()
