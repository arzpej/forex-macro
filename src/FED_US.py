import os
import requests
import pandas as pd
from dotenv import load_dotenv
from src.database import last_date, save

load_dotenv()

FRED_API_KEY = "cfde8ab121aeff8bec8ec4adf4faa0f1"
FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
FOREXFACTORY_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

COUNTRY = "US"

FRED_SERIES = {
    # --- Inflation ---
    "CPIAUCSL": "CPI",                       # Consumer Price Index
    "CPILFESL": "CORE_CPI",                  # Core CPI (no food and energy)
    "PPIFIS": "PPI",                         # Producer Price Index (Final Demand)
    "PCEPI": "PCE",                          # PCE - the Fed's favourite inflation measure
    "PCEPILFE": "CORE_PCE",                  # Core PCE

    # --- Growth ---
    "GDPC1": "REAL_GDP",                     # Real GDP (quarterly)
    "INDPRO": "INDUSTRIAL_PROD",             # Industrial production
    "RSAFS": "RETAIL_SALES",                 # Retail sales
    "UMCSENT": "CONSUMER_SENTIMENT",         # Consumer sentiment

    # --- Jobs ---
    "PAYEMS": "NFP",                         # Non-Farm Payrolls
    "UNRATE": "UNEMPLOYMENT",                # Unemployment rate
    "ICSA": "JOBLESS_CLAIMS",                # Weekly jobless claims

    # --- Interest rates ---
    "FEDFUNDS": "POLICY_RATE",               # Fed Funds rate
    "DGS2": "YIELD_2Y",                      # 2-year yield
    "DGS10": "YIELD_10Y",                    # 10-year yield
    "T10Y2Y": "YIELD_CURVE",                 # 10-year minus 2-year

    # --- Markets ---
    "DEXUSEU": "EURUSD",                     # EUR/USD
    "DTWEXBGS": "USD_INDEX",                 # US Dollar Index (Broad)
    "VIXCLS": "VIX",                         # Market fear index
}


def get_fred(series, start):
    params = {
        "series_id": series,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "observation_start": start,
    }
    response = requests.get(FRED_URL, params=params)
    return pd.DataFrame(response.json()["observations"])[["date", "value"]]


def update_fred():
    for series, name in FRED_SERIES.items():
        start = last_date(name, COUNTRY) or "2010-01-01"     # only ask for what we don't have yet
        df = get_fred(series, start)
        added = save(df, name, COUNTRY, "FRED")
        print(COUNTRY, name, "new rows:", added)


def get_calendar():
    response = requests.get(FOREXFACTORY_URL)
    df = pd.DataFrame(response.json())
    df.to_csv("data/raw/ff_calendar.csv", index=False)
    return df