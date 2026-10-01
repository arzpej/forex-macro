import requests
import pandas as pd
from io import StringIO

# ECB Data Portal API - free, no key needed
ECB_URL = "https://data-api.ecb.europa.eu/service/data/"


# What to download (Eurozone versions of FRED_SERIES)
ECB_SERIES = {
    # --- Inflation ---
    "HICP.M.U2.N.000000.4D0.ANR": "ez_hicp",                       # HICP inflation, % per year
    "HICP.M.U2.N.XEF000.4D0.ANR": "ez_core_hicp",                  # Core HICP (no energy, food, alcohol, tobacco), % per year
    "STBS.M.I10.N.PRIN.NS0020.4D0.N.IX": "ez_ppi",                 # Producer Price Index

    # --- Growth ---
    "MNA.Q.Y.I9.W2.S1.S1.B.B1GQ._Z._Z._Z.EUR.LR.N": "ez_real_gdp", # Real GDP (quarterly)
    "STBS.M.I10.Y.PROD.NS0020.4D0.N.IX": "ez_industrial_prod",     # Industrial production
    "STBS.M.I10.Y.TOVV.2G4700.4D0.N.IX": "ez_retail_sales",        # Retail sales (volume)

    # --- Jobs ---
    "LFSI.M.I9.S.UNEHRT.TOTAL0.15_74.T": "ez_unemployment",        # Unemployment rate

    # --- Interest rates ---
    "FM.D.U2.EUR.4F.KR.DFR.LEV": "ecb_rate",                       # ECB deposit rate
    "YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y": "ez_2y_yield",           # Euro area 2-year yield (AAA)
    "YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y": "ez_10y_yield",         # Euro area 10-year yield (AAA)

    # --- Markets ---
    "EXR.D.USD.EUR.SP00.A": "eurusd_ecb",                          # EUR/USD (ECB reference rate)
}


def get_ecb(series, name, start="2010-01-01"):
    dataset, key = series.split(".", 1)          # "HICP.M.U2..." -> "HICP" and "M.U2..."
    url = f"{ECB_URL}{dataset}/{key}"
    params = {"format": "csvdata", "startPeriod": start}
    response = requests.get(url, params=params)
    df = pd.read_csv(StringIO(response.text))[["TIME_PERIOD", "OBS_VALUE"]]
    df.columns = ["date", "value"]
    df["date"] = (df["date"].str.replace("-Q1", "-01").str.replace("-Q2", "-04")
                            .str.replace("-Q3", "-07").str.replace("-Q4", "-10"))   # quarters -> months
    df["name"] = name
    return df


def get_all_ecb():
    tables = []
    for series, name in ECB_SERIES.items():
        tables.append(get_ecb(series, name))
        print("downloaded", name)
    df = pd.concat(tables)
    df.to_csv("data/raw/ecb_raw.csv", index=False)
    return df


def clean_ecb():
    df = pd.read_csv("data/raw/ecb_raw.csv")
    df["date"] = pd.to_datetime(df["date"], format="ISO8601")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna()
    df = df.pivot_table(index="date", columns="name", values="value")  # one column per indicator
    df = df.resample("MS").last().ffill()                               # one row per month
    df.to_csv("data/clean/ecb_clean.csv")
    return df
 