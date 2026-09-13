# ---------- FILE DESCRIPTION ----------
f"""({__name__}'s file description.) 
This module contains logging functions to keep track of changes within the local repo.
"""

# -------- IMPORTS ----------
import MetaTrader5 as mt5
import pandas as pd
import subprocess
import pytz
import csv

from datetime import datetime
from pathlib import Path

from fx.connection import mt5_connection

# -------- CONSTANTS ----------
_TIMEZONE = pytz.timezone("Etc/UTC")
_LOG_COLUMNS = ["LOG_TIME", "ACTION", "BY", "SYMBOL", "TIMEFRAME", "TCST", "TCET"]

# -------- FUNCTIONS ----------
# Get local git username
def get_gitusername() -> str:
    try:
        process_result = subprocess.run(
            ["git", "config", "user.name"],
            stdout = subprocess.PIPE,
            text   = True,
            check  = True)
        git_username = process_result.stdout.strip()
        return git_username
    except Exception as err:
        print(f"<ERROR> {err}")
        return "Unknown"