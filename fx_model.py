# LAYER 3: FX - always RELATIVE (base country vs quote country).
# Drivers -> regime-dependent weights -> pair score -> explanation of WHY.

from datetime import datetime
import pandas as pd
from src.database import connect
from engines import country_scores, zscore
from model_config import (MODEL_VERSION, CURRENCY, PAIRS, SAFE_HAVEN, COT_MONTHS, REGIME_WEIGHTS,
                          RISK_OFF_VIX_Z, INFLATION_SHOCK_LEVEL, RECESSION_LEVEL, ENGINES, CURRENCY_LINKS,
                          TIER_WEIGHTS, POLICY_INPUTS)

COUNTRY_OF = {cur: country for country, cur in CURRENCY.items()}


# ---------- regime ----------

def global_risk(cs):
    us = cs.get("US")
    if us is None or "VIX" not in us.columns:
        return None
    return zscore(us["VIX"])


def detect_regime(cs, vix_z):
    growth = pd.concat([s["Growth"] for s in cs.values() if "Growth" in s.columns], axis=1).mean(axis=1)
    inflation = pd.concat([s["Inflation"] for s in cs.values() if "Inflation" in s.columns], axis=1).mean(axis=1)
    regime = pd.Series("NORMAL", index=growth.index)
    regime[growth < RECESSION_LEVEL] = "RECESSION"
    regime[inflation > INFLATION_SHOCK_LEVEL] = "INFLATION_SHOCK"
    if vix_z is not None:
        regime[vix_z.reindex(regime.index) > RISK_OFF_VIX_Z] = "RISK_OFF"     # risk-off beats everything
    return regime


# ---------- drivers for one pair ----------

def differential(a, b):
    return ((a - b) / 2).clip(-100, 100)


def pair_drivers(base, quote, base_cur, quote_cur, vix_z):
    idx = base.index.intersection(quote.index)
    b, q = base.reindex(idx), quote.reindex(idx)
    d = pd.DataFrame(index=idx)

    if "market_rate" in b.columns and "market_rate" in q.columns:         # expected rate differential
        rate_diff = b["market_rate"] - q["market_rate"]
        d["RATES"] = ((zscore(rate_diff) + zscore(rate_diff.diff(3))) / 2 * 50).clip(-100, 100)

    for driver, col in [("GROWTH", "Growth"), ("INFLATION_POLICY", "Policy"), ("LABOUR", "Labour")]:
        if col in b.columns and col in q.columns:
            d[driver] = differential(b[col], q[col])

    if "Liquidity" in b.columns and "Liquidity" in q.columns:              # easier money = weaker currency
        d["LIQUIDITY"] = differential(q["Liquidity"], b["Liquidity"])

    if "policy_rate" in b.columns and "policy_rate" in q.columns:         # carry = who pays more interest
        d["CARRY"] = (zscore(b["policy_rate"] - q["policy_rate"]) * 50).clip(-100, 100)

    safe = SAFE_HAVEN.get(base_cur, 0) - SAFE_HAVEN.get(quote_cur, 0)
    if vix_z is not None and safe != 0:                                   # fear helps safe havens
        d["RISK"] = (vix_z.reindex(idx) * 50 * safe).clip(-100, 100)

    has_b, has_q = "COT_NET" in b.columns, "COT_NET" in q.columns
    if has_b or has_q:                                                    # crowded long = less upside (contrarian)
        zb = zscore(b["COT_NET"], COT_MONTHS) if has_b else 0
        zq = zscore(q["COT_NET"], COT_MONTHS) if has_q else 0
        d["POSITIONING"] = (-(zb - zq) * 25).clip(-100, 100)

    return d


def score_pair(drivers, regime):
    regimes = regime.reindex(drivers.index).fillna("NORMAL")
    w = pd.DataFrame([REGIME_WEIGHTS[r] for r in regimes], index=drivers.index)[drivers.columns]
    used = (drivers.notna() * w).sum(axis=1)
    contributions = (drivers * w).div(used, axis=0)                       # each driver's share of the score
    score = contributions.sum(axis=1, min_count=1).clip(-100, 100)
    return score, contributions


