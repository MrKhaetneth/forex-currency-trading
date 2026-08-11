# Fractional Differencing Analysis & Optimal $d^*$ Search Tool

A Python module implementing **Fixed-width Window Fractional Differentiation (FFD)** for financial time series data, following Chapter 5 of Marcos López de Prado's *Advances in Financial Machine Learning* (2018).

---

## 📌 Overview

Standard time-series preprocessing methods in financial machine learning present a dilemma:
- **Price Levels ($d = 0$)**: Retain 100% of long-term predictive memory, but are non-stationary (exhibiting unit roots and trending behavior), violating the stationarity assumption of most ML algorithms.
- **First Differences ($d = 1.0$)**: Achieve stationarity (stationary returns), but completely erase long-term historical memory and macro trends.

**Fractional Differencing (FFD)** solves this trade-off by expanding the differencing operator to non-integer values $d \in (0, 1)$. This tool performs a grid search across $d \in [0.0, 1.0]$ to identify the **minimum differencing parameter $d^*$** required to achieve stationarity ($p_{\text{ADF}} \le 0.05$), preserving maximum predictive memory while removing non-stationarity.

---

## 🧮 Theoretical Background

### Fractional Differentiation Operator
The fractional differencing operator $(1 - B)^d$ is defined via the binomial expansion:

$$
(1 - B)^d = \sum_{k=0}^{\infty} (-1)^k \binom{d}{k} B^k = 1 - d B + \frac{d(d-1)}{2!} B^2 - \frac{d(d-1)(d-2)}{3!} B^3 + \dots
$$

The weights $w_k$ are generated recursively:

$$
w_0 = 1, \quad w_k = -w_{k-1} \frac{d - k + 1}{k}
$$

### Fixed-width Window (FFD)
To prevent infinite lag windows and asymptotic memory loss, the **Fixed-width Window Fractional Differentiation (FFD)** method truncates weights below a tolerance threshold $\tau$ (default $\tau = 10^{-4}$):

$$
l = \min \{ k \mid |w_k| < \tau \}
$$

The fixed weight vector $[w_0, w_1, \dots, w_{l-1}]$ is convolved with the target series, providing a constant window width $l$ across the entire dataset.

---

## 🔑 Key Features

1. **Optimal $d^*$ Grid Search**: Systematically evaluates candidate values $d \in [0.0, 1.0]$ at step size $0.01$ (configurable) to find $\min \{ d \mid p_{\text{ADF}} \le 0.05 \}$.
2. **Multi-Series Comparative Analysis**: Compares stationarity and memory retention across Volatility-Normalized Volume Bars, Raw Volume Bars, and Raw M30 Time Bars.
3. **Automated HDF5 & CSV Exports**: Saves transformed series directly to `dataset/MT5CurrencyHistory.h5` and CSV data files.
4. **Audit Logging**: Logs all transformations with user, timestamp, symbol, and timeframe details in `MT5CurrencyHistory_change_log.csv`.
5. **6-Panel Diagnostic Visualization**: Renders publication-quality charts detailing $p$-values, t-statistics, memory trade-offs, normalized overlays, return distributions, and Gaussian Q-Q plots.

---

## 🛠️ Code Structure & API Reference

### Core Functions in `dataset/fractional_differencing.py`

