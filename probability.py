# PROBABILITIES: turns every score into "chance the next move is UP".
#
# How (no invented numbers):
#   1. For each past month we know the signal AND what actually happened next (up or down).
#   2. Past signals are split into 5 groups, from very weak to very strong.
#   3. Today's probability = how often things went UP after past signals in the SAME group as today.
#   4. Walk-forward: on any date we only use outcomes that were already known on that date.
#   5. Track record: we check how often those probabilities called the direction right,
#      and compare it with the base rate (always guessing the most common direction).

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from src.database import connect
from charts import save_and_show
from model_config import (CURRENCY, PAIRS, ENGINES, HORIZONS, FX_HORIZON, OUTCOME_SOURCE, LABELS,
                          CURRENCY_PRICE, CALIBRATION_BINS, CALIBRATION_MIN_OBS, CALIBRATION_PRIOR)

ENGINE_LIST = list(ENGINES) + ["Policy"]


# ---------- the core: history decides the probability ----------

def up_or_down(change):
    out = pd.Series(np.nan, index=change.index)
    out[change > 0] = 1.0                         # went up
    out[change < 0] = 0.0                         # went down (no change = not counted)
    return out


def calibrate(signal, outcome, horizon):
    s = signal.to_numpy(dtype=float)
    o = outcome.reindex(signal.index).to_numpy(dtype=float)
    probs, similar = np.full(len(s), np.nan), np.zeros(len(s))
    for i in range(len(s)):
        known = i - horizon + 1                   # outcomes already known in month i
        if np.isnan(s[i]) or known <= 0:
            continue
        hs, ho = s[:known], o[:known]
        ok = ~np.isnan(hs) & ~np.isnan(ho)
        hs, ho = hs[ok], ho[ok]
        if len(hs) < CALIBRATION_MIN_OBS:
            continue
        edges = np.quantile(hs, np.linspace(0, 1, CALIBRATION_BINS + 1))[1:-1]
        group = np.digitize(hs, edges) == np.digitize(s[i], edges)
        probs[i] = (ho[group].sum() + CALIBRATION_PRIOR * 0.5) / (group.sum() + CALIBRATION_PRIOR)
        similar[i] = group.sum()
    return pd.Series(probs, index=signal.index), pd.Series(similar, index=signal.index)


def track_record(prob, outcome):
    both = pd.DataFrame({"p": prob, "o": outcome}).dropna()
    both = both[both["p"] != 0.5]
    if both.empty:
        return np.nan, np.nan, 0
    hit = ((both["p"] > 0.5) == (both["o"] == 1)).mean() * 100
    base = max(both["o"].mean(), 1 - both["o"].mean()) * 100      # always guessing the common direction
    return hit, base, len(both)


def forecast(signal, outcome, horizon):
    prob, similar = calibrate(signal, outcome, horizon)
    hit, base, calls = track_record(prob, outcome)
    valid = prob.dropna()
    if valid.empty:
        return None
    return {"history": prob, "p_up": valid.iloc[-1], "date": valid.index[-1],
            "similar": similar.loc[valid.index[-1]], "hit": hit, "base": base, "calls": calls}


# ---------- what "up" means for each engine ----------

def engine_outcome(scores, engine):
    h = HORIZONS[engine]
    source = OUTCOME_SOURCE.get(engine)
    if source is None or source not in scores.columns:
        source = next((c for c in [f"{engine}_coin", f"{engine}_lag", engine] if c in scores.columns), None)
    base = scores[source]
    return up_or_down(base.shift(-h) - base)


def fx_prices(df):
    out = {}
    for col in ["EURUSD", "GBPUSD", "USDJPY", "USDCNY", "USD_INDEX"]:
        if col in df.columns:
            s = df.dropna(subset=[col]).set_index("date")[col].sort_index()
            out[col] = s[~s.index.duplicated()]
    p = pd.DataFrame(out)
    if "EURUSD" in p.columns and "GBPUSD" in p.columns:
        p["EURGBP"] = p["EURUSD"] / p["GBPUSD"]
    if "EURUSD" in p.columns and "USDJPY" in p.columns:
        p["EURJPY"] = p["EURUSD"] * p["USDJPY"]
    return p


# ---------- run every engine, currency and pair ----------

def compute(df, cs, pairs):
    prices = fx_prices(df)
    results = []                                  # one row per country x engine (+ currency) and per pair

    for country, scores in cs.items():
        currency = CURRENCY.get(country, country)
        for engine in ENGINE_LIST:
            if engine not in scores.columns:
                continue
            f = forecast(scores[engine], engine_outcome(scores, engine), HORIZONS[engine])
            if f:
                results.append({"group": currency, "item": engine, **f})

        col, sign = CURRENCY_PRICE.get(currency, (None, 0))
        if col in prices.columns and "MacroScore" in scores.columns:
            price = prices[col].reindex(scores.index)
            outcome = up_or_down((price.shift(-HORIZONS["Currency"]) - price) * sign)
            f = forecast(scores["MacroScore"], outcome, HORIZONS["Currency"])
            if f:
                results.append({"group": currency, "item": "Currency", **f})

    for name, p in pairs.items():
        if name not in prices.columns:
            continue
        price = prices[name].reindex(p["score"].index)
        f = forecast(p["score"], up_or_down(price.shift(-FX_HORIZON) - price), FX_HORIZON)
        if f:
            results.append({"group": "PAIRS", "item": name, **f})
    return results