def pair_label(x):
    if x > 40:
        return "STRONG BUY"
    if x > 15:
        return "BUY"
    if x < -40:
        return "STRONG SELL"
    if x < -15:
        return "SELL"
    return "NEUTRAL / WAIT"


# ---------- save ----------

def save_outputs(cs, pairs, regime):
    con = connect()

    country_table = pd.concat([s.assign(country=c) for c, s in cs.items()]).reset_index()
    country_table.to_sql("country_scores", con, if_exists="replace", index=False)
    country_table.to_csv("data/country_scores.csv", index=False)

    pair_table = pd.concat([
        p["drivers"].assign(pair=name, score=p["score"], regime=regime.reindex(p["drivers"].index))
        for name, p in pairs.items()
    ]).reset_index()
    pair_table.to_sql("pair_scores", con, if_exists="replace", index=False)
    pair_table.to_csv("data/pair_scores.csv", index=False)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = [(MODEL_VERSION, "fx", r, d, w, now) for r, ws in REGIME_WEIGHTS.items() for d, w in ws.items()]
    rows += [(MODEL_VERSION, "engine", f"{e}:{tier}", ind, w, now)
             for e, items in ENGINES.items() for ind, _, _, w, tier in items]
    rows += [(MODEL_VERSION, "tier", "ALL", t, w, now) for t, w in TIER_WEIGHTS.items()]
    rows += [(MODEL_VERSION, "policy", "ALL", e, w, now) for e, w in POLICY_INPUTS.items()]
    rows += [(MODEL_VERSION, "currency", "ALL", e, w, now) for e, w in CURRENCY_LINKS.items()]
    weights = pd.DataFrame(rows, columns=["model_version", "layer", "group", "item", "prior_weight", "updated_at"])
    weights.to_sql("model_weights", con, if_exists="append", index=False)                  # history of all weights
    con.close()


# ---------- report ----------

def cycle_phase(growth, inflation):
    if growth >= 0 and inflation >= 0:
        return "Expansion (hot)"
    if growth >= 0:
        return "Recovery"
    if inflation >= 0:
        return "Stagflation"
    return "Slowdown"


def fmt(row, col, pct=False):
    v = row.get(col)
    if v is None or pd.isna(v):
        return "  -"
    return f"{v:.2f}%" if pct else f"{v:+.0f}"


def print_report(cs, pairs, regime):
    # the detail behind the dashboard: which drivers push each pair (the "click to see why" view)
    print(f"\n========== WHY: DRIVERS BEHIND EACH PAIR  (regime now: {regime.dropna().iloc[-1]}) ==========")
    for name, p in pairs.items():
        valid = p["score"].dropna()
        if valid.empty:
            continue
        date, score = valid.index[-1], valid.iloc[-1]
        contrib = p["contributions"].loc[date].dropna()
        share = (contrib.abs() / contrib.abs().sum() * 100).round(0)
        print(f"\n{name}  score {score:+.0f}   (as of {date:%Y-%m})")
        for driver in share.sort_values(ascending=False).index:
            print(f"     {driver:<17} {contrib[driver]:+6.1f} pts   {share[driver]:3.0f}% of the reason")


# ---------- run everything ----------

def run_model(df):
    cs = country_scores(df)
    vix_z = global_risk(cs)
    regime = detect_regime(cs, vix_z)

    pairs = {}
    for name, (base_cur, quote_cur) in PAIRS.items():
        base, quote = COUNTRY_OF.get(base_cur), COUNTRY_OF.get(quote_cur)
        if base not in cs or quote not in cs:
            continue
        drivers = pair_drivers(cs[base], cs[quote], base_cur, quote_cur, vix_z)
        if drivers.empty:
            continue
        score, contributions = score_pair(drivers, regime)
        pairs[name] = {"drivers": drivers, "score": score, "contributions": contributions}

    save_outputs(cs, pairs, regime)
    print_report(cs, pairs, regime)
    return cs, pairs, regime