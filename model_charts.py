# Charts for the 3-layer model. All charts adapt to whatever countries and pairs exist.

import pandas as pd
import matplotlib.pyplot as plt
from charts import save_and_show, GREEN, RED, GREY, BLUE, ORANGE
from model_config import ENGINES, CURRENCY
from fx_model import pair_label

DRIVER_COLORS = {"RATES": "#2a78d6", "GROWTH": "#1baf7a", "INFLATION_POLICY": "#eb6834", "LABOUR": "#8e5bd1",
                 "LIQUIDITY": "#17a2b8", "CARRY": "#c9a227", "RISK": "#d03b3b", "POSITIONING": "#8a8a85"}


def latest(s, col):
    valid = s.dropna(subset=[col])
    return valid.iloc[-1]


def chart_engines(cs):
    # Layer 1: country x engine heatmap
    engines = list(ENGINES) + ["Policy"]
    rows = {CURRENCY.get(c, c): latest(s, "MacroScore").reindex(engines) for c, s in cs.items()}
    table = pd.DataFrame(rows).T
    fig, ax = plt.subplots(figsize=(10, 0.6 * len(table) + 1.8))
    im = ax.imshow(table.values.astype(float), cmap="RdYlGn", vmin=-100, vmax=100, aspect="auto")
    ax.set_xticks(range(len(engines)), engines)
    ax.set_yticks(range(len(table)), table.index)
    for i in range(len(table)):
        for j in range(len(engines)):
            v = table.iat[i, j]
            ax.text(j, i, "-" if pd.isna(v) else f"{v:+.0f}", ha="center", va="center", fontsize=9)
    ax.set_title("Layer 1-2: engine scores by country  (green = supports the currency)", loc="left")
    fig.colorbar(im, ax=ax, shrink=0.8)
    save_and_show("model_engines")


def chart_policy(cs):
    # Layer 2: what the Taylor rule says vs what the central bank and market do
    rows = {}
    for c, s in cs.items():
        if "model_rate" in s.columns and s["model_rate"].notna().any():
            last = latest(s, "model_rate")
            rows[CURRENCY.get(c, c)] = [last.get("policy_rate"), last.get("market_rate"), last["model_rate"]]
    if not rows:
        return
    table = pd.DataFrame(rows, index=["Policy rate (now)", "Market rate (expects)", "Model rate (should be)"]).T
    ax = table.plot.bar(figsize=(10, 4.5), color=[BLUE, ORANGE, GREEN], rot=0)
    ax.axhline(0, color=GREY, lw=1)
    ax.set_ylabel("%")
    ax.set_title("Layer 2: model rate above policy rate = hike pressure, below = cut pressure", loc="left")
    ax.grid(alpha=0.25, axis="y")
    ax.legend(frameon=False, fontsize=8)
    save_and_show("model_policy")


def chart_pairs_now(pairs):
    # Layer 3: pair score now
    s = pd.Series({name: p["score"].dropna().iloc[-1] for name, p in pairs.items() if p["score"].notna().any()})
    s = s.sort_values()
    fig, ax = plt.subplots(figsize=(9, 0.6 * len(s) + 1.5))
    ax.barh(s.index, s, color=[GREEN if v > 0 else RED for v in s])
    ax.axvline(0, color=GREY, lw=1)
    ax.set_xlim(-140, 140)
    for y, (name, v) in enumerate(s.items()):
        ax.text(v + (3 if v >= 0 else -3), y, f"{v:+.0f}  {pair_label(v)}",
                va="center", ha="left" if v >= 0 else "right", fontsize=9)
    ax.set_title("Layer 3: pair score now  (+ = buy the pair, - = sell)", loc="left")
    ax.grid(alpha=0.25, axis="x")
    save_and_show("model_pairs")


def chart_pair_reasons(pairs):
    # explainability: which driver pushes each pair up (right) or down (left)
    names = [n for n, p in pairs.items() if p["score"].notna().any()]
    fig, ax = plt.subplots(figsize=(10, 0.7 * len(names) + 2))
    shown = set()
    for y, name in enumerate(names):
        p = pairs[name]
        date = p["score"].dropna().index[-1]
        contrib = p["contributions"].loc[date].dropna()
        right, left = 0, 0
        for driver, v in contrib.items():
            label = driver if driver not in shown else None
            shown.add(driver)
            if v >= 0:
                ax.barh(y, v, left=right, color=DRIVER_COLORS.get(driver, GREY), label=label)
                right += v
            else:
                ax.barh(y, v, left=left, color=DRIVER_COLORS.get(driver, GREY), label=label)
                left += v
    ax.set_yticks(range(len(names)), names)
    ax.axvline(0, color="black", lw=1)
    ax.set_title("WHY: each driver's push on the pair  (right = up, left = down)", loc="left")
    ax.grid(alpha=0.25, axis="x")
    ax.legend(frameon=False, fontsize=8, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    save_and_show("model_reasons")


def chart_pair_history(pairs, regime, start="2015-01-01"):
    fig, ax = plt.subplots(figsize=(10, 4.5))
    for name, p in pairs.items():
        s = p["score"].loc[start:]
        ax.plot(s.index, s, lw=1.6, label=name)
    shocks = regime.loc[start:]
    for date, r in shocks[shocks != "NORMAL"].items():                    # shade non-normal regimes
        ax.axvspan(date, date + pd.offsets.MonthBegin(1), color=GREY, alpha=0.12, lw=0)
    ax.axhline(0, color=GREY, lw=1)
    ax.set_ylim(-100, 100)
    ax.set_title("Pair scores over time  (grey = risk-off / inflation shock / recession regime)", loc="left")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, ncol=len(pairs), fontsize=8)
    save_and_show("model_pair_history")


def draw_model_charts(cs, pairs, regime):
    chart_engines(cs)
    chart_policy(cs)
    chart_pairs_now(pairs)
    chart_pair_reasons(pairs)
    chart_pair_history(pairs, regime)
