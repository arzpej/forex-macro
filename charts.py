# -*- coding: utf-8 -*-
"""
Created on Thu Sep 24 18:29:14 2026

@author: anism
"""

"""
STEP 2 of the macro charts lesson: 10 charts + 1 summary table.

HOW TO USE IN SPYDER
- Each chart is a CELL that starts with  # %%
- Click inside a cell and press  Ctrl+Enter  to run ONLY that cell.
- Always run the SETUP cell first.
- Charts appear in the "Plots" tab (top right). They are also saved in charts/.

Before this, run get_macro_data.py once to create data/raw/macro_monthly.csv
"""

# %% SETUP  (run this cell first)
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Colours: one fixed colour per job, always in the same order
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
GREY = "#8a8985"              # recessions, zero lines, grid

plt.rcParams.update({
    "figure.dpi": 110,
    "axes.grid": True,
    "grid.color": "#e6e5e1",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.titlesize": 11,
    "axes.titleweight": "bold",
    "lines.linewidth": 2,
})

CHART_DIR = Path("charts")
CHART_DIR.mkdir(exist_ok=True)

# Load the table made by get_macro_data.py
df = pd.read_csv("data/raw/macro_monthly.csv", index_col="date", parse_dates=True)


# ---- small helper functions -------------------------------------------------
def yoy(series):
    """Year-over-year % change: this month compared with 12 months ago."""
    return series.pct_change(12, fill_method=None) * 100


def zscore(series):
    """Put any series on the same scale: 0 = its average, +1 = 1 standard deviation above."""
    return (series - series.mean()) / series.std()


def shade_recessions(ax):
    """Grey bands where the US was in recession (USREC = 1)."""
    in_recession = df["recession"].fillna(0) == 1
    start = None
    for date, flag in in_recession.items():
        if flag and start is None:
            start = date
        if not flag and start is not None:
            ax.axvspan(start, date, color=GREY, alpha=0.2, linewidth=0)
            start = None


def save(fig, name):
    """Save the chart as a PNG (useful for your presentation)."""
    fig.savefig(CHART_DIR / f"{name}.png", bbox_inches="tight")
    print("Saved charts/" + name + ".png")


# ---- new columns we calculate once ----------------------------------------
for col in ["payrolls", "industrial_production", "real_income", "core_cpi", "cpi",
            "business_loans", "capex_orders", "gold", "dxy", "eurusd", "sp500"]:
    df[col + "_yoy"] = yoy(df[col])

df["rate_difference"] = df["fed_rate"] - df["ecb_rate"]   # US rate minus Europe rate

print("Data loaded:", df.shape[0], "months from", df.index.min().date(),
      "to", df.index.max().date())


# %% CHART 1 - LEADING indicators (early warnings)
# What to look for: do these lines turn down BEFORE the grey recession bands?
leading = {
    "yield_curve":        "Yield curve 10y-2y (%)  - below 0 = warning",
    "jobless_claims":     "Jobless claims  - rising = warning",
    "building_permits":   "Building permits (thousands)",
    "consumer_sentiment": "Consumer sentiment (index)",
    "capex_orders_yoy":   "Business equipment orders (YoY %)",
    "factory_hours":      "Factory weekly hours",
}

fig, axes = plt.subplots(3, 2, figsize=(12, 9), sharex=True)
for ax, (col, title) in zip(axes.flat, leading.items()):
    ax.plot(df.index, df[col], color=BLUE)
    shade_recessions(ax)
    ax.set_title(title)
    if col in ("yield_curve", "capex_orders_yoy"):
        ax.axhline(0, color=GREY, linewidth=1)
fig.suptitle("Chart 1 - Leading indicators (grey = US recession)", fontsize=13, fontweight="bold")
fig.tight_layout()
save(fig, "01_leading")
plt.show()


# %% CHART 2 - COINCIDENT indicators (where the economy is now)
# What to look for: these fall INSIDE the grey bands, at the same time as the recession.
coincident = {
    "payrolls_yoy":              "Jobs / payrolls (YoY %)",
    "industrial_production_yoy": "Industrial production (YoY %)",
    "real_income_yoy":           "Real income (YoY %)",
}

fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
for ax, (col, title) in zip(axes, coincident.items()):
    ax.plot(df.index, df[col], color=BLUE)
    shade_recessions(ax)
    ax.axhline(0, color=GREY, linewidth=1)
    ax.set_title(title)
fig.suptitle("Chart 2 - Coincident indicators", fontsize=13, fontweight="bold")
fig.tight_layout()
save(fig, "02_coincident")
plt.show()


# %% CHART 3 - LAGGING indicators (confirm what already happened)
# What to look for: these peak or turn AFTER the grey bands end.
lagging = {
    "unemployment_rate":  "Unemployment rate (%)",
    "unemployment_weeks": "Average weeks unemployed",
    "core_cpi_yoy":       "Core inflation (YoY %)",
    "business_loans_yoy": "Business loans (YoY %)",
}