# ---------- show it simply ----------

def arrow(p):
    return f"↑ {p * 100:.0f}%" if p >= 0.5 else f"↓ {(1 - p) * 100:.0f}%"


def word(item, p):
    up, down = LABELS.get(item, ("Up", "Down"))
    return up if p >= 0.5 else down


def track(r):
    if r["calls"] == 0:
        return "no track record yet"
    edge = r["hit"] - r["base"]
    return f"right {r['hit']:.0f}% of {r['calls']} past calls (base rate {r['base']:.0f}%, edge {edge:+.0f})"


def print_dashboard(results, cs):
    print("\n================ OUTLOOK: chance of the next move (from past data, walk-forward) ================")
    for country, scores in cs.items():
        currency = CURRENCY.get(country, country)
        rows = [r for r in results if r["group"] == currency]
        if not rows:
            continue
        print(f"\n{currency} ({country})  data as of {rows[0]['date']:%Y-%m}")
        for r in rows:
            name = f"{currency} strength" if r["item"] == "Currency" else r["item"]
            h = HORIZONS[r["item"]]
            print(f"  {name:<14} {arrow(r['p_up']):<7} {word(r['item'], r['p_up']):<14} next {h}m | {track(r)}")
            if r["item"] in ENGINES:                                       # drill-down: the three tiers
                last = scores.loc[r["date"]]
                tiers = []
                for t in ["lead", "coin", "lag"]:
                    v = last.get(r["item"] + "_" + t)
                    if pd.notna(v):
                        tiers.append(f"{t} {v:+.0f}")
                print(f"  {'':<14} {'':<7} indicators: {' | '.join(tiers)}")

    rows = [r for r in results if r["group"] == "PAIRS"]
    if rows:
        print(f"\nPAIRS  (next {FX_HORIZON} month)")
        for r in rows:
            print(f"  {r['item']:<8} {arrow(r['p_up']):<7} | {track(r)}")
    print("\nTreat any line with edge 0 or below as NO signal: the model is not beating a simple guess there.")


def chart_dashboard(results):
    currencies = [g for g in dict.fromkeys(r["group"] for r in results) if g != "PAIRS"]
    cols = ENGINE_LIST + ["Currency"]
    table = pd.DataFrame(np.nan, index=currencies, columns=cols)
    for r in results:
        if r["group"] in table.index:
            table.loc[r["group"], r["item"]] = r["p_up"] * 100
    fig, ax = plt.subplots(figsize=(11, 0.65 * len(table) + 2))
    im = ax.imshow(table.values.astype(float), cmap="RdYlGn", vmin=20, vmax=80, aspect="auto")
    ax.set_xticks(range(len(cols)), [c if c != "Currency" else "CURRENCY" for c in cols])
    ax.set_yticks(range(len(table)), table.index)
    for i in range(len(table)):
        for j in range(len(cols)):
            v = table.iat[i, j]
            ax.text(j, i, "-" if pd.isna(v) else arrow(v / 100), ha="center", va="center", fontsize=9)
    ax.set_title("Outlook: chance of the next move  (green = up, red = down, pale = close to 50/50)", loc="left")
    fig.colorbar(im, ax=ax, shrink=0.8, label="% chance of UP")
    save_and_show("outlook_dashboard")


def chart_pairs(results):
    rows = [r for r in results if r["group"] == "PAIRS"]
    if not rows:
        return
    s = pd.Series({r["item"]: r["p_up"] * 100 for r in rows}).sort_values()
    hits = {r["item"]: r for r in rows}
    fig, ax = plt.subplots(figsize=(9, 0.6 * len(s) + 1.5))
    ax.barh(s.index, s - 50, left=50, color=["#1baf7a" if v >= 50 else "#d03b3b" for v in s])
    ax.axvline(50, color="#8a8a85", lw=1)
    ax.set_xlim(0, 100)
    for y, (name, v) in enumerate(s.items()):
        r = hits[name]
        note = f"{arrow(v / 100)}  (right {r['hit']:.0f}% vs {r['base']:.0f}% base)" if r["calls"] else arrow(v / 100)
        ax.text(v + (1 if v >= 50 else -1), y, note, va="center", ha="left" if v >= 50 else "right", fontsize=8.5)
    ax.set_xlabel("% chance the pair goes UP next month")
    ax.set_title("Pairs: chance of the next move, with past accuracy", loc="left")
    ax.grid(alpha=0.25, axis="x")
    save_and_show("outlook_pairs")


def save(results):
    con = connect()
    latest = pd.DataFrame([{k: v for k, v in r.items() if k != "history"} for r in results])
    latest.to_sql("probabilities", con, if_exists="replace", index=False)
    latest.to_csv("data/probabilities.csv", index=False)
    history = pd.concat([r["history"].rename("p_up").to_frame().assign(group=r["group"], item=r["item"])
                         for r in results]).reset_index().dropna(subset=["p_up"])
    history.to_sql("probability_history", con, if_exists="replace", index=False)
    con.close()


def run_probabilities(df, cs, pairs):
    results = compute(df, cs, pairs)
    save(results)
    print_dashboard(results, cs)
    chart_dashboard(results)
    chart_pairs(results)
    return results
