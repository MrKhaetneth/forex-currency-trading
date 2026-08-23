#!/usr/bin/env python3
"""
Volatility-Sampled Bars Transformation Entrypoint
================================================
Runs dataset/volatility_bar_transform.py for D1 datasets.
"""

import sys
from pathlib import Path
import subprocess

SCRIPT_DIR = Path(__file__).resolve().parent
TARGET_SCRIPT = SCRIPT_DIR / "volatility_bar_transform.py"

if __name__ == "__main__":
    cmd = [sys.executable, str(TARGET_SCRIPT)] + sys.argv[1:]
    sys.exit(subprocess.run(cmd).returncode)
