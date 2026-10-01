# LAYER 1 (economy engines) and LAYER 2 (policy engine) - one country at a time.
# Works for any country: it only uses the indicators that country has.
# Each engine = leading tier (60%) + coincident tier (25%) + lagging tier (15%).

import pandas as pd
from model_config import (ENGINES, TIER_WEIGHTS, FEATURE_WEIGHTS, ZSCORE_MONTHS, OVERRIDES, UNIT_SCALE,
                          DEFAULT_LAG_MONTHS, LAG_OVERRIDES, NO_LAG, INFLATION_TARGET, NEUTRAL_REAL_RATE,
                          TAYLOR_INFLATION, TAYLOR_SLACK, POLICY_INPUTS, POLICY_TAYLOR_SHARE, CURRENCY_LINKS)


# ---------- helpers ----------

def pick(data, choices):
    for name in choices:
        if name in data.columns:
            return name
    return None


def zscore(series, months=ZSCORE_MONTHS):
    mean = series.rolling(months, min_periods=24).mean()
    std = series.rolling(months, min_periods=24).std()
    return ((series - mean) / std).clip(-3, 3)


def weighted_average(parts, used):
    return pd.concat(parts, axis=1).sum(axis=1, min_count=1) / pd.concat(used, axis=1).sum(axis=1)


def signed_blend(scores, weights):
    # weighted average that allows negative weights (e.g. Liquidity -0.10)
    cols = [c for c in weights if c in scores.columns]
    if not cols:
        return None
    parts = [scores[c] * weights[c] for c in cols]
    used = [scores[c].notna() * abs(weights[c]) for c in cols]
    return weighted_average(parts, used)


def inflation_rate(data, country):
    # inflation as % per year, whatever format the country publishes
    for name in ["CORE_PCE", "CORE_CPI", "CPI"]:
        if name in data.columns:
            s = data[name]
            if s.median() > 20:
                return s.pct_change(12, fill_method=None) * 100
            return s * UNIT_SCALE.get((country, name), 1)
    return None


def prepare(df, country):
    data = df[df["country"] == country].set_index("date").sort_index()
    data = data.drop(columns="country").dropna(axis=1, how="all")
    for col in data.columns:                                       # publication delay
        if col not in NO_LAG:
            data[col] = data[col].shift(LAG_OVERRIDES.get(col, DEFAULT_LAG_MONTHS))
    policy = pick(data, ["POLICY_RATE", "INTERBANK_3M"])
    market = pick(data, ["YIELD_2Y", "YIELD_10Y"])
    if policy and market:
        data["MARKET_SPREAD"] = data[market] - data[policy]
    infl = inflation_rate(data, country)
    if policy and infl is not None:
        data["REAL_RATE"] = data[policy] - infl
    return data


def transform(series, how, country, name):
    how = OVERRIDES.get((country, name), how)
    if how == "auto":
        how = "yoy" if series.median() > 20 else "level"
    if how == "yoy":
        return series.pct_change(12, fill_method=None) * 100
    if how == "change":
        return series.diff(12)
    return series


def indicator_score(series):
    # one number per month: level + momentum + acceleration (each compared with the last 5 years)
    momentum = series.diff(3)
    feats = {
        "level": zscore(series),
        "momentum": zscore(momentum),
        "accel": zscore(momentum - momentum.shift(3)),
    }
    return weighted_average([feats[f] * w for f, w in FEATURE_WEIGHTS.items()],
                            [feats[f].notna() * w for f, w in FEATURE_WEIGHTS.items()])


# ---------- LAYER 1: economy engines ----------

def engine_scores(data, country):
    scores = pd.DataFrame(index=data.index)
    for engine, items in ENGINES.items():
        tiers = {}
        for tier in TIER_WEIGHTS:
            parts, used = [], []
            for name, how, direction, weight, t in items:
                if t != tier or name not in data.columns:
                    continue
                s = indicator_score(transform(data[name], how, country, name)) * direction
                parts.append(s * weight)
                used.append(s.notna() * weight)
            if parts:
                tiers[tier] = (weighted_average(parts, used) * 50).clip(-100, 100)   # z of +2 = +100
                scores[f"{engine}_{tier}"] = tiers[tier]
        if tiers:
            scores[engine] = weighted_average([s * TIER_WEIGHTS[t] for t, s in tiers.items()],
                                              [s.notna() * TIER_WEIGHTS[t] for t, s in tiers.items()])
    return scores


# ---------- LAYER 2: policy engine ----------

def taylor_rule(data, country):
    out = pd.DataFrame(index=data.index)
    infl = inflation_rate(data, country)
    policy = pick(data, ["POLICY_RATE", "INTERBANK_3M"])
    market = pick(data, ["YIELD_2Y", "YIELD_10Y"])
    if infl is None or policy is None:
        return out

    slack = 0
    if "UNEMPLOYMENT" in data.columns:
        u = data["UNEMPLOYMENT"]
        slack = u - u.rolling(ZSCORE_MONTHS, min_periods=24).mean()   # above normal = spare capacity

    target = INFLATION_TARGET.get(country, 2.0)
    out["inflation_rate"] = infl
    out["model_rate"] = NEUTRAL_REAL_RATE + infl + TAYLOR_INFLATION * (infl - target) - TAYLOR_SLACK * slack
    out["policy_rate"] = data[policy]
    out["policy_gap"] = out["model_rate"] - out["policy_rate"]         # + = should hike, - = should cut
    if market:
        out["market_rate"] = data[market]
        out["repricing_gap"] = out["model_rate"] - out["market_rate"]  # + = market not pricing enough hikes
    out["Policy_taylor"] = (out["policy_gap"] * 25).clip(-100, 100)     # 1 percentage point = 25 points
    return out


def policy_engine(scores):
    from_engines = signed_blend(scores, POLICY_INPUTS)
    if from_engines is None:
        return None
    if "Policy_taylor" not in scores.columns:
        return from_engines
    both = pd.concat([from_engines * (1 - POLICY_TAYLOR_SHARE), scores["Policy_taylor"] * POLICY_TAYLOR_SHARE], axis=1)
    used = pd.concat([from_engines.notna() * (1 - POLICY_TAYLOR_SHARE),
                      scores["Policy_taylor"].notna() * POLICY_TAYLOR_SHARE], axis=1)
    return both.sum(axis=1, min_count=1) / used.sum(axis=1)


# ---------- all countries ----------

def country_scores(df):
    results = {}
    for country in df["country"].unique():
        data = prepare(df, country)
        scores = engine_scores(data, country)
        if scores.dropna(how="all").empty:
            continue
        scores = scores.join(taylor_rule(data, country))
        policy = policy_engine(scores)
        if policy is not None:
            scores["Policy"] = policy
        for col in ["COT_NET", "VIX"]:
            if col in data.columns:
                scores[col] = data[col]
        scores["MacroScore"] = signed_blend(scores, CURRENCY_LINKS)    # + = good for this currency
        results[country] = scores
    return results