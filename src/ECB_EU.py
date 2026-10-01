import requests
import pandas as pd
from io import StringIO
from src.database import last_date, save

ECB_URL = "https://data-api.ecb.europa.eu/service/data/"     # free, no key

COUNTRY = "Euro"

ECB_SERIES = {
    # --- Inflation ---
    "HICP.M.U2.N.000000.4D0.ANR": "CPI",                               # HICP inflation, % per year
    "HICP.M.U2.N.XEF000.4D0.ANR": "CORE_CPI",                          # Core HICP, % per year
    "STBS.M.I10.N.PRIN.NS0020.4D0.N.IX": "PPI",                        # Producer Price Index

    # --- Growth ---
    "MNA.Q.Y.I9.W2.S1.S1.B.B1GQ._Z._Z._Z.EUR.LR.N": "REAL_GDP",       # Real GDP (quarterly)
    "STBS.M.I10.Y.PROD.NS0020.4D0.N.IX": "INDUSTRIAL_PROD",            # Industrial production
    "STBS.M.I10.Y.TOVV.2G4700.4D0.N.IX": "RETAIL_SALES",               # Retail sales (volume)

    # --- Jobs ---
    "LFSI.M.I9.S.UNEHRT.TOTAL0.15_74.T": "UNEMPLOYMENT",               # Unemployment rate

    # --- Interest rates ---
    "FM.D.U2.EUR.4F.KR.DFR.LEV": "POLICY_RATE",                        # ECB deposit rate
    "YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y": "YIELD_2Y",                  # 2-year yield (AAA)
    "YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y": "YIELD_10Y",                # 10-year yield (AAA)
}


def get_ecb(series, start):
    dataset, key = series.split(".", 1)          # "HICP.M.U2..." -> "HICP" and "M.U2..."
    url = f"{ECB_URL}{dataset}/{key}"
    params = {"format": "csvdata", "startPeriod": start}
    response = requests.get(url, params=params)
    df = pd.read_csv(StringIO(response.text))[["TIME_PERIOD", "OBS_VALUE"]]
    df.columns = ["date", "value"]
    return df


def update_ecb():
    for series, name in ECB_SERIES.items():
        start = last_date(name, COUNTRY) or "2010-01-01"     # only ask for what we don't have yet
        df = get_ecb(series, start)
        added = save(df, name, COUNTRY, "ECB")
        print(COUNTRY, name, "new rows:", added)