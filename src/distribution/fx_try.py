import yfinance as yf
import pandas as pd
import numpy as np
import scipy.stats as stats
import matplotlib.pyplot as plt
import statsmodels.api as sm

# 1. Download Real 1-Minute FX Data
print("Fetching real 1-minute EUR/USD data...")
# Switch to a centralized asset that registers real volume per minute
ticker = "SPY"
data = yf.download(tickers=ticker, period="5d", interval="1m") # 5 days of 1-minute data for SPY as a proxy for FX volume analysis

if data.empty:
    raise ValueError("No data retrieved. Check internet connection or ticker.")

# Clean multi-index columns if present
if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)

# Extract Close price and Volume
df = data[['Close', 'Volume']].dropna().copy()

# 2. Generate Standard Time Bar Returns
#negative when price goes down, positive when price goes up, zero when price is unchanged
# Why? Why is this parameter important and what does it imply?
df['Time_Log_Returns'] = np.log(df['Close'] / df['Close'].shift(1))
time_returns = df['Time_Log_Returns'].dropna().to_numpy() 

# 3. Construct Custom Volume Bars
# We define a volume threshold based on the average volume per minute
avg_minute_volume = df['Volume'].mean()
volume_threshold = avg_minute_volume * 5  # Aggregate roughly every 5 minutes of volume activity

volume_bars_close = []
current_vol = 0.0
last_close = df['Close'].iloc[0]

for idx, row in df.iterrows():
    current_vol += row['Volume']
    if current_vol >= volume_threshold:
        volume_bars_close.append(row['Close'])
        current_vol = 0.0

# Generate Volume Bar Returns
vol_df = pd.DataFrame({'Close': volume_bars_close})
vol_df['Vol_Log_Returns'] = np.log(vol_df['Close'] / vol_df['Close'].shift(1))
volume_returns = vol_df['Vol_Log_Returns'].dropna().to_numpy()

# Standardize returns (mean=0, stdev=1) to allow direct comparison on a normal curve
time_returns_std = (time_returns - np.mean(time_returns)) / np.std(time_returns)
volume_returns_std = (volume_returns - np.mean(volume_returns)) / np.std(volume_returns)

# 4. Statistical Metrics Output
print("\n" + "="*40)
print("             STATISTICAL METRICS")
print("="*40)
print(f"Time Bars Excess Kurtosis   : {stats.kurtosis(time_returns, fisher=True):.4f}") # fisher=True gives excess kurtosis (subtracts 3)
print(f"Volume Bars Excess Kurtosis : {stats.kurtosis(volume_returns, fisher=True):.4f}")
print("-"*40)
print(f"Time Bars Jarque-Bera Stat  : {stats.jarque_bera(time_returns)[0]:.2f}")
print(f"Volume Bars Jarque-Bera Stat: {stats.jarque_bera(volume_returns)[0]:.2f}")
print("="*40)

# 5. Plotting the Distributions vs. Theoretical Gaussian
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
x_axis = np.linspace(-5, 5, 500) 
gaussian_pdf = stats.norm.pdf(x_axis, 0, 1)

# Histogram: Time Bars
axes[0, 0].hist(time_returns_std, bins=80, density=True, alpha=0.6, color='crimson', label='Time Returns')
axes[0, 0].plot(x_axis, gaussian_pdf, 'k--', linewidth=2, label='Normal Distribution')
axes[0, 0].set_xlim([-5, 5])
axes[0, 0].set_title(f"Standard Time Bars Distribution\n(Excess Kurtosis: {stats.kurtosis(time_returns):.2f})")
axes[0, 0].legend()
axes[0, 0].grid(True, alpha=0.3)

# Histogram: Volume Bars
axes[0, 1].hist(volume_returns_std, bins=80, density=True, alpha=0.6, color='teal', label='Volume Returns')
axes[0, 1].plot(x_axis, gaussian_pdf, 'k--', linewidth=2, label='Normal Distribution')
axes[0, 1].set_xlim([-5, 5])
axes[0, 1].set_title(f"Transformed Volume Bars Distribution\n(Excess Kurtosis: {stats.kurtosis(volume_returns):.2f})")
axes[0, 1].legend()
axes[0, 1].grid(True, alpha=0.3)

# Q-Q Plot: Time Bars
sm.qqplot(time_returns_std, line='45', ax=axes[1, 0], fmt='.', color='crimson', alpha=0.5)
axes[1, 0].set_title("Q-Q Plot: Standard Time Bars")
axes[1, 0].grid(True, alpha=0.3)

# Q-Q Plot: Volume Bars
sm.qqplot(volume_returns_std, line='45', ax=axes[1, 1], fmt='.', color='teal', alpha=0.5)
axes[1, 1].set_title("Q-Q Plot: Transformed Volume Bars")
axes[1, 1].grid(True, alpha=0.3)

# Align x and y axes for Q-Q plots to enable direct visual comparison
qq_xlim = (
    min(axes[1, 0].get_xlim()[0], axes[1, 1].get_xlim()[0]),
    max(axes[1, 0].get_xlim()[1], axes[1, 1].get_xlim()[1])
)
qq_ylim = (
    min(axes[1, 0].get_ylim()[0], axes[1, 1].get_ylim()[0]),
    max(axes[1, 0].get_ylim()[1], axes[1, 1].get_ylim()[1])
)
for ax in [axes[1, 0], axes[1, 1]]:
    ax.set_xlim(qq_xlim)
    ax.set_ylim(qq_ylim)

plt.tight_layout()
plt.savefig("stock_returns_comparison.png", dpi=300)
plt.show()