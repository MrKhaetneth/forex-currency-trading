# Volume-Based Microstructure Analysis: Time Bars vs. Volume Bars

This folder contains [fx_try.py](file:forex-currency-trading/src/distribution/fx_try.py), a script that demonstrates the statistical benefits of **Volume Bars** over standard **Time Bars** for modeling asset returns.

## Background & Rationale

In quantitative finance, security returns sampled at constant time intervals (e.g., every 1 minute) suffer from severe statistical anomalies:
1. **High Excess Kurtosis (Leptokurtosis)**: The return distribution has a high peak and "fat tails," meaning extreme events occur far more frequently than predicted by a standard normal distribution.
2. **Heteroscedasticity**: Volatility clusters together over time.

As detailed by Marcos López de Prado in *Advances in Financial Machine Learning*, trading activity is not uniform over time. Rather than sampling prices at arbitrary chronological intervals, we can sample prices whenever a specific amount of transactional volume has passed. This yields **Volume Bars**, which align the sampling rate with the arrival of market information. 

By analyzing returns in "transaction time" rather than "clock time," the distribution of log returns becomes closer to a standard Gaussian (normal) distribution. This makes the returns much better suited for standard statistical modeling, portfolio optimization, and machine learning models that assume normally distributed inputs.

---

## Financial Implications of Gaussian Returns

In standard quantitative finance theory, asset returns are often assumed to be **Gaussian (normally) distributed**. However, understanding what this means—and why this assumption is often dangerous in practice—is critical for risk management.

### 1. The Gaussian Assumption (Mild Randomness)
A Gaussian distribution assumes that prices change due to a continuous stream of small, independent random shocks:
* **Symmetry**: Prices are equally likely to rise or fall.
* **Predictable Dispersion**: Returns follow the empirical **68-95-99.7 rule**. A $3\sigma$ (standard deviation) move happens only once every 1.5 years. A $6\sigma$ move is expected only **once every 4 million years**, and a $10\sigma$ move is practically impossible in the lifetime of the universe.

### 2. The Real-World Reality (Fat Tails & Black Swans)
In actual financial markets, returns exhibit **heavy/fat tails (leptokurtosis)**. 
* Extreme price shocks (like Black Monday in 1987, the 2008 Financial Crisis, or the 2020 COVID crash) are mathematically impossible under a Gaussian curve (often registering as $10\sigma$ to $20\sigma$ events).
* In the real world, these "Black Swan" events occur regularly. Assuming a Gaussian distribution severely **underestimates tail risk**, which has historically led to massive hedge fund collapses (such as LTCM in 1998).

### 3. Why Quant Traders Strive for Gaussian returns
If Gaussian models are so unrealistic, why does [fx_try.py](file:forex-currency-trading/src/distribution/fx_try.py) attempt to restore normality using **Volume Bars**?
Many of the most powerful and widely used tools in quantitative finance are mathematically predicated on normal distributions:
* **Black-Scholes Option Pricing**: Assumes log-normal price paths.
* **Modern Portfolio Theory (Markowitz)**: Uses mean and variance to optimize portfolios (which breaks down if returns are highly asymmetric or heavy-tailed).
* **Value at Risk (VaR)**: Used by institutions to calculate potential losses.
* **Machine Learning & Linear Models**: Perform significantly better when inputs and targets are normally distributed.

By changing our sampling clock from chronological "time" to transactional "volume", we recover the Gaussian properties of returns. This enables quantitative models to run with much higher stability and reliability.

---

## Methodology & Pipeline

The pipeline implemented in [fx_try.py](forex-currency-trading/src/distribution/fx_try.py) follows these key steps:

### 1. Data Ingestion
- **Asset Selection**: Downloads 1-minute historical data for `SPY` (S&P 500 ETF) over a `5d` (5 days) period via `yfinance`. 
> [!NOTE]
> `SPY` is utilized as a centralized proxy for high-resolution intraday market microstructure analysis, as standard FX tickers (like `EURUSD=X` on Yahoo Finance) lack granular, real-time transaction volume.

### 2. Time Bars
- Log returns are computed at regular 1-minute time intervals:
  $$\text{Time\_Log\_Returns}_t = \ln\left(\frac{P_t}{P_{t-1}}\right)$$

### 3. Volume Bars
- The average 1-minute volume is computed as a baseline: $\overline{V}$.
- A cumulative volume threshold is defined as:
  $$\text{Threshold} = 5 \times \overline{V}$$
- Prices are sampled only when the cumulative transaction volume meets or exceeds this threshold, forming a Volume Bar.
- Log returns are then calculated across these volume-based intervals.

### 4. Normalization & Statistical Tests
- Both return series are standardized ($\mu=0, \sigma=1$) to facilitate comparison.
- **Excess Kurtosis**: Measures the "tailedness" of the distribution. A normal distribution has an excess kurtosis of `0.0`.
- **Jarque-Bera Test**: A goodness-of-fit test testing whether sample data have the skewness and kurtosis matching a normal distribution. A lower statistic indicates a distribution closer to normal.

---

## Prerequisites & Installation

To run this script, ensure you have set up the virtual environment with the project dependencies.

Using [`uv`](https://github.com/astral-sh/uv) (recommended):
```bash
# Sync all dependencies listed in pyproject.toml
uv sync
```

Alternatively, ensure the following Python packages are installed:
- `yfinance`
- `pandas`
- `numpy`
- `scipy`
- `matplotlib`
- `statsmodels`

---

## How to Run

Navigate to the project root directory and execute:
```bash
uv run python src/distribution/fx_try.py
```
Or directly within the `src/distribution` directory:
```bash
python fx_try.py
```

---

## Outputs

### 1. Terminal Metrics
The script prints the statistical comparison table directly to your console:
```text
========================================
             STATISTICAL METRICS
========================================
Time Bars Excess Kurtosis   : 254.5765
Volume Bars Excess Kurtosis : 36.8770
----------------------------------------
Time Bars Jarque-Bera Stat  : 5287102.43
Volume Bars Jarque-Bera Stat: 18172.85
========================================
```
> [!TIP]
> Notice the significant reduction in excess kurtosis and Jarque-Bera statistic when transitioning from Time Bars to Volume Bars. This confirms the returns have transitioned closer to a Gaussian distribution.

### 2. Plots
The script saves a high-resolution plot named `stock_returns_comparison.png` in your current working directory. The plot contains four subplots:
1. **Standard Time Bars Distribution**: Histogram of standardized time returns fitted against a theoretical Gaussian curve.
2. **Transformed Volume Bars Distribution**: Histogram of standardized volume returns fitted against a theoretical Gaussian curve.
3. **Q-Q Plot (Time Bars)**: Quantile-Quantile plot comparing Time Bar return quantiles against normal distribution quantiles.
4. **Q-Q Plot (Volume Bars)**: Quantile-Quantile plot comparing Volume Bar return quantiles against normal distribution quantiles (showing a much tighter alignment with the $45^\circ$ line).

> [!NOTE]
> The $x$-axis (theoretical quantiles) and $y$-axis (sample quantiles) are dynamically aligned and shared between both Q-Q subplots. This allows direct visual comparison of their heavy-tailed behavior and the degree of normal-distribution conformity.
