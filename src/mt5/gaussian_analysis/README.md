# MT5 Forex Return Normality & Volatility Analysis

This folder serves as a pedagogical research sandbox to study the statistical behavior of high-frequency foreign exchange returns (`EURUSD`). 

The central question we address is: **Why do financial returns violate the Gaussian (normal) distribution assumptions, and how can we use market microstructure and volatility models to restore normality?**

---

## 🚀 Execution Guide

Run the normality comparison script using `uv` from the repository root directory (`{HOME_DIRECTORY}/undergrad/fx_analysis/forex-currency-trading`):

```bash
# Compare all normalization methods (Time, Volume, Dollar, Vol-Std Time, Vol-Std Volume)
uv run src/mt5/gaussian_analysis/mt5_advanced_normalization.py
```

---

## 📖 Pedagogical Roadmap: From Raw Prices to Gaussian Returns

### Step 1: Why We Calculate Log Returns
Raw exchange rates (closing prices $P_t$) are non-stationary—they trend, drift, and are highly dependent on their starting value. To perform statistical distribution analysis, we must work with **returns**. 

In quantitative finance, we use **log returns** instead of simple percentage returns:
$$R_t = \ln\left(\frac{P_t}{P_{t-1}}\right)$$

* **Mathematical Property:** Log returns are time-additive. Summing the log returns of five consecutive minutes yields the exact log return of the entire 5-minute block. Consider a set of $n$ closing prices, $C=\{P_0,P_1,\cdots,P_n\}$, with each closing price being $\Delta T$ apart in time. So, the entire set $C$ spans over $n\Delta T$ in time. If $P_t = P_{t-1}$ then $R_t = 0$; $P_t < P_{t-1}$ then $R_t < 0$; $P_t > P_{t-1}$ then $R_t > 0$. 

  But you might wonder why it's not $R_t = P_t - P_{t-1}$ or the **simple return** $R(t) = P_t/P_{t-1} - 1$. Well, if $R_t = P_t - P_{t-1}$, sure it might satisfy the *time-additive* property: $P_t - P_{t-2} = R_t + R_{t-1}$. But then it would be just price difference, if the difference in price is very minute or very large, the quantity $P_t - P_{t-1}$ wouldn't exactly capture the sheer difference between $P_t$ and $P_{t-1}$. 

  As for the simple return, consider the case where $(P_0,P_1,P_2) = (100, 110, 99)$. There are three simple returns we can define from this $P_0,P_1,$ and $P_2$. Over a single time interval, we have 

  $$ R(P_0,P_1) = \frac{P_1}{P_0} - 1 = 10\% ,\quad R(P_2,P_1) = \frac{P_2}{P_1} - 1 = -10\%,\quad\text{and}\quad R(P_2,P_0) = \frac{P_2}{P_0} - 1 = -1\% $$

  But this is not time-additive: $-1\% = R(P_2,P_0) \neq R(P_2,P_1) + R(P_1, P_0) = 10\% - 10\% = 0\%$. Thus, we chose $R_t = \ln(P_t/P_{t-1})$ because it encapsulates the difference in scale between $P_t$ and $P_{t-1}$ comprehensibly and it's time-additive. The mathematical form isn't too intimidating too. In general, we also have that 

  $$ \ln \frac{P_n}{P_0} = \sum_{t=1}^{n\Delta T} R_t $$

  Also, if $1 + r(t) = P_t/P_{t-1}$, where $r(t)$ is the simple return, then we may approximate $R_t = \ln(1 + r(t)) \simeq r(t)$ for a small enough $r(t)$.


* **Code Implementation**:
  ```python
  df['Time_Log_Returns'] = np.log(df['close'] / df['close'].shift(1))
  ```

---

### Step 2: Slicing by Time vs. Transaction Volume (MDH)
Standard charts slice data by chronological clock-time (e.g., a new bar every 1 minute). However, the rate of information arrival in the market is not constant—trading is dense during London/New York hours and virtually non-existent during quiet periods.

When you force returns into arbitrary clock-time steps, you get massive outlier price jumps (during announcements) and periods of zero movement. This is called the **Mixture of Distributions Hypothesis (MDH)**. Lumping these different market states together creates a return distribution with an extremely tall peak and fat tails (**leptokurtosis**), yielding an excess kurtosis of **~300**!

To resolve this, we construct alternative bar sizes:
1. **Volume Bars**: Group data by a constant number of transaction units (e.g., every 1,000 ticks).
2. **Dollar Bars (Notional Value)**: Group data by a constant monetary size:
   $$\text{Notional Value} = \text{Price} \times \text{Volume}$$
   A new bar is formed when the cumulative transacted value reaches a threshold. This keeps the economic transaction size constant as price levels change.

