import sqlite3
import pandas as pd

DB_FILE = "data/macro.db"            # one database for everything
CSV_FILE = "data/macro_clean.csv"    # final clean file


def connect():
    con = sqlite3.connect(DB_FILE)
    con.execute("""
        CREATE TABLE IF NOT EXISTS observations (
            country   TEXT,
            indicator TEXT,
            source    TEXT,
            date      TEXT,
            value     REAL,
            PRIMARY KEY (country, indicator, date)
        )
    """)
    return con


def last_date(indicator, country):
    # newest date we already have (None = never downloaded)
    con = connect()
    row = con.execute(
        "SELECT MAX(date) FROM observations WHERE indicator = ? AND country = ?",
        (indicator, country),
    ).fetchone()
    con.close()
    return row[0]


def save(df, indicator, country, source):
    # df has two columns: date, value
    df = df.copy()
    df["date"] = df["date"].astype(str).str.replace("-Q", "Q")
    df["date"] = (df["date"].str.replace("Q1", "-01").str.replace("Q2", "-04")
                            .str.replace("Q3", "-07").str.replace("Q4", "-10"))   # quarters -> months
    df["date"] = pd.to_datetime(df["date"], format="ISO8601").dt.strftime("%Y-%m-%d")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")                        # "." becomes empty
    df = df.dropna()

    rows = [(country, indicator, source, d, v) for d, v in zip(df["date"], df["value"])]
    con = connect()
    before = con.total_changes
    con.executemany("INSERT OR IGNORE INTO observations VALUES (?, ?, ?, ?, ?)", rows)   # only new dates are added
    con.commit()
    added = con.total_changes - before
    con.close()
    return added


def export_clean():
    # one row = one month of one country, one column per indicator (CPI, PPI, ...)
    con = connect()
    df = pd.read_sql("SELECT country, indicator, date, value FROM observations", con)
    df["date"] = pd.to_datetime(df["date"])

    # step 1: make every indicator monthly (daily/weekly/quarterly -> one value per month)
    df = df.pivot_table(index="date", columns=["country", "indicator"], values="value")
    df = df.resample("MS").last().ffill()
    df = df.melt(ignore_index=False).reset_index().dropna()

    # step 2: one row per date + country, indicators side by side
    df = df.pivot_table(index=["date", "country"], columns="indicator", values="value").reset_index()
    df = df.sort_values(["country", "date"])
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")

    df.to_sql("monthly", con, if_exists="replace", index=False)
    con.close()
    df.to_csv(CSV_FILE, index=False)
    return df