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
FRED_API_KEY = "cfde8ab121aeff8bec8ec4adf4faa0f1"
FED_url = "https://api.stlouisfed.org/fred/series/observations"

FOREXFACTORY_URL= "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

OANDA_TOKEN = "b6011d88fcef69b5cababa48d5e8d12d-8ed494a8062925240b9093fbb70549a1"
OANDA_ACCOUNT_ID="101-011-40520853-001"
OANDA_URL="https://api-fxpractice.oanda.com"

# What to download


FRED_SERIES = {
    # --- Inflation ---
    "CPIAUCSL":  "us_cpi",               # US Consumer Price Index
    "CPILFESL":  "us_core_cpi",          # Core CPI (no food and energy)
    "PPIFIS":    "us_ppi",               # Producer Price Index (Final Demand)
    "PCEPI":     "us_pce",               # PCE - the Fed's favourite inflation measure
    "PCEPILFE":  "us_core_pce",          # Core PCE
    "CP0000EZ19M086NEST": "ez_hicp",     # Eurozone inflation (HICP)

    # --- Growth ---
    "GDPC1":     "us_real_gdp",          # Real GDP (quarterly)
    "INDPRO":    "us_industrial_prod",   # Industrial production
    "RSAFS":     "us_retail_sales",      # Retail sales
    "UMCSENT":   "us_consumer_sentiment",# Consumer sentiment

    # --- Jobs ---
    "PAYEMS":    "us_nfp",               # Non-Farm Payrolls
    "UNRATE":    "us_unemployment",      # Unemployment rate
    "ICSA":      "us_jobless_claims",    # Weekly jobless claims

    # --- Interest rates ---
    "FEDFUNDS":  "fed_rate",             # Fed Funds rate
    "ECBDFR":    "ecb_rate",             # ECB deposit rate
    "DGS2":      "us_2y_yield",          # US 2-year yield
    "DGS10":     "us_10y_yield",         # US 10-year yield
    "IRLTLT01DEM156N": "de_10y_yield",   # Germany 10-year yield
    "T10Y2Y":    "us_yield_curve",       # Yield curve (10-year minus 2-year)

    # --- Markets ---
    "DEXUSEU":   "eurusd",               # EUR/USD exchange rate
    "DTWEXBGS":  "usd_index",            # US Dollar Index (Broad)
    "VIXCLS":    "vix",                  # Market fear index
}



START_DATE = "2010-01-01"