fig, axes = plt.subplots(2, 2, figsize=(12, 7), sharex=True)
for ax, (col, title) in zip(axes.flat, lagging.items()):
    ax.plot(df.index, df[col], color=BLUE)
    shade_recessions(ax)
    ax.set_title(title)
fig.suptitle("Chart 3 - Lagging indicators", fontsize=13, fontweight="bold")
fig.tight_layout()
save(fig, "03_lagging")
plt.show()


# %% CHART 4 - Our own LEADING INDEX vs the real economy
# We combine the 6 leading indicators into ONE line (average of z-scores).
# Jobless claims are flipped (minus sign) because MORE claims = WORSE economy.
# What to look for: does the blue line turn before the orange line?
parts = pd.DataFrame({
    "yield_curve":        zscore(df["yield_curve"]),
    "jobless_claims":     -zscore(df["jobless_claims"]),
    "building_permits":   zscore(df["building_permits"]),
    "consumer_sentiment": zscore(df["consumer_sentiment"]),
    "capex_orders":       zscore(df["capex_orders_yoy"]),
    "factory_hours":      zscore(df["factory_hours"]),
})
df["leading_index"] = parts.mean(axis=1)
economy = zscore(df["industrial_production_yoy"])

fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(df.index, df["leading_index"], color=BLUE, label="Our leading index")
ax.plot(df.index, economy, color=ORANGE, label="Industrial production YoY (the economy)")
shade_recessions(ax)
ax.axhline(0, color=GREY, linewidth=1)
ax.set_ylabel("z-score (0 = average)")
ax.set_title("Chart 4 - Leading index vs the economy")
ax.legend(loc="lower left", frameon=False)
fig.tight_layout()
save(fig, "04_leading_index_vs_economy")
plt.show()


# %% CHART 5 - How the leading indicators move together (correlation heatmap)
# +1 = move together, -1 = move opposite, 0 = no relationship
corr = parts.corr()

fig, ax = plt.subplots(figsize=(7, 6))
image = ax.imshow(corr, cmap="RdBu", vmin=-1, vmax=1)
ax.set_xticks(range(len(corr)), corr.columns, rotation=45, ha="right")
ax.set_yticks(range(len(corr)), corr.index)
ax.grid(False)
for i in range(len(corr)):
    for j in range(len(corr)):
        value = corr.iloc[i, j]
        text_colour = "white" if abs(value) > 0.6 else "black"   # readable on dark cells
        ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=9, color=text_colour)
fig.colorbar(image, ax=ax, shrink=0.8, label="correlation")
ax.set_title("Chart 5 - Correlation between leading indicators\n(jobless claims flipped)")
fig.tight_layout()
save(fig, "05_leading_correlation")
plt.show()


# %% CHART 6 - HOW MANY MONTHS does each indicator lead the economy?
# For each indicator we shift it forward 0..18 months and find the shift
# where it matches industrial production best (highest correlation).
target = df["industrial_production_yoy"]
results = []
for name in parts.columns:
    best_lag, best_corr = 0, 0.0
    for lag in range(0, 19):
        c = parts[name].shift(lag).corr(target)     # indicator from 'lag' months ago
        if abs(c) > abs(best_corr):
            best_lag, best_corr = lag, c
    results.append({"indicator": name, "lead_months": best_lag, "correlation": best_corr})

lead_table = pd.DataFrame(results).sort_values("lead_months")
print(lead_table.to_string(index=False))

fig, ax = plt.subplots(figsize=(9, 5))
ax.barh(lead_table["indicator"], lead_table["lead_months"], color=BLUE, height=0.6)
for y, (months, c) in enumerate(zip(lead_table["lead_months"], lead_table["correlation"])):
    ax.text(months + 0.2, y, f"{months} months  (corr {c:.2f})", va="center", fontsize=9)
ax.set_xlabel("Months ahead of industrial production")
ax.set_xlim(0, 22)
ax.set_title("Chart 6 - How early does each leading indicator move?")
fig.tight_layout()
save(fig, "06_lead_months")
plt.show()


# %% CHART 7 - GOLD vs the US DOLLAR (DXY)
# Top: both prices rebased to 100 at the start, so they share one scale.
# Bottom: 24-month rolling correlation of monthly changes.
#   Below 0 = they move opposite (the usual pattern).
both = df[["gold", "dxy"]].dropna()
rebased = both / both.iloc[0] * 100
rolling_corr = both.pct_change().rolling(24).corr().unstack()["gold"]["dxy"]

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True,
                               gridspec_kw={"height_ratios": [2, 1]})
ax1.plot(rebased.index, rebased["gold"], color=BLUE, label="Gold")
ax1.plot(rebased.index, rebased["dxy"], color=ORANGE, label="Dollar index (DXY)")
ax1.axhline(100, color=GREY, linewidth=1)
ax1.set_ylabel(f"Rebased: {rebased.index[0]:%b %Y} = 100")
ax1.set_title("Chart 7 - Gold vs the US Dollar")
ax1.legend(frameon=False)
ax2.plot(rolling_corr.index, rolling_corr, color=BLUE)
ax2.axhline(0, color=GREY, linewidth=1)
ax2.set_ylim(-1, 1)
ax2.set_ylabel("24-month correlation")
fig.tight_layout()
save(fig, "07_gold_vs_dollar")
plt.show()


