"""FRED (Federal Reserve Economic Data) source.

API docs: https://fred.stlouisfed.org/docs/api/fred/series_observations.html
Get a free key: https://fredaccount.stlouisfed.org/apikeys
"""

import pandas as pd

from src.config import FRED_API_KEY
from src.data.base import DataSource, DataSourceError

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"


class FredSource(DataSource):
    """Download macro series from FRED."""

    def __init__(self, api_key: str = FRED_API_KEY, **kwargs):
        super().__init__(name="FRED", **kwargs)
        if not api_key:
            raise DataSourceError("FRED_API_KEY is missing. Add it to your .env file.")
        self._api_key = api_key  # encapsulated: never print or log it

    def _request(self, series_id: str, start: str, end: str | None, extra: dict) -> list[dict]:
        params = {
            "series_id": series_id,
            "api_key": self._api_key,
            "file_type": "json",
            "observation_start": start,
        }
        if end:
            params["observation_end"] = end
        params.update(extra)
        data = self._get_json(FRED_URL, params=params)
        observations = data.get("observations", [])
        if not observations:
            raise DataSourceError(f"FRED returned no data for {series_id}")
        return observations

    @staticmethod
    def _to_frame(observations: list[dict], series_id: str) -> pd.DataFrame:
        df = pd.DataFrame(observations)
        # FRED writes missing values as "." -> turn them into NaN
        df["value"] = pd.to_numeric(df["value"].replace(".", None), errors="coerce")
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df["series_id"] = series_id
        return df

    def download(self, symbol: str, start: str, end: str | None = None) -> pd.DataFrame:
        """Latest (revised) values. Good for charts, NOT for training a model."""
        obs = self._request(symbol, start, end, extra={})
        df = self._to_frame(obs, symbol)[["date", "value", "series_id"]]
        df = df.dropna(subset=["value"]).reset_index(drop=True)
        self.log.info("%s: %d rows (%s -> %s)", symbol, len(df),
                      df["date"].min().date(), df["date"].max().date())
        return df

    def download_first_release(self, symbol: str, start: str, end: str | None = None) -> pd.DataFrame:
        """First-published values plus the date they were released.

        output_type=4 means "initial release only". Column realtime_start is the
        day the number became public -> use it to avoid look-ahead bias.
        """
        obs = self._request(
            symbol, start, end,
            extra={"output_type": 4, "realtime_start": "1776-07-04", "realtime_end": "9999-12-31"},
        )
        df = self._to_frame(obs, symbol)
        df["release_date"] = pd.to_datetime(df["realtime_start"], utc=True)
        df = df[["date", "release_date", "value", "series_id"]].dropna(subset=["value"])
        self.log.info("%s first release: %d rows", symbol, len(df))
        return df.reset_index(drop=True)
