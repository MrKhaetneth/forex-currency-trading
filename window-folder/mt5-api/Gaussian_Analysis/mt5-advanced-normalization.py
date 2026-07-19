import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import scipy.stats as stats
import matplotlib.pyplot as plt
import statsmodels.api as sm
import scipy.optimize as opt
import json

def main():
    print("Connecting to MetaTrader5...")
    if not mt5.initialize():
        print("Initialization failed, error code = ", mt5.last_error())
        return

    symbol = "EURUSD"
    if not mt5.symbol_select(symbol, True):
        print(f"Failed to select symbol {symbol}")
        mt5.shutdown()
        return

    # Pull 20,000 M1 bars
    timeframe = mt5.TIMEFRAME_M1
    num_bars = 20000
    print(f"Fetching the latest {num_bars} M1 bars for {symbol}...")
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_bars)
    mt5.shutdown()

    if rates is None or len(rates) == 0:
        print("Failed to retrieve rates.")
        return

    # Create DataFrame
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    # 1. Base Time Bars Returns
    df['Time_Log_Returns'] = np.log(df['close'] / df['close'].shift(1))
    time_returns = df['Time_Log_Returns'].dropna().to_numpy()

    # 2. Volatility-Standardized Time Returns via GARCH(1,1)
    print("Fitting GARCH(1,1) model to Time Bar returns...")
    scaled_time_returns = time_returns * 100
    
    def garch_neg_log_likelihood(params, returns):
        omega, alpha, beta = params
        penalty = 0.0
        # Soft penalty for stationarity violations (alpha + beta >= 1)
        if alpha + beta >= 1.0:
            penalty = 1e6 * (alpha + beta - 0.999)**2
        T = len(returns)
        variance = np.zeros(T)
        variance[0] = np.var(returns)
        for t in range(1, T):
            variance[t] = omega + alpha * (returns[t-1]**2) + beta * variance[t-1]
        variance = np.clip(variance, 1e-10, None)
        nll = 0.5 * np.sum(np.log(2 * np.pi) + np.log(variance) + (returns**2) / variance)
        return nll + penalty

    init_params = [np.var(scaled_time_returns) * 0.1, 0.05, 0.90]
    bounds = ((1e-10, None), (1e-10, 0.999), (1e-10, 0.999))

    # Use L-BFGS-B optimizer, which is much faster and highly robust for bounded optimization
    res = opt.minimize(garch_neg_log_likelihood, init_params, args=(scaled_time_returns,),
                       bounds=bounds, method='L-BFGS-B')
    
    garch_success = False
    garch_info = {}
    if res.success:
        omega_garch_scaled, alpha_garch, beta_garch = res.x
        # Verify it meets the stationarity condition
        if alpha_garch + beta_garch < 1.0:
            omega_garch = omega_garch_scaled / 10000.0
            
            garch_variance = np.zeros(len(time_returns))
            garch_variance[0] = np.var(time_returns)
            for t in range(1, len(time_returns)):
                garch_variance[t] = omega_garch + alpha_garch * (time_returns[t-1]**2) + beta_garch * garch_variance[t-1]
            
            vol_std_time_returns = time_returns / np.sqrt(garch_variance)
            time_method_label = "GARCH Vol-Std Time"
            garch_success = True
            
            uncond_vol = np.sqrt(omega_garch / (1.0 - alpha_garch - beta_garch))
            print(f"GARCH(1,1) Optimization Succeeded:")
            print(f"  Omega (baseline var): {omega_garch:.8e}")
            print(f"  Alpha (shock sens)  : {alpha_garch:.4f}")
            print(f"  Beta (persistence)  : {beta_garch:.4f}")
            print(f"  Unconditional Vol   : {uncond_vol * 100:.6f}% per minute")
            
            garch_info = {
                "status": "success",
                "omega": float(omega_garch),
                "alpha": float(alpha_garch),
                "beta": float(beta_garch),
                "unconditional_volatility_per_min": float(uncond_vol),
                "unconditional_volatility_annualized": float(uncond_vol * np.sqrt(374400))
            }

    if not garch_success:
        print("\nGARCH Optimization failed to converge or did not meet stationarity.")
        print("-> Falling back to the highly responsive Rolling Volatility (window=20) method.")
        
        rolling_vol = df['Time_Log_Returns'].rolling(window=20).std()
        vol_std_time_returns = (df['Time_Log_Returns'] / rolling_vol).dropna().to_numpy()
        time_method_label = "Rolling Vol-Std Time"
        
        garch_info = {
            "status": "optimization_failed_fallback_used",
            "fallback_method": "Rolling Volatility (window=20)"
        }

    # 3. Construct Volume Bars Returns
    avg_tick_volume = df['tick_volume'].mean()
    volume_threshold = avg_tick_volume * 10
    
    volume_bars_close = []
    current_vol = 0.0
    for idx, row in df.iterrows():
        current_vol += row['tick_volume']
        if current_vol >= volume_threshold:
            volume_bars_close.append(row['close'])
            current_vol = 0.0
            
    vol_df = pd.DataFrame({'close': volume_bars_close})
    vol_df['returns'] = np.log(vol_df['close'] / vol_df['close'].shift(1))
    volume_returns = vol_df['returns'].dropna().to_numpy()

    # 4. Volatility-Standardized Volume Bars Returns (Using Rolling Volatility window = 20)
    # We apply volatility standardization directly to the constructed volume bar returns
    volume_returns_series = pd.Series(volume_returns)
    rolling_vol_volume = volume_returns_series.rolling(window=20).std()
    vol_std_volume_returns = (volume_returns_series / rolling_vol_volume).dropna().to_numpy()

    # 5. Dollar Bars Returns (Notional Value = Price * tick_volume)
    df['Notional_Val'] = df['close'] * df['tick_volume']
    avg_notional = df['Notional_Val'].mean()
    dollar_threshold = avg_notional * 10
    
    dollar_bars_close = []
    current_dollar = 0.0
    for idx, row in df.iterrows():
        current_dollar += row['Notional_Val']
        if current_dollar >= dollar_threshold:
            dollar_bars_close.append(row['close'])
            current_dollar = 0.0
            
    dollar_df = pd.DataFrame({'close': dollar_bars_close})
    dollar_df['returns'] = np.log(dollar_df['close'] / dollar_df['close'].shift(1))
    dollar_returns = dollar_df['returns'].dropna().to_numpy()

    # Standardize all returns for visual comparison (mean=0, std=1)
    time_std = (time_returns - np.mean(time_returns)) / np.std(time_returns)
    vol_std_time_std = (vol_std_time_returns - np.mean(vol_std_time_returns)) / np.std(vol_std_time_returns)
    vol_std = (volume_returns - np.mean(volume_returns)) / np.std(volume_returns)
    vol_std_volume_std = (vol_std_volume_returns - np.mean(vol_std_volume_returns)) / np.std(vol_std_volume_returns)
    dollar_std = (dollar_returns - np.mean(dollar_returns)) / np.std(dollar_returns)

    # Compute statistics
    methods = {
        "Time Bars": time_returns,
        "Volume Bars": volume_returns,
        "Dollar Bars": dollar_returns,
        time_method_label: vol_std_time_returns,
        "Vol-Std Volume Bars": vol_std_volume_returns
    }

    print("\n" + "="*110)
    print("                              STATISTICAL COMPARISON OF ALL NORMALIZATION METHODS")
    print("="*110)
    print(f"{'Method':<25} | {'Observations':<12} | {'Skewness':<8} | {'Excess Kurtosis':<15} | {'JB Stat':<12} | {'JB p-value':<12}")
    print("-" * 110)
    
    stats_dict = {}
    for name, data in methods.items():
        skew = stats.skew(data)
        kurt = stats.kurtosis(data)
        jb_stat, jb_p = stats.jarque_bera(data)
        jb_p_str = f"{jb_p:.2e}" if jb_p > 1e-300 else "< 1e-300"
        print(f"{name:<25} | {len(data):<12} | {skew:<8.4f} | {kurt:<15.4f} | {jb_stat:<12.2f} | {jb_p_str:<12}")
        
        # Collect statistics to save in JSON
        stats_dict[name] = {
            "observations": int(len(data)),
            "skewness": float(skew),
            "excess_kurtosis": float(kurt),
            "jb_statistic": float(jb_stat),
            "jb_p_value": float(jb_p)
        }
    print("="*110)

    # Save GARCH parameters and all comparison metrics to JSON inside Gaussian_Analysis/analysis_results/
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    save_dir = os.path.join(script_dir, "analysis_results")
    os.makedirs(save_dir, exist_ok=True)

    output_json = os.path.join(save_dir, "garch_parameters.json")
    output_data = {
        "symbol": symbol,
        "garch_estimation": garch_info,
        "comparison_metrics": stats_dict
    }
    with open(output_json, "w") as f:
        json.dump(output_data, f, indent=4)
    print(f"\nAll statistical comparison numbers successfully saved to: {output_json}")

    # Plot comparisons (Histograms & Q-Q Plots)
    # We compare: Volume Bars vs. Vol-Standardized Volume Bars
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    x_axis = np.linspace(-5, 5, 500)
    gaussian_pdf = stats.norm.pdf(x_axis, 0, 1)

    # Row 1, Col 1: Histogram - Volume Bars
    axes[0, 0].hist(vol_std, bins=50, density=True, alpha=0.6, color='teal', edgecolor='black', label='Volume Returns')
    axes[0, 0].plot(x_axis, gaussian_pdf, 'k--', linewidth=2, label='Normal Distribution')
    axes[0, 0].set_xlim([-5, 5])
    axes[0, 0].set_title(f"Volume Bars Distribution\n(Excess Kurtosis: {stats.kurtosis(volume_returns):.2f})")
    axes[0, 0].set_xlabel("Standardized Return")
    axes[0, 0].set_ylabel("Density")
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)

    # Row 1, Col 2: Q-Q Plot - Volume Bars
    sm.qqplot(vol_std, line='45', ax=axes[0, 1], marker='.', markerfacecolor='teal', markeredgecolor='teal', alpha=0.4)
    axes[0, 1].set_title("Q-Q Plot: Volume Bars")
    axes[0, 1].grid(True, alpha=0.3)

    # Row 2, Col 1: Histogram - Vol-Std Volume Bars
    axes[1, 0].hist(vol_std_volume_std, bins=50, density=True, alpha=0.6, color='purple', edgecolor='black', label='Vol-Std Volume')
    axes[1, 0].plot(x_axis, gaussian_pdf, 'k--', linewidth=2, label='Normal Distribution')
    axes[1, 0].set_xlim([-5, 5])
    axes[1, 0].set_title(f"Vol-Std Volume Bars Distribution\n(Excess Kurtosis: {stats.kurtosis(vol_std_volume_returns):.2f})")
    axes[1, 0].set_xlabel("Standardized Return")
    axes[1, 0].set_ylabel("Density")
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)

    # Row 2, Col 2: Q-Q Plot - Vol-Std Volume Bars
    sm.qqplot(vol_std_volume_std, line='45', ax=axes[1, 1], marker='.', markerfacecolor='purple', markeredgecolor='purple', alpha=0.4)
    axes[1, 1].set_title("Q-Q Plot: Vol-Std Volume Bars")
    axes[1, 1].grid(True, alpha=0.3)

    # Align axes for the Q-Q plots (Column 2)
    qq_xlim = (
        min(axes[0, 1].get_xlim()[0], axes[1, 1].get_xlim()[0]),
        max(axes[0, 1].get_xlim()[1], axes[1, 1].get_xlim()[1])
    )
    qq_ylim = (
        min(axes[0, 1].get_ylim()[0], axes[1, 1].get_ylim()[0]),
        max(axes[0, 1].get_ylim()[1], axes[1, 1].get_ylim()[1])
    )
    for ax in [axes[0, 1], axes[1, 1]]:
        ax.set_xlim(qq_xlim)
        ax.set_ylim(qq_ylim)

    plt.tight_layout()
    output_filename = os.path.join(save_dir, "eurusd_advanced_normalization.png")
    plt.savefig(output_filename, dpi=300)
    print(f"\nAdvanced comparison plot successfully saved as: {output_filename}")
    plt.show()

if __name__ == "__main__":
    main()
