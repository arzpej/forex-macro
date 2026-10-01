# DATA QUALITY: checks every series in the database before the model uses it.
# Nothing is changed here - it only REPORTS problems, so you decide what to fix.
#
# Status per country + indicator:
#   OK       all checks passed
#   STALE    no new data for longer than normal for its frequency (source stopped or changed?)
#   GAPS     missing periods in the middle of the history
#   FLAT     no change at all for the last 24 readings (z-scores ignore it)
#   CHECK    impossible values or extreme jumps -> look at the source, maybe a bad number

from datetime import date
import pandas as pd
from src.database import connect

MAX_DELAY_MONTHS = {"daily": 1, "weekly": 1, "monthly": 3, "quarterly": 6}
OUTLIER_LIMIT = 8                  # jump bigger than 8x the normal move = suspicious

# values that are impossible in real life
SANITY = {
    "UNEMPLOYMENT": (0, 50), "VIX": (0, 150), "PMI_MANUFACTURING": (0, 100), "PMI_SERVICES": (0, 100),
    "EURUSD": (0.01, None), "GBPUSD": (0.01, None), "USDJPY": (0.01, None), "USDCNY": (0.01, None),
    "USD_INDEX": (0.01, None), "REAL_GDP": (0.01, None), "NFP": (0.01, None), "JOBLESS_CLAIMS": (0.01, None),
}


def frequency(dates):
    days = dates.to_series().diff().dt.days.median()
    if days <= 3:
        return "daily"
    if days <= 10:
        return "weekly"
    if days <= 45:
        return "monthly"
    return "quarterly"


def missing_periods(dates, freq):
    if freq in ("daily", "weekly"):                 # markets close on holidays - only count missing months
        freq = "monthly"
    periods = dates.to_period("M" if freq == "monthly" else "Q").unique()
    expected = pd.period_range(periods.min(), periods.max(), freq=periods.freq)
    return len(expected) - len(periods)


def outliers(values):
    move = values.diff()
    typical = move.abs().rolling(24, min_periods=12).median().shift(1)
    big = (move.abs() > OUTLIER_LIMIT * typical) & (typical > 0)
    return values.index[big.fillna(False).to_numpy()]


def check_series(group):
    s = group.set_index("date")["value"].sort_index()
    freq = frequency(s.index)
    last = s.index[-1]
    months_old = (date.today().year - last.year) * 12 + date.today().month - last.month
    low, high = SANITY.get(group["indicator"].iloc[0], (None, None))
    too_low = s < low if low is not None else pd.Series(False, index=s.index)
    too_high = s > high if high is not None else pd.Series(False, index=s.index)
    bad = s[too_low | too_high]
    jumps = outliers(s)
    flat = len(s) >= 24 and s.tail(24).nunique() == 1
    gaps = missing_periods(s.index, freq)

    problems = []
    if len(bad):
        problems.append(f"{len(bad)} impossible values (e.g. {bad.index[-1]:%Y-%m-%d} = {bad.iloc[-1]})")
    if len(jumps):
        problems.append(f"{len(jumps)} extreme jumps (latest {jumps[-1]:%Y-%m-%d})")
    if months_old > MAX_DELAY_MONTHS[freq]:
        problems.append(f"no update for {months_old} months")
    if gaps:
        problems.append(f"{gaps} missing periods")
    if flat:
        problems.append("unchanged for 24 readings")

    status = ("CHECK" if len(bad) or len(jumps) else "STALE" if months_old > MAX_DELAY_MONTHS[freq]
              else "GAPS" if gaps else "FLAT" if flat else "OK")
    return {"country": group["country"].iloc[0], "indicator": group["indicator"].iloc[0],
            "source": group["source"].iloc[0], "frequency": freq, "first": s.index[0].date(),
            "last": last.date(), "readings": len(s), "months_since_update": months_old,
            "status": status, "problems": "; ".join(problems)}


def run_data_quality():
    con = connect()
    df = pd.read_sql("SELECT country, indicator, source, date, value FROM observations", con)
    df["date"] = pd.to_datetime(df["date"])
    report = pd.DataFrame([check_series(g) for _, g in df.groupby(["country", "indicator"])])
    report = report.sort_values(["status", "country", "indicator"])
    report.astype({"first": str, "last": str}).to_sql("data_quality", con, if_exists="replace", index=False)
    con.close()
    report.to_csv("data/data_quality.csv", index=False)

    counts = report["status"].value_counts().to_dict()
    print("\n==================== DATA QUALITY ====================")
    print("  ".join(f"{k}: {v}" for k, v in counts.items()))
    problems = report[report["status"] != "OK"]
    if len(problems):
        print(problems[["status", "country", "indicator", "source", "last", "problems"]].to_string(index=False))
    print("Full report: data/data_quality.csv")
    return report