#### Result
Sampling returns in transaction space (Volume/Dollar Bars) filters out the noise of inactive clock time, reducing the excess kurtosis by roughly **90%** (bringing it down from ~298 to ~32).

---

### Step 3: Understanding Market Microstructure Gaps at Zero
If you plot a high-resolution histogram of 1-minute time-bar returns, you will see a massive vertical spike at exactly $0.0$, surrounded by a relative "canyon" (vacuum) on either side. This is caused by:
1. **Zero-Return Minutes**: In quiet minutes, the exchange rate does not move. The return is exactly $0.0$.
2. **Price Discretization**: Exchange rates move in discrete steps called ticks (for `EURUSD`, the minimum tick is $0.00001$). A price change is either $0$ or at least $\pm 1$ tick ($\approx \pm 0.000009$). There are no fractional ticks (like $0.5$ ticks), leaving a structural gap immediately surrounding $0$.

*Volume and Dollar bars naturally fix this* because they skip inactive clock minutes and only sample when trades actually occur.

---

### Step 4: Stripping Volatility Clustering (The Volatility Accordion)
Even in volume space, returns still exhibit **volatility clustering** (periods of high volatility tend to follow high volatility). This time-varying variance is called **heteroskedasticity**.

If we assume returns are a product of conditional volatility ($\sigma_t$) and a standardized random shock ($Z_t$):
$$R_t = \sigma_t \cdot Z_t$$

We can isolate the stationary shock $Z_t$ by dividing the returns by their conditional volatility:
$$Z_t = \frac{R_t}{\sigma_t}$$

This division behaves like an **accordion**:
* During volatile periods, $\sigma_t$ is large $\rightarrow$ it **compresses** the massive return spikes.
* During quiet periods, $\sigma_t$ is small $\rightarrow$ it **stretches (amplifies)** the small returns.

Standardizing the returns by their conditional volatility (either using a rolling standard deviation or GARCH) eliminates the fat tails, yielding an excess kurtosis of **$< 1.0$**—a nearly perfect normal Gaussian distribution.

---

### Step 5: Estimating Volatility using GARCH(1,1) MLE
To find the volatility $\sigma_t$ at any step, we fit a **GARCH(1,1) model**:
$$\sigma^2_t = \omega + \alpha R^2_{t-1} + \beta \sigma^2_{t-1}$$
* **$\omega$ (omega)**: Baseline constant variance.
* **$\alpha$ (alpha)**: Sensitivity to recent price shocks (yesterday's squared return $R_{t-1}^2$).
* **$\beta$ (beta)**: Volatility persistence (remembers yesterday's volatility $\sigma_{t-1}^2$).
* **$\alpha + \beta < 1$**: Must hold to prevent volatility from exploding to infinity.

#### Numerical Optimization Implementation:
Because the equation is recursive, we use SciPy's `L-BFGS-B` numerical optimizer to search for the parameter values that maximize the **Log-Likelihood ($LL$) function**:
$$LL(\omega, \alpha, \beta) = -\frac{1}{2} \sum_{t=1}^{T} \left( \ln(2\pi) + \ln(\sigma_t^2) + \frac{R_t^2}{\sigma_t^2} \right)$$

---

## 🔬 Optimization & Arithmetic Insights

### 1. Return Scaling
Because log returns are tiny ($\sim 10^{-5}$), squaring them drops values close to zero ($\sim 10^{-10}$), causing numerical optimizers to crash. The script multiplies returns by $100$ (percentage scale) before optimization to ensure convergence, and then rescales $\omega$ back down.

### 2. Jarque-Bera $p$-value Underflow
The Jarque-Bera normality test statistic grows with sample size. For $20,000$ observations, a large test statistic yields a $p$-value of $e^{-44,000}$. Since double-precision floats underflow below $10^{-308}$, the computer outputs exactly $0.00\text{e}+00$. The script formats this as `< 1e-300` to prevent confusion.

---

## 📂 Output Files Generated (Saved in `analysis_results/`)

All output results are saved dynamically in the `analysis_results/` subfolder in this directory:
* **`analysis_results/garch_parameters.json`**: Compiles the estimated GARCH model parameters ($\omega$, $\alpha$, $\beta$, and long-term annual volatility) along with the full statistical comparison metrics (Observations, Skewness, Kurtosis, JB stats) for all 5 methods.
* **`analysis_results/eurusd_advanced_normalization.png`**: Generates return distribution histograms and aligned Q-Q plots comparing raw **Volume Bars** vs. **Volatility-Standardized Volume Bars**.
* **`analysis_results/eurusd_kurtosis_qq.png`**: (From base analysis) Historical price returns distribution vs. Normal Gaussian.
* **`analysis_results/eurusd_time_vs_volume_comparison.png`**: (From time vs. volume bar analysis) Visual comparison of Time Bars against Volume Bars.