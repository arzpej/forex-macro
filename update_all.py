"""Download every data source into data/raw/.

Run:  python update_all.py            (everything)
      python update_all.py fred ff     (only some sources)

One failing source does not stop the others. A summary is printed at the end.
"""

import sys

import pandas as pd

from src.config import FRED_SERIES, START_DATE, YAHOO_TICKERS
from src.data.base import DataSourceError
from src.data.forexfactory_source import ForexFactorySource
from src.data.fred_source import FredSource
from src.data.oanda_source import OandaSource
from src.data.yahoo_source import YahooSource
from src.logger import get_logger

log = get_logger("update_all")


def run_fred(results: dict) -> None:
    fred = FredSource()
    for series_id in FRED_SERIES:
        try:
            fred.save(fred.download(series_id, START_DATE), f"fred_{series_id}")
            results[f"FRED {series_id}"] = "OK"
        except DataSourceError as err:
            results[f"FRED {series_id}"] = f"FAILED: {err}"
    # First-release CPI with release dates (needed later to avoid look-ahead bias)
    try:
        fred.save(fred.download_first_release("CPIAUCSL", START_DATE), "fred_CPIAUCSL_first_release")
        results["FRED CPI first release"] = "OK"
    except DataSourceError as err:
        results["FRED CPI first release"] = f"FAILED: {err}"


def run_oanda(results: dict) -> None:
    oanda = OandaSource()
    two_years_ago = (pd.Timestamp.now(tz="UTC") - pd.DateOffset(years=2)).strftime("%Y-%m-%d")
    jobs = [("EUR_USD", "D", START_DATE), ("EUR_USD", "H1", two_years_ago)]
    for instrument, granularity, start in jobs:
        key = f"OANDA {instrument} {granularity}"
        try:
            df = oanda.download(instrument, start, granularity=granularity)
            oanda.save(df, f"oanda_{instrument}_{granularity}")
            results[key] = "OK"
        except DataSourceError as err:
            results[key] = f"FAILED: {err}"


def run_forexfactory(results: dict) -> None:
    ff = ForexFactorySource()
    try:
        week = ff.download()
        ff.save(week, "ff_calendar_thisweek")
        history = ff.save_history(week)
        results["Forex Factory"] = f"OK ({len(history)} events in history)"
    except DataSourceError as err:
        results["Forex Factory"] = f"FAILED: {err}"


def run_yahoo(results: dict) -> None:
    yahoo = YahooSource()
    for ticker in YAHOO_TICKERS:
        try:
            yahoo.save(yahoo.download(ticker, START_DATE), f"yahoo_{ticker}")
            results[f"Yahoo {ticker}"] = "OK"
        except DataSourceError as err:
            results[f"Yahoo {ticker}"] = f"FAILED: {err}"


JOBS = {"fred": run_fred, "oanda": run_oanda, "ff": run_forexfactory, "yahoo": run_yahoo}


def main(selected: list[str]) -> int:
    results: dict[str, str] = {}
    for name in selected or JOBS:
        try:
            JOBS[name](results)
        except DataSourceError as err:  # e.g. missing API key
            results[name.upper()] = f"SKIPPED: {err}"

    log.info("===== SUMMARY =====")
    for key, status in results.items():
        log.info("%-32s %s", key, status)
    failed = [k for k, v in results.items() if not v.startswith("OK")]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