| Function | Description |
| :--- | :--- |
| [`get_ffd_weights(d, thres=1e-4)`](file:///mnt/c/Users/src_rith/forex-currency-trading/dataset/fractional_differencing.py#L83-L103) | Computes the FFD weight vector $[w_0, \dots, w_{l-1}]$ until $|w_k| < \text{thres}$. |
| [`frac_diff_ffd(series, d, thres=1e-4)`](file:///mnt/c/Users/src_rith/forex-currency-trading/dataset/fractional_differencing.py#L105-L128) | Applies 1D discrete convolution of FFD weights over a pandas `Series`. |
| [`grid_search_minimum_d(...)`](file:///mnt/c/Users/src_rith/forex-currency-trading/dataset/fractional_differencing.py#L134-L221) | Grid searches candidate $d$ values, running ADF tests (`adfuller`) and Pearson correlation. |
| [`generate_fractional_differencing_plots(...)`](file:///mnt/c/Users/src_rith/forex-currency-trading/dataset/fractional_differencing.py#L228-L379) | Renders and exports the 6-panel diagnostic plot figure. |
| [`run_fractional_differencing_analysis(...)`](file:///mnt/c/Users/src_rith/forex-currency-trading/dataset/fractional_differencing.py#L385-L550) | Main orchestration workflow handling data loading, processing, exporting, logging, and plotting. |

---

## 📊 6-Panel Diagnostic Plot Details

The generated plot (`EURUSD_M30_fractional_differencing_analysis.png`) contains:

1. **ADF $p$-value vs $d$**: Displays $p$-value progression with horizontal threshold line ($p = 0.05$) and marker at optimal $d^*$.
2. **ADF $t$-Statistic vs $d$**: Shows t-statistic trajectory across candidate $d$ values.
3. **Memory Retention & Loss Trade-off**: Plots Pearson correlation $r(X_0, X_d)$ vs memory loss ($1 - r$).
4. **Time-Series Overlay**: Standardized (Z-score) comparison of Original ($d=0$), FFD Optimal ($d^*$), and First Difference ($d=1.0$).
5. **Distribution & Gaussian Fit**: Histogram of $FFD(d^*)$ values overlaid with fitted normal curve $N(\mu, \sigma^2)$, plus Jarque-Bera normality metrics.
6. **Normal Q-Q Plot**: Quantile-Quantile plot comparing $FFD(d^*)$ distribution against theoretical normal distribution.

---

## 💻 Command Line Usage

### Basic Execution
Run using default parameters (`EURUSD`, grid $d \in [0.0, 1.0]$, step $0.01$, threshold $p \le 0.05$):

```bash
python dataset/fractional_differencing.py
```

### Advanced Usage & CLI Arguments

```bash
python dataset/fractional_differencing.py \
    --hdf5 dataset/MT5CurrencyHistory.h5 \
    --symbol EURUSD \
    --d-min 0.0 \
    --d-max 1.0 \
    --d-step 0.01 \
    --p-threshold 0.05
```

#### CLI Options
- `--hdf5`: Path to target HDF5 file (default: `dataset/MT5CurrencyHistory.h5`).
- `--symbol`: Symbol ticker to analyze (default: `EURUSD`).
- `--d-min`: Lower bound for grid search (default: `0.0`).
- `--d-max`: Upper bound for grid search (default: `1.0`).
- `--d-step`: Grid step increment (default: `0.01`).
- `--p-threshold`: ADF p-value significance threshold for stationarity (default: `0.05`).
- `--no-csv`: Skip CSV file updates and exports.
- `--no-plot`: Skip diagnostic plot creation.

---

## 📁 Input & Output Dependencies

### Inputs
- **`dataset/EURUSD_M30_volatility_normalized_bars.csv`**: Must contain `norm_price_index` and `close` columns.
- **`dataset/MT5CurrencyHistory.h5`**: Optional/Default data store containing raw time bars and volume bars.

### Outputs Generated
- **`dataset/EURUSD_M30_volatility_normalized_bars.csv`**: Updated with `ffd_norm_price_index` and `ffd_d_star` columns.
- **`dataset/EURUSD_M30_fractional_differencing_grid_search.csv`**: Evaluation table containing $d$, ADF stat, $p$-value, correlation, memory lost, window length $l$, and stationarity flag.
- **`dataset/EURUSD_M30_fractional_differencing_analysis.png`**: High-resolution 300 DPI 6-panel diagnostic plot.
- **`dataset/MT5CurrencyHistory.h5`**: Stores structured array under key `FRACTIONAL_DIFFERENCED_BARS/M30/<SYMBOL>`.
- **`dataset/MT5CurrencyHistory_change_log.csv`**: Appends audit record detailing operation history.

---

## 📦 Requirements

- Python 3.8+
- `numpy`
- `pandas`
- `h5py`
- `scipy`
- `statsmodels`
- `matplotlib`

---

## 📖 References

- López de Prado, M. (2018). *Advances in Financial Machine Learning*. John Wiley & Sons. Chapter 5: "Fractionally Differentiated Features".
