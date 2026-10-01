import requests
import pandas as pd
from io import StringIO
from src.FED_US import get_fred               # for GBP/USD
from src.database import last_date, save

COUNTRY = "UK"

ONS_SEARCH = "https://api.beta.ons.gov.uk/v1/search"     # free, no key
ONS_DATA = "https://api.beta.ons.gov.uk/v1/data"
BOE_URL = "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp"   # free, no key


# ONS (Office for National Statistics) -> "NAME": (CDID code, dataset)
ONS_SERIES = {
    # --- Inflation ---
    "CPI": ("D7G7", "MM23"),                 # CPI, % per year
    "CORE_CPI": ("DKO8", "MM23"),            # CPI without energy, food, alcohol, tobacco, % per year

    # --- Growth ---
    "REAL_GDP": ("ABMI", "QNA"),             # Real GDP (quarterly)
    "INDUSTRIAL_PROD": ("K222", "DIOP"),     # Industrial production index
    "RETAIL_SALES": ("J5EK", "DRSI"),        # Retail sales volume index

    # --- Jobs ---
    "UNEMPLOYMENT": ("MGSX", "LMS"),         # Unemployment rate
    "WAGES": ("KAC3", "LMS"),                # Average weekly earnings growth, %
}

# Bank of England -> "NAME": series code
BOE_SERIES = {
    # --- Interest rates ---
    "POLICY_RATE": "IUDBEDR",                # Bank Rate
    "YIELD_10Y": "IUDMNZC",                  # 10-year gilt yield
}

# FRED -> "NAME": FRED code
FRED_SERIES = {
    # --- Markets ---
    "GBPUSD": "DEXUSUK",                     # US dollars per 1 pound
}


def get_ons(cdid, dataset):
    # step 1: find the address of the series
    search = requests.get(ONS_SEARCH, params={"content_type": "timeseries", "cdids": cdid.lower()}).json()
    uri = [item["uri"] for item in search["items"] if item["uri"].endswith("/" + dataset.lower())][0]
    # step 2: download it
    data = requests.get(ONS_DATA, params={"uri": uri}).json()
    if data["months"]:
        df = pd.DataFrame(data["months"])[["date", "value"]]
        df["date"] = pd.to_datetime(df["date"].str.title(), format="%Y %b").dt.strftime("%Y-%m-%d")   # "2024 JAN"
    else:
        df = pd.DataFrame(data["quarters"])[["date", "value"]]
        df["date"] = df["date"].str.replace(" ", "")                                                # "2024 Q1" -> "2024Q1"
    return df


def get_boe(code, start):
    params = {
        "csv.x": "yes",
        "Datefrom": pd.to_datetime(start).strftime("%d/%b/%Y"),
        "Dateto": "now",
        "SeriesCodes": code,
        "CSVF": "TN",
        "UsingCodes": "Y",
        "VPD": "Y",
        "VFD": "N",
    }
    response = requests.get(BOE_URL, params=params, headers={"User-Agent": "Mozilla/5.0"})
    df = pd.read_csv(StringIO(response.text))
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"], dayfirst=True).dt.strftime("%Y-%m-%d")    # "02 Jan 2010"
    return df


def update_uk():
    for name, (cdid, dataset) in ONS_SERIES.items():
        try:
            df = get_ons(cdid, dataset)           # ONS always sends full history; save() keeps only new dates
            added = save(df, name, COUNTRY, "ONS")
            print(COUNTRY, name, "new rows:", added)
        except Exception as error:
            print("FAILED", COUNTRY, name, "->", error)

    for name, code in BOE_SERIES.items():
        try:
            start = last_date(name, COUNTRY) or "2010-01-01"
            df = get_boe(code, start)
            added = save(df, name, COUNTRY, "BOE")
            print(COUNTRY, name, "new rows:", added)
        except Exception as error:
            print("FAILED", COUNTRY, name, "->", error)

    for name, code in FRED_SERIES.items():
        start = last_date(name, COUNTRY) or "2010-01-01"
        df = get_fred(code, start)
        added = save(df, name, COUNTRY, "FRED")
        print(COUNTRY, name, "new rows:", added)
