import pandas as pd
import nbsc                        # a
from src.FED_US import get_fred    # same FRED key as the US module


# What to download (China) - same groups as FRED_SERIES in FED_US.py
# FRED series   ->  "FRED code": "name"
# NBS series    ->  "name": (nbsc function, first year)

CHINA_FRED = {
    # --- Growth ---
    "CHNLOLITOAASTSAM": "cn_leading_index",        # OECD leading indicator for China

    # --- Interest rates ---
    "IR3TIB01CNM156N": "cn_3m_interbank",          # 3-month interbank rate (like fed_rate)

    # --- Markets ---
    "DEXCHUS": "usdcny",                           # Yuan per 1 US dollar (like eurusd)
    "RBCNBIS": "cn_real_fx_index",                 # Real effective exchange rate (like usd_index)
}

CHINA_NBS = {
    # --- Inflation ---
    "cn_cpi_yoy": (nbsc.get_annual_inflation, "2010"),          # like us_cpi (0.012 = +1.2%)
    "cn_ppi_yoy": (nbsc.get_ppi_yoy, "2010"),                   # like us_ppi (same month last year = 100)

    # --- Growth ---
    "cn_real_gdp": (nbsc.get_gdp_real, "2011"),                 # like us_real_gdp (quarterly)
    "cn_gdp_growth": (nbsc.get_gdp_index, "2010"),              # GDP, same quarter last year = 100
    "cn_pmi_manufacturing": (nbsc.get_manufacturing_pmi, "2010"),  # like US ISM manufacturing
    "cn_pmi_services": (nbsc.get_non_manufacturing_pmi, "2010"),   # like US ISM services

    # --- Jobs ---
    "cn_unemployment": (nbsc.get_unemployment_rate, "2018"),    # like us_unemployment (starts 2018)

    # --- Money ---
    "cn_m2_yoy": (nbsc.get_m2_yoy, "2010"),                     # money supply growth, %
}


def get_nbs(name, func, start):
    data = func(start)
    if isinstance(data, pd.DataFrame):
        data = data.iloc[:, 0]                     # keep the first column only
    df = pd.DataFrame({"date": data.index.astype(str), "value": data.values})
    df["name"] = name
    return df


def get_all_china():
    tables = []

    for series, name in CHINA_FRED.items():
        df = get_fred(series, name)
        tables.append(df)
        print("downloaded", name, "last date:", df["date"].iloc[-1])

    for name, (func, start) in CHINA_NBS.items():
        try:
            df = get_nbs(name, func, start)
            tables.append(df)
            print("downloaded", name, "last date:", df["date"].iloc[-1])
        except Exception as error:
            print("FAILED", name, "->", error)     # one bad series does not stop the rest

    df = pd.concat(tables)
    df.to_csv("data/raw/china_raw.csv", index=False)
    return df


def clean_china():
    df = pd.read_csv("data/raw/china_raw.csv")
    df["date"] = (df["date"].str.replace("Q1", "-01").str.replace("Q2", "-04")
                            .str.replace("Q3", "-07").str.replace("Q4", "-10"))   # quarters -> months
    df["date"] = pd.to_datetime(df["date"], format="ISO8601")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna()
    df = df.pivot_table(index="date", columns="name", values="value")  # one column per indicator
    df = df.resample("MS").last().ffill()                               # one row per month
    df.to_csv("data/clean/china_clean.csv")
    return df