# %% CHART 8 - GOLD vs the REAL interest rate
# Real yield = interest rate AFTER inflation. Gold pays no interest,
# so when real yields go UP, holding gold is less attractive.
pair = df[["real_10y_yield", "gold"]].dropna()
slope, intercept = np.polyfit(pair["real_10y_yield"], pair["gold"], 1)
x_line = np.linspace(pair["real_10y_yield"].min(), pair["real_10y_yield"].max(), 50)
r = pair["real_10y_yield"].corr(pair["gold"])

fig, ax = plt.subplots(figsize=(8, 6))
ax.scatter(pair["real_10y_yield"], pair["gold"], color=BLUE, s=18, alpha=0.6)
ax.plot(x_line, slope * x_line + intercept, color=ORANGE, label=f"Trend (correlation {r:.2f})")
ax.set_xlabel("US 10-year REAL yield (%)")
ax.set_ylabel("Gold price (USD)")
ax.set_title("Chart 8 - Gold vs real interest rate (each dot = one month)")
ax.legend(frameon=False)
fig.tight_layout()
save(fig, "08_gold_vs_real_yield")
plt.show()


# %% CHART 9 - Interest-rate difference vs EUR/USD
# When US rates rise ABOVE Europe's, money moves to the dollar -> EUR/USD tends to fall.
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
ax1.plot(df.index, df["rate_difference"], color=BLUE)
ax1.axhline(0, color=GREY, linewidth=1)
ax1.set_title("US Fed rate minus ECB rate (percentage points)")
ax2.plot(df.index, df["eurusd"], color=ORANGE)
ax2.set_title("EUR/USD")
fig.suptitle("Chart 9 - Rate difference vs EUR/USD", fontsize=13, fontweight="bold")
fig.tight_layout()
save(fig, "09_rate_difference_vs_eurusd")
plt.show()
print("Correlation (rate difference vs EUR/USD):",
      round(df["rate_difference"].corr(df["eurusd"]), 2))


# %% CHART 10 - Inflation and the Fed's answer
# All three lines are in %, so they share one axis.
# What to look for: inflation rises first, then the Fed raises rates (a lag).
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(df.index, df["cpi_yoy"], color=BLUE, label="CPI inflation (YoY %)")
ax.plot(df.index, df["core_cpi_yoy"], color=ORANGE, label="Core CPI inflation (YoY %)")
ax.plot(df.index, df["fed_rate"], color=AQUA, label="Fed Funds rate (%)")
ax.axhline(2, color=GREY, linewidth=1, linestyle="--")
ax.text(df.index[0], 2.2, "Fed's 2% inflation target", color="#52514e", fontsize=9)
shade_recessions(ax)
ax.set_ylabel("%")
ax.set_title("Chart 10 - Inflation vs the Fed interest rate")
ax.legend(loc="upper left", frameon=False)
fig.tight_layout()
save(fig, "10_inflation_vs_fed")
plt.show()


# %% TABLE 11 - Markets vs macro: one summary correlation table
# Rows = markets, columns = macro factors. All in yearly changes where it makes sense.
markets = pd.DataFrame({
    "Gold (YoY %)":    df["gold_yoy"],
    "DXY (YoY %)":     df["dxy_yoy"],
    "EUR/USD (YoY %)": df["eurusd_yoy"],
    "S&P 500 (YoY %)": df["sp500_yoy"],
})
macro = pd.DataFrame({
    "CPI inflation":        df["cpi_yoy"],
    "Fed rate change 12m":  df["fed_rate"].diff(12),
    "Real yield change 12m": df["real_10y_yield"].diff(12),
    "Rate diff (US-EU)":    df["rate_difference"],
    "VIX":                  df["vix"],
    "Leading index":        df["leading_index"],
})
summary = pd.DataFrame({m: [markets[m].corr(macro[f]) for f in macro] for m in markets},
                       index=macro.columns).T.round(2)

print("\nTable 11 - correlation between markets (rows) and macro factors (columns)")
print(summary.to_string())
summary.to_csv(CHART_DIR / "11_markets_vs_macro.csv")

fig, ax = plt.subplots(figsize=(10, 4))
image = ax.imshow(summary, cmap="RdBu", vmin=-1, vmax=1, aspect="auto")
ax.set_xticks(range(summary.shape[1]), summary.columns, rotation=30, ha="right")
ax.set_yticks(range(summary.shape[0]), summary.index)
ax.grid(False)
for i in range(summary.shape[0]):
    for j in range(summary.shape[1]):
        value = summary.iloc[i, j]
        text_colour = "white" if abs(value) > 0.6 else "black"
        ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=9, color=text_colour)
fig.colorbar(image, ax=ax, label="correlation")
ax.set_title("Table 11 - Markets vs macro factors")
fig.tight_layout()
save(fig, "11_markets_vs_macro")
plt.show()