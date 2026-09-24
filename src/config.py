"""Project settings. Secrets come from the .env file, never from the code."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Folders
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
LOG_DIR = PROJECT_ROOT / "logs"

# API keys (read from .env)
FRED_API_KEY = os.getenv("FRED_API_KEY", "")
OANDA_TOKEN = os.getenv("OANDA_TOKEN", "")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID", "")
OANDA_ENV = os.getenv("OANDA_ENV", "practice")  # "practice" or "live"

# What to download
FRED_SERIES = {
    "DEXUSEU": "EUR/USD exchange rate (daily)",
    "FEDFUNDS": "Fed Funds rate (monthly)",
    "ECBDFR": "ECB deposit facility rate (daily)",
    "DGS10": "US 10-year Treasury yield (daily)",
    "IRLTLT01DEM156N": "Germany 10-year yield (monthly)",
    "CPIAUCSL": "US CPI (monthly)",
    "UNRATE": "US unemployment rate (monthly)",
    "T10Y2Y": "US yield curve 10Y-2Y (daily)",
}

YAHOO_TICKERS = {
    "EURUSD=X": "EUR/USD",
    "DX-Y.NYB": "US Dollar Index (DXY)",
    "^VIX": "VIX volatility index",
    "^GSPC": "S&P 500",
    "GC=F": "Gold futures",
}

START_DATE = "2010-01-01"
