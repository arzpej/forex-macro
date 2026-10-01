from src.FED_US import get_fred               # Japan's official data, served through FRED (same key)
from src.database import last_date, save

COUNTRY = "Japan"

JAPAN_SERIES = {
    # --- Inflation ---
    "JPNCPIALLMINMEI": "CPI",                     # Consumer Price Index (OECD)

    # --- Growth ---
    "JPNRGDPEXP": "REAL_GDP",                     # Real GDP, quarterly (Cabinet Office)
    "JPNLOLITOAASTSAM": "LEADING_INDEX",          # OECD leading indicator

    # --- Jobs ---
    "LRUN64TTJPM156S": "UNEMPLOYMENT",            # Unemployment rate, age 15-64

    # --- Interest rates ---
    "IRSTCI01JPM156N": "POLICY_RATE",             # Overnight call rate (BOJ policy target)
    "IRLTLT01JPM156N": "YIELD_10Y",               # 10-year government bond (JGB) yield

    # --- Markets ---
    "DEXJPUS": "USDJPY",                          # Yen per 1 US dollar
}


def update_japan():
    for series, name in JAPAN_SERIES.items():
        try:
            start = last_date(name, COUNTRY) or "2010-01-01"
            df = get_fred(series, start)
            added = save(df, name, COUNTRY, "FRED")
            print(COUNTRY, name, "new rows:", added)
        except Exception as error:
            print("FAILED", COUNTRY, name, "->", error)
