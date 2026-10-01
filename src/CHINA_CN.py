import pandas as pd
import nbsc                                   # pip install git+https://github.com/mbk-dev/nbsc.git
from src.FED_US import get_fred               # same FRED key as the US module
from src.database import last_date, save

COUNTRY = "China"

CHINA_FRED = {
    # --- Growth ---
    "CHNLOLITOAASTSAM": "LEADING_INDEX",           # OECD leading indicator

    # --- Interest rates ---
    "IR3TIB01CNM156N": "INTERBANK_3M",             # 3-month interbank rate

    # --- Markets ---
    "DEXCHUS": "USDCNY",                           # Yuan per 1 US dollar
    "RBCNBIS": "REAL_FX_INDEX",                    # Real effective exchange rate
}

CHINA_NBS = {
    # --- Inflation ---
    "CPI": (nbsc.get_annual_inflation, "2010"),                   # vs same month last year (0.012 = +1.2%)
    "PPI": (nbsc.get_ppi_yoy, "2010"),                            # same month last year = 100

    # --- Growth ---
    "REAL_GDP": (nbsc.get_gdp_real, "2011"),                      # quarterly
    "GDP_GROWTH": (nbsc.get_gdp_index, "2010"),                   # same quarter last year = 100
    "PMI_MANUFACTURING": (nbsc.get_manufacturing_pmi, "2010"),
    "PMI_SERVICES": (nbsc.get_non_manufacturing_pmi, "2010"),

    # --- Jobs ---
    "UNEMPLOYMENT": (nbsc.get_unemployment_rate, "2018"),         # starts 2018

    # --- Money ---
    "M2": (nbsc.get_m2_yoy, "2010"),                              # % growth per year
}


def get_nbs(func, year):
    data = func(year)
    if isinstance(data, pd.DataFrame):
        data = data.iloc[:, 0]                     # keep the first column only
    return pd.DataFrame({"date": data.index.astype(str), "value": data.values})


def update_china():
    for series, name in CHINA_FRED.items():
        start = last_date(name, COUNTRY) or "2010-01-01"
        df = get_fred(series, start)
        added = save(df, name, COUNTRY, "FRED")
        print(COUNTRY, name, "new rows:", added)

    for name, (func, first_year) in CHINA_NBS.items():
        start = last_date(name, COUNTRY)
        year = start[:4] if start else first_year     # NBS works with years
        try:
            df = get_nbs(func, year)
            added = save(df, name, COUNTRY, "NBS")
            print(COUNTRY, name, "new rows:", added)
        except Exception as error:
            print("FAILED", COUNTRY, name, "->", error)     # one bad series does not stop the rest