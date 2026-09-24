"""Base class for every data source.

The four pillars of OOP in this file:
- Abstraction:   every source must have download(); how it works is hidden.
- Encapsulation: the save folder and HTTP session are "private" (_underscore).
- Inheritance:   FredSource, OandaSource, ... inherit save() and _get_json().
- Polymorphism:  update_all.py calls .download() on any source the same way.
"""

import time
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd
import requests

from src.config import RAW_DIR
from src.logger import get_logger


class DataSourceError(Exception):
    """Raised when a data source cannot return valid data."""


class DataSource(ABC):
    """Abstract parent class for all data sources."""

    MAX_RETRIES = 3
    RETRY_WAIT_SECONDS = 2
    TIMEOUT_SECONDS = 30

    def __init__(self, name: str, save_dir: Path = RAW_DIR):
        self.name = name
        self._save_dir = Path(save_dir)
        self._save_dir.mkdir(parents=True, exist_ok=True)
        self._session = requests.Session()
        self.log = get_logger(name)

    # ---------- every child MUST write this ----------
    @abstractmethod
    def download(self, symbol: str, start: str, end: str | None = None) -> pd.DataFrame:
        """Download one symbol/series and return a tidy DataFrame."""

    # ---------- shared helpers every child inherits ----------
    def _get_json(self, url: str, params: dict | None = None, headers: dict | None = None):
        """GET a URL and return JSON, retrying on network errors."""
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = self._session.get(
                    url, params=params, headers=headers, timeout=self.TIMEOUT_SECONDS
                )
                if response.status_code == 429:  # too many requests
                    raise requests.HTTPError("Rate limited (429)", response=response)
                response.raise_for_status()
                return response.json()
            except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as err:
                status = getattr(getattr(err, "response", None), "status_code", None)
                # 400/401/403/404 are our mistakes: retrying will not help
                if status in (400, 401, 403, 404):
                    raise DataSourceError(f"{self.name}: HTTP {status} for {url}") from err
                self.log.warning("Attempt %d/%d failed: %s", attempt, self.MAX_RETRIES, err)
                if attempt == self.MAX_RETRIES:
                    raise DataSourceError(f"{self.name}: gave up after {attempt} tries") from err
                time.sleep(self.RETRY_WAIT_SECONDS * attempt)  # wait longer each time
        return None  # never reached

    def save(self, df: pd.DataFrame, filename: str) -> Path:
        """Save a DataFrame as Parquet in data/raw/."""
        if df.empty:
            raise DataSourceError(f"{self.name}: refusing to save an empty table ({filename})")
        safe_name = filename.replace("/", "_").replace("^", "").replace("=", "_")
        path = self._save_dir / f"{safe_name}.parquet"
        df.to_parquet(path, index=False)
        self.log.info("Saved %d rows -> %s", len(df), path.name)
        return path

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
