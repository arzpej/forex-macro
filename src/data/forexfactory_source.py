"""Forex Factory economic calendar (weekly JSON feed).

Feed: https://nfs.faireconomy.media/ff_calendar_thisweek.json
Fields: title, country, date, impact, forecast, previous

IMPORTANT LIMITS
- The feed only contains THIS WEEK. To build history, run this every week and
  append to a history file (save_history does that).
- The feed has NO "actual" column. Get actual values from FRED (e.g. CPI) or
  add them after the release.
- Be polite: download at most a few times per hour. The file is cached in
  data/raw so you do not need to download it again.
"""

import re

import pandas as pd

from src.data.base import DataSource, DataSourceError

FF_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
IMPACT_ORDER = {"Holiday": 0, "Low": 1, "Medium": 2, "High": 3}
MULTIPLIERS = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}
CURRENCY_TO_COUNTRY = {"USD": "US", "EUR": "EZ", "GBP": "UK", "JPY": "JP",
                       "AUD": "AU", "NZD": "NZ", "CAD": "CA", "CHF": "CH", "CNY": "CN"}


def parse_value(text) -> float | None:
    """Turn '22.5K' -> 22500, '4.5%' -> 4.5, '-258B' -> -2.58e11, '' -> None.

    Values like '3.90|2.4' (bond auctions: yield|bid-to-cover) keep the first part.
    """
    if text is None:
        return None
    text = str(text).strip().replace(",", "")
    if not text:
        return None
    text = text.split("|")[0]
    match = re.fullmatch(r"([<>]?)(-?\d+(?:\.\d+)?)([KMBT%]?)", text)
    if not match:
        return None
    number = float(match.group(2))
    suffix = match.group(3)
    return number * MULTIPLIERS.get(suffix, 1)


class ForexFactorySource(DataSource):
    """Download and clean this week's Forex Factory calendar."""

    def __init__(self, url: str = FF_URL, **kwargs):
        super().__init__(name="ForexFactory", **kwargs)
        self._url = url

    @staticmethod
    def clean(events: list[dict]) -> pd.DataFrame:
        """Turn the raw JSON list into a tidy table."""
        df = pd.DataFrame(events)
        required = {"title", "country", "date", "impact", "forecast", "previous"}
        missing = required - set(df.columns)
        if missing:
            raise DataSourceError(f"Forex Factory feed changed, missing columns: {missing}")

        df = df.rename(columns={"title": "event", "country": "currency"})
        df["time_utc"] = pd.to_datetime(df["date"], utc=True)  # the feed includes the offset
        df["impact_level"] = df["impact"].map(IMPACT_ORDER).fillna(0).astype(int)
        df["forecast_value"] = df["forecast"].apply(parse_value)
        df["previous_value"] = df["previous"].apply(parse_value)
        df["actual_value"] = None  # the feed has no actual; fill later
        df["unit"] = df["forecast"].where(df["forecast"] != "", df["previous"]).str.extract(
            r"([KMBT%])$", expand=False)
        df["country"] = df["currency"].map(CURRENCY_TO_COUNTRY)
        df["event_id"] = (df["currency"] + "|" + df["event"] + "|"
                          + df["time_utc"].dt.strftime("%Y-%m-%dT%H:%M"))
        columns = ["event_id", "time_utc", "currency", "country", "event", "impact",
                   "impact_level", "forecast", "previous", "forecast_value",
                   "previous_value", "actual_value", "unit"]
        return df[columns].sort_values("time_utc").reset_index(drop=True)

    def download(self, symbol: str = "calendar", start: str | None = None,
                 end: str | None = None) -> pd.DataFrame:
        """Download this week. symbol/start/end exist only to match the parent class."""
        events = self._get_json(self._url, headers={"User-Agent": "forex-macro-ai student project"})
        if not isinstance(events, list) or not events:
            raise DataSourceError("Forex Factory feed was empty or not a list")
        df = self.clean(events)
        self.log.info("Calendar: %d events (%d high impact)", len(df), (df["impact_level"] == 3).sum())
        return df

    def save_history(self, new: pd.DataFrame, filename: str = "ff_calendar_history") -> pd.DataFrame:
        """Append this week to the history file. Newer rows replace older copies."""
        path = self._save_dir / f"{filename}.parquet"
        if path.exists():
            old = pd.read_parquet(path)
            combined = pd.concat([old, new], ignore_index=True)
        else:
            combined = new.copy()
        combined = (combined.drop_duplicates("event_id", keep="last")
                    .sort_values("time_utc").reset_index(drop=True))
        self.save(combined, filename)
        return combined

    @staticmethod
    def filter_events(df: pd.DataFrame, currencies=("USD", "EUR"), min_impact: str = "Medium") -> pd.DataFrame:
        """Keep only events that matter for EUR/USD."""
        level = IMPACT_ORDER[min_impact]
        mask = df["currency"].isin(currencies) & (df["impact_level"] >= level)
        return df[mask].reset_index(drop=True)
