# Author's Notes

This specific directory of this repository is dedicated to files that works only in WindowsOS. If you try to run any of these files on your computer whose OS is not Window, it may crash and result in errors, e.g. installing MetaTrader5 on Linux when you try to run 

```bash
$ uv sync # if the pyproject.toml is not written properly in the dependency section
$ uv run python_window_file.py # if the file contains libraries available only for WindowsOS
```

However, at the time I'm writing this (Khaetneth, 29/06/2026 18:22 GMT+07) I have already configured the `pyproject.toml` file so that `MetaTrader5` is only installed for WindowsOS.