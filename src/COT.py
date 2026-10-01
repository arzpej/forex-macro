# CFTC Commitments of Traders: how speculators are positioned in currency futures (free, weekly).
# Net = speculators' long contracts minus short contracts.

import requests
import pandas as pd
from src.database import last_date, save

COT_URL = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"     # Legacy report, futures only

# country -> CME futures contract code
COT_CONTRACTS = {
    "Euro": "099741",       # Euro FX
    "Japan": "097741",      # Japanese yen
    "UK": "096742",         # British pound
    "US": "098662",         # US Dollar Index
}


def get_cot(code, start):
    params = {
        "cftc_contract_market_code": code,
        "$where": f"report_date_as_yyyy_mm_dd >= '{start}'",
        "$order": "report_date_as_yyyy_mm_dd",
        "$limit": 50000,
    }
    df = pd.DataFrame(requests.get(COT_URL, params=params).json())
    df["date"] = df["report_date_as_yyyy_mm_dd"].str[:10]
    df["value"] = df["noncomm_positions_long_all"].astype(float) - df["noncomm_positions_short_all"].astype(float)
    return df[["date", "value"]]


def update_cot():
    for country, code in COT_CONTRACTS.items():
        try:
            start = last_date("COT_NET", country) or "2010-01-01"
            df = get_cot(code, start)
            added = save(df, "COT_NET", country, "CFTC")
            print(country, "COT_NET new rows:", added)
        except Exception as error:
            print("FAILED", country, "COT_NET ->", error)
