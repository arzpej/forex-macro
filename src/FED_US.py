"""Project settings. Secrets come from the .env file, never from the code."""

import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


# API keys (read from .env)
FRED_API_KEY = "cfde8ab121aeff8bec8ec4adf4faa0f1"
FRED_URL = "https://api.stlouisfed.org/fred/series/observations"

FOREXFACTORY_URL= "https://nfs.faireconomy.media/ff_calendar_thisweek.json"


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



def get_fred(series, name, start="2010-01-01"):
    params = {
        "series_id": series,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "observation_start": start,
    }
    response = requests.get(FRED_URL, params=params)
    df = pd.DataFrame(response.json()["observations"])[["date", "value"]]
    df["name"] = name
    return df
 
 
def get_all_fred():
    tables = []
    for series, name in FRED_SERIES.items():
        tables.append(get_fred(series, name))
        print("downloaded", name)
    df = pd.concat(tables)
    df.to_csv("data/raw/fred_raw.csv", index=False)
    return df
 
 
def get_calendar():
    response = requests.get(FOREXFACTORY_URL)
    df = pd.DataFrame(response.json())
    df.to_csv("data/raw/ff_calendar.csv", index=False)
    return df

def clean_fred():
    df = pd.read_csv("data/raw/fred_raw.csv")
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")   # "." becomes empty
    df = df.dropna()
    df = df.pivot_table(index="date", columns="name", values="value")  # one column per indicator
    df = df.resample("MS").last().ffill()                               # one row per month
    df.to_csv("data/clean/fred_clean.csv")
    return df
 