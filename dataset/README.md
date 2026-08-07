# General Description

This directory is dedicated to storing any data we use in our study: be it raw, downloaded, configured, or cleaned data. 

Currently, there is/are 1 data-storage file(s) within this directory. 

- `MetaTrader5CurrencyHistory.h5`: This HDF5 file stores various currency pairs' prices history. The contents within this file is grouped by timeframe (5 year, 1 year, etc.) and withn each timeframe are the prices in a currency pair's history. This file was first created/initialized from `src/mt5/data_management/add_symbol.py`.
