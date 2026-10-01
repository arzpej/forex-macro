# Adaptive charts: work for ANY country in macro_clean.csv.
# Each chart has a list of indicators to try, in order. The first one the country has is used.
#
#   draw_rate_chart(df, country)          -> market rate (leading) vs policy rate (lagging)
#   draw_unemployment_chart(df, country)  -> early-warning bars + unemployment line

import os
import matplotlib.pyplot as plt

BLUE, ORANGE, GREEN, RED, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#d03b3b", "#8a8a85"
CHART_FOLDER = "charts"

# --- What to try, in order ---
POLICY_CHOICES = ["POLICY_RATE", "INTERBANK_3M"]        # lagging: what the central bank did
MARKET_CHOICES = ["YIELD_2Y", "YIELD_10Y"]              # leading: what the market expects

# early-warning indicator: (column, how to turn it into a signal, "bad" direction, label)
WARNING_CHOICES = [
    ("JOBLESS_CLAIMS",    "yoy",      "up",   "Jobless claims, % vs a year ago"),
    ("PMI_MANUFACTURING", "minus50",  "down", "Manufacturing PMI minus 50"),
    ("INDUSTRIAL_PROD",   "yoy",      "down", "Industrial production, % vs a year ago"),
    ("LEADING_INDEX",     "minus100", "down", "OECD leading index minus 100"),
]


def get_country(df, country, start):
    data = df[df["country"] == country].set_index("date").sort_index().loc[start:]
    return data.dropna(axis=1, how="all")          # drop columns this country doesn't have


def pick(data, choices):
    # first column in the list that this country has (None if none)
    for name in choices:
        if name in data.columns:
            return name
    return None


def save_and_show(name):
    os.makedirs(CHART_FOLDER, exist_ok=True)
    plt.tight_layout()
    plt.savefig(f"{CHART_FOLDER}/{name}.png", dpi=150)
    plt.show()


def draw_rate_chart(df, country, start="2010-01-01"):
    data = get_country(df, country, start)
    policy_col = pick(data, POLICY_CHOICES)
    market_col = pick(data, MARKET_CHOICES)

    if policy_col is None:
        print(f"{country}: no policy rate - rate chart skipped")
        return

    policy = data[policy_col]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(policy.index, policy, color=BLUE, lw=2, label=f"{policy_col} (lagging)")

    if market_col is None:
        ax.set_title(f"{country}: {policy_col}", loc="left")
    else:
        market = data[market_col]
        ax.plot(market.index, market, color=ORANGE, lw=2, label=f"{market_col} (leading)")
        ax.fill_between(policy.index, policy, market, where=market > policy,
                        color=ORANGE, alpha=0.15, label="Market above policy = expects HIKES")
        ax.fill_between(policy.index, policy, market, where=market < policy,
                        color=BLUE, alpha=0.15, label="Market below policy = expects CUTS")
        gap = market.dropna().iloc[-1] - policy.dropna().iloc[-1]
        if gap > 0.25:
            verdict = "HIKE expected"
        elif gap < -0.25:
            verdict = "CUT expected"
        else:
            verdict = "HOLD expected"
        ax.set_title(f"{country} {market_col} vs {policy_col}  |  gap now {gap:+.2f}  ->  {verdict}", loc="left")

    ax.set_ylabel("%")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    save_and_show(f"{country}_rate")


def draw_unemployment_chart(df, country, start="2022-01-01"):
    data = get_country(df, country, "2009-01-01")      # extra year so "% vs a year ago" works from start

    if "UNEMPLOYMENT" not in data.columns:
        print(f"{country}: no unemployment data - chart skipped")
        return

    warning = None
    for col, method, bad_way, label in WARNING_CHOICES:
        if col in data.columns:
            if method == "yoy":
                warning = data[col].pct_change(12, fill_method=None) * 100
            elif method == "minus50":
                warning = data[col] - 50
            else:
                warning = data[col] - 100
            bad = warning > 0 if bad_way == "up" else warning < 0
            break

    unemp = data["UNEMPLOYMENT"].loc[start:].dropna()

    if warning is None:
        fig, bottom = plt.subplots(figsize=(10, 3.5))
    else:
        warning, bad = warning.loc[start:], bad.loc[start:]
        fig, (top, bottom) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
        top.bar(warning.index, warning, width=25, color=[RED if b else GREEN for b in bad])
        top.axhline(0, color=GREY, lw=1)
        top.set_title(f"{country} early warning - {label}   (red = bad for jobs)", loc="left")
        top.grid(alpha=0.25)

    bottom.plot(unemp.index, unemp, color=BLUE, lw=2)
    bottom.set_title(f"{country} unemployment rate % (lagging)", loc="left")
    bottom.grid(alpha=0.25)
    save_and_show(f"{country}_unemployment")