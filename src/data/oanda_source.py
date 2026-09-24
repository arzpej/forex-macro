"""OANDA v20 REST API source (Forex candles).

Docs: https://developer.oanda.com/rest-live-v20/instrument-ep/
Token: OANDA website -> My Account -> Manage API Access (practice account is free).
"""

import pandas as pd

from src.config import OANDA_URL, OANDA_TOKEN
from src.data.base import DataSource, DataSourceError

BASE_URLS = {
    "practice": "https://api-fxpractice.oanda.com",
    "live": "https://api-fxtrade.oanda.com",
}
MAX_CANDLES = 5000  # OANDA limit per request
VALID_GRANULARITIES = {"M1", "M5", "M15", "M30", "H1", "H4", "D", "W"}


class OandaSource(DataSource):
    """Download Forex candles (mid, bid and ask prices) from OANDA."""

    def __init__(self, token: str = OANDA_TOKEN, environment: str = OANDA_URL, **kwargs):
        super().__init__(name="OANDA", **kwargs)
        if not token:
            raise DataSourceError("OANDA_TOKEN is missing. Add it to your .env file.")
        if environment not in BASE_URLS:
            raise DataSourceError(f"OANDA_ENV must be 'practice' or 'live', got {environment!r}")
        self._base_url = BASE_URLS[environment]
        self._headers = {"Authorization": f"Bearer {token}", "Accept-Datetime-Format": "RFC3339"}

    @staticmethod
    def _parse_candles(candles: list[dict]) -> pd.DataFrame:
        rows = []
        for c in candles:
            if not c.get("complete", False):  # skip the candle that is still forming
                continue
            mid, bid, ask = c["mid"], c.get("bid", {}), c.get("ask", {})
            rows.append({
                "time": c["time"],
                "open": float(mid["o"]), "high": float(mid["h"]),
                "low": float(mid["l"]), "close": float(mid["c"]),
                "bid_close": float(bid["c"]) if bid else None,
                "ask_close": float(ask["c"]) if ask else None,
                "tick_volume": int(c["volume"]),
            })
        df = pd.DataFrame(rows)
        if not df.empty:
            df["time"] = pd.to_datetime(df["time"], utc=True)
            df["spread"] = df["ask_close"] - df["bid_close"]
        return df

    def download(self, symbol: str, start: str, end: str | None = None,
                 granularity: str = "H1") -> pd.DataFrame:
        """Download candles for e.g. symbol='EUR_USD' by looping in pages of 5,000."""
        if granularity not in VALID_GRANULARITIES:
            raise DataSourceError(f"Unknown granularity {granularity!r}")
        url = f"{self._base_url}/v3/instruments/{symbol}/candles"
        end_ts = pd.Timestamp(end, tz="UTC") if end else pd.Timestamp.now(tz="UTC")
        cursor = pd.Timestamp(start, tz="UTC")
        pages = []

        while cursor < end_ts:
            params = {
                "granularity": granularity,
                "price": "MBA",  # Mid, Bid, Ask
                "from": cursor.isoformat(),
                "count": MAX_CANDLES,
                "includeFirst": "false" if pages else "true",
            }
            data = self._get_json(url, params=params, headers=self._headers)
            page = self._parse_candles(data.get("candles", []))
            if page.empty:
                break
            pages.append(page)
            last_time = page["time"].max()
            self.log.info("%s %s: page %d, up to %s", symbol, granularity, len(pages), last_time)
            if last_time <= cursor:  # safety: stop if we are not moving forward
                break
            cursor = last_time

        if not pages:
            raise DataSourceError(f"OANDA returned no candles for {symbol}")
        df = pd.concat(pages, ignore_index=True)
        df = df[df["time"] <= end_ts].drop_duplicates("time").sort_values("time")
        df["instrument"] = symbol
        return df.reset_index(drop=True)
