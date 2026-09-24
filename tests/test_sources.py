"""Unit tests for the data sources. No internet needed: API calls are faked (mocked)."""

from unittest.mock import patch

import pandas as pd
import pytest

from src.data.base import DataSourceError
from src.data.forexfactory_source import ForexFactorySource, parse_value
from src.data.fred_source import FredSource
from src.data.oanda_source import OandaSource
from src.data.yahoo_source import YahooSource

# ---------------------------------------------------------------- FRED
FRED_JSON = {"observations": [
    {"realtime_start": "2026-02-11", "realtime_end": "9999-12-31", "date": "2026-01-01", "value": "320.1"},
    {"realtime_start": "2026-03-11", "realtime_end": "9999-12-31", "date": "2026-02-01", "value": "."},
    {"realtime_start": "2026-04-10", "realtime_end": "9999-12-31", "date": "2026-03-01", "value": "321.4"},
]}


def test_fred_needs_key(tmp_path):
    with pytest.raises(DataSourceError, match="FRED_API_KEY"):
        FredSource(api_key="", save_dir=tmp_path)


def test_fred_download_drops_missing(tmp_path):
    fred = FredSource(api_key="test", save_dir=tmp_path)
    with patch.object(fred, "_get_json", return_value=FRED_JSON):
        df = fred.download("CPIAUCSL", "2026-01-01")
    assert list(df.columns) == ["date", "value", "series_id"]
    assert len(df) == 2  # the "." row is removed
    assert str(df["date"].dt.tz) == "UTC"


def test_fred_first_release_has_release_date(tmp_path):
    fred = FredSource(api_key="test", save_dir=tmp_path)
    with patch.object(fred, "_get_json", return_value=FRED_JSON) as fake:
        df = fred.download_first_release("CPIAUCSL", "2026-01-01")
    assert fake.call_args.kwargs["params"]["output_type"] == 4
    assert (df["release_date"] > df["date"]).all()  # released AFTER the month it describes


# ---------------------------------------------------------------- OANDA
def candle(time, close, complete=True):
    price = {"o": "1.1000", "h": "1.1050", "l": "1.0950", "c": close}
    return {"time": time, "complete": complete, "volume": 1200, "mid": price,
            "bid": {**price, "c": str(float(close) - 0.00005)},
            "ask": {**price, "c": str(float(close) + 0.00005)}}


def test_oanda_skips_incomplete_candle():
    df = OandaSource._parse_candles([
        candle("2026-09-01T00:00:00Z", "1.1010"),
        candle("2026-09-01T01:00:00Z", "1.1020", complete=False),
    ])
    assert len(df) == 1
    assert df["spread"].iloc[0] == pytest.approx(0.0001)


def test_oanda_pages_until_end(tmp_path):
    oanda = OandaSource(token="test", environment="practice", save_dir=tmp_path)
    page1 = {"candles": [candle("2026-09-01T00:00:00Z", "1.10"), candle("2026-09-01T01:00:00Z", "1.11")]}
    page2 = {"candles": [candle("2026-09-01T02:00:00Z", "1.12")]}
    page3 = {"candles": []}
    with patch.object(oanda, "_get_json", side_effect=[page1, page2, page3]):
        df = oanda.download("EUR_USD", "2026-09-01", "2026-09-02", granularity="H1")
    assert len(df) == 3
    assert df["time"].is_monotonic_increasing


def test_oanda_rejects_bad_settings(tmp_path):
    with pytest.raises(DataSourceError):
        OandaSource(token="test", environment="demo", save_dir=tmp_path)
    oanda = OandaSource(token="test", save_dir=tmp_path)
    with pytest.raises(DataSourceError, match="granularity"):
        oanda.download("EUR_USD", "2026-01-01", granularity="H2")


# ---------------------------------------------------------------- Forex Factory
FF_JSON = [  # real rows copied from the feed, week of 21 Sep 2026
    {"title": "Unemployment Claims", "country": "USD", "date": "2026-09-24T08:30:00-04:00",
     "impact": "Medium", "forecast": "201K", "previous": "196K"},
    {"title": "German Flash Services PMI", "country": "EUR", "date": "2026-09-23T03:30:00-04:00",
     "impact": "Medium", "forecast": "49.9", "previous": "48.5"},
    {"title": "Unemployment Rate", "country": "AUD", "date": "2026-09-23T21:30:00-04:00",
     "impact": "High", "forecast": "4.5%", "previous": "4.5%"},
    {"title": "Bank Holiday", "country": "JPY", "date": "2026-09-20T19:00:00-04:00",
     "impact": "Holiday", "forecast": "", "previous": ""},
]


@pytest.mark.parametrize("text, expected", [
    ("22.5K", 22500), ("4.5%", 4.5), ("-258B", -2.58e11), ("-0.7M", -700000),
    ("3.90|2.4", 3.90), ("", None), ("n/a", None), (None, None), ("<0.1%", 0.1),
])
def test_parse_value(text, expected):
    assert parse_value(text) == (pytest.approx(expected) if expected is not None else None)


def test_ff_clean_converts_time_to_utc():
    df = ForexFactorySource.clean(FF_JSON)
    claims = df[df["event"] == "Unemployment Claims"].iloc[0]
    assert claims["time_utc"] == pd.Timestamp("2026-09-24 12:30", tz="UTC")  # 08:30 New York = 12:30 UTC
    assert claims["forecast_value"] == 201000
    assert df["time_utc"].is_monotonic_increasing


def test_ff_filter_keeps_usd_eur_medium_plus():
    df = ForexFactorySource.filter_events(ForexFactorySource.clean(FF_JSON))
    assert set(df["currency"]) == {"USD", "EUR"}
    assert len(df) == 2


def test_ff_detects_feed_change():
    with pytest.raises(DataSourceError, match="missing columns"):
        ForexFactorySource.clean([{"title": "CPI", "country": "USD"}])


def test_ff_history_has_no_duplicates(tmp_path):
    ff = ForexFactorySource(save_dir=tmp_path)
    week = ff.clean(FF_JSON)
    ff.save_history(week)
    history = ff.save_history(week)  # same week saved twice
    assert len(history) == len(FF_JSON)


# ---------------------------------------------------------------- Yahoo
def test_yahoo_tidy_flattens_columns():
    index = pd.DatetimeIndex(["2026-09-01", "2026-09-02"], name="Date")
    columns = pd.MultiIndex.from_product([["Open", "High", "Low", "Close", "Volume"], ["^VIX"]])
    raw = pd.DataFrame([[15, 16, 14, 15.5, 0], [15.5, 17, 15, 16.2, 0]], index=index, columns=columns)
    df = YahooSource.tidy(raw, "^VIX")
    assert list(df.columns) == ["date", "open", "high", "low", "close", "volume", "symbol"]
    assert str(df["date"].dt.tz) == "UTC"


def test_yahoo_empty_raises():
    with pytest.raises(DataSourceError):
        YahooSource.tidy(pd.DataFrame(), "BAD")


# ---------------------------------------------------------------- Base class
def test_save_refuses_empty(tmp_path):
    fred = FredSource(api_key="test", save_dir=tmp_path)
    with pytest.raises(DataSourceError, match="empty"):
        fred.save(pd.DataFrame(), "nothing")


def test_save_writes_parquet(tmp_path):
    fred = FredSource(api_key="test", save_dir=tmp_path)
    path = fred.save(pd.DataFrame({"a": [1, 2]}), "yahoo_^VIX")
    assert path.name == "yahoo_VIX.parquet"
    assert pd.read_parquet(path)["a"].tolist() == [1, 2]
