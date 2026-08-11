# General Description

This directory is dedicated to storing any data we use in our study: be it raw, downloaded, configured, or cleaned data. 

Currently, there is/are 1 data-storage file(s) within this directory. 

- `MT5CurrencyHistory.h5`: HDF5 file storing raw M30 price history (`TIMEFRAME/M30/<SYMBOL>`), Volume Bars (`VOLUME_BARS/M30/<SYMBOL>`), and Volatility-Normalized Bars (`VOLATILITY_NORMALIZED_BARS/M30/<SYMBOL>`).
- `volatility_bar_transform.py`: Script to process M30 datasets, purge D1 data, construct Volume Bars & Volatility-Normalized Volume Bars, and generate diagnostic distribution and Q-Q plots.
- `EURUSD_M30_return_distributions_and_qq_plots.png`: 6-panel diagnostic plot comparing Return Distributions (Histograms with N(0,1) overlay) and Q-Q plots across Time Bars (M30), Volume Bars, and Volatility-Normalized Volume Bars.
- `EURUSD_M30_volatility_normalized_bars.csv`: CSV export containing the Volatility-Normalized M30 Volume Bars.
- `MT5CurrencyHistory_change_log.csv`: Audit change log tracking dataset operations and bar transformations.
- `fractional_differencing.py`: Script performing Fixed-width Window Fractional Differentiation (FFD) grid search to find minimum d* preserving maximum memory while achieving stationarity (ADF p <= 0.05).
- `fractional_differencing_README.md`: Detailed documentation for `fractional_differencing.py` including theory, API, CLI, and diagnostic plot explanation.
- `EURUSD_M30_fractional_differencing_analysis.png`: 6-panel diagnostic visualization plot for fractional differencing optimization and stationarity trade-offs.
- `EURUSD_M30_fractional_differencing_grid_search.csv`: Grid search results table evaluating ADF stats, p-values, memory loss, and window length across d in [0.0, 1.0].






