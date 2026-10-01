# All model settings in one place. Change numbers here, not in the code.
# Every run also saves these weights to the database (table: model_weights) so changes are audit-able.

MODEL_VERSION = "v2-probability"

CURRENCY = {"US": "USD", "Euro": "EUR", "China": "CNY", "UK": "GBP", "Japan": "JPY"}

PAIRS = {
    "EURUSD": ("EUR", "USD"),
    "GBPUSD": ("GBP", "USD"),
    "USDJPY": ("USD", "JPY"),
    "USDCNY": ("USD", "CNY"),
    "EURGBP": ("EUR", "GBP"),
    "EURJPY": ("EUR", "JPY"),
}

# ---------------- LAYER 1: ECONOMY ENGINES ----------------
# Each engine answers ONE question about the next few months:
#   Growth: stronger or weaker?        Inflation: rising or falling?      Labour: strengthening or weakening?
#   Liquidity: expanding or tightening? Expectations: market more hawkish or dovish?

ZSCORE_MONTHS = 60                  # "unusual" = compared with the last 5 years

# inside each indicator: level, momentum (3-month change) and acceleration
FEATURE_WEIGHTS = {"level": 0.5, "momentum": 0.3, "accel": 0.2}

# the forecast leans on LEADING indicators (starting prior - the backtest will adjust these later)
TIER_WEIGHTS = {"lead": 0.60, "coin": 0.25, "lag": 0.15}

# engine: [(indicator, how to read it, direction for THIS engine, weight, tier)]
#   yoy = % vs a year ago (index levels) | change = change vs a year ago | level = value | auto = yoy if index-like
#   tier: lead = leading, coin = coincident (current), lag = lagging (confirms)
ENGINES = {
    "Growth": [
        ("LEADING_INDEX",      "level", +1, 0.20, "lead"),
        ("PMI_MANUFACTURING",  "level", +1, 0.15, "lead"),
        ("PMI_SERVICES",       "level", +1, 0.10, "lead"),
        ("CONSUMER_SENTIMENT", "level", +1, 0.10, "lead"),
        ("YIELD_CURVE",        "level", +1, 0.10, "lead"),     # steeper curve = growth ahead
        ("INDUSTRIAL_PROD",    "yoy",   +1, 0.15, "coin"),
        ("RETAIL_SALES",       "yoy",   +1, 0.15, "coin"),
        ("REAL_GDP",           "yoy",   +1, 0.10, "lag"),
        ("GDP_GROWTH",         "level", +1, 0.10, "lag"),
    ],
    "Inflation": [
        ("PPI",      "auto", +1, 0.15, "lead"),
        ("WAGES",    "auto", +1, 0.15, "lead"),               # wage pressure feeds prices
        ("CPI",      "auto", +1, 0.15, "coin"),
        ("CORE_CPI", "auto", +1, 0.20, "coin"),
        ("PCE",      "auto", +1, 0.10, "lag"),
        ("CORE_PCE", "auto", +1, 0.20, "lag"),
    ],
    "Labour": [
        ("JOBLESS_CLAIMS", "yoy",    -1, 0.20, "lead"),        # more claims = weaker
        ("NFP",            "yoy",    +1, 0.20, "coin"),
        ("UNEMPLOYMENT",   "change", -1, 0.20, "lag"),         # rising unemployment = weaker
        ("WAGES",          "auto",   +1, 0.15, "lag"),
    ],
    "Liquidity": [                                             # + = money getting easier
        ("M2",        "level", +1, 0.15, "lead"),
        ("REAL_RATE", "level", -1, 0.15, "coin"),              # high real rate = tight money
    ],
    "Expectations": [                                          # + = market expects higher rates
        ("MARKET_SPREAD", "level",  +1, 0.15, "lead"),         # market rate minus policy rate
        ("YIELD_10Y",     "change", +1, 0.10, "coin"),
        ("POLICY_RATE",   "change", +1, 0.15, "lag"),
    ],
}

OVERRIDES = {("China", "PPI"): "level"}             # China PPI is already "same month last year = 100"
UNIT_SCALE = {("China", "CPI"): 100}                # China CPI comes as 0.012 = 1.2%

# publication delay: data for month X is only known later -> shift it so the model never "sees the future"
DEFAULT_LAG_MONTHS = 1
LAG_OVERRIDES = {"REAL_GDP": 3, "GDP_GROWTH": 3}
NO_LAG = ["YIELD_2Y", "YIELD_10Y", "YIELD_CURVE", "POLICY_RATE", "INTERBANK_3M", "VIX",
          "EURUSD", "GBPUSD", "USDJPY", "USDCNY", "USD_INDEX", "COT_NET"]

# ---------------- LAYER 2: POLICY ENGINE ----------------
# Question: will the central bank tighten (+) or ease (-)?
# Built from the other engines + the Taylor rule.

POLICY_INPUTS = {"Inflation": 0.30, "Labour": 0.20, "Growth": 0.15, "Liquidity": -0.10, "Expectations": 0.25}
POLICY_TAYLOR_SHARE = 0.30          # 30% Taylor-rule gap, 70% the engines above

# Taylor rule: model rate = neutral real rate + inflation + 0.5 x (inflation - target) - 1.0 x (unemployment gap)
INFLATION_TARGET = {"US": 2.0, "Euro": 2.0, "UK": 2.0, "Japan": 2.0, "China": 3.0}
NEUTRAL_REAL_RATE = 0.5
TAYLOR_INFLATION = 0.5
TAYLOR_SLACK = 1.0

# ---------------- CURRENCY STRENGTH ----------------
# how each engine pushes the country's currency (+ = stronger currency)
CURRENCY_LINKS = {"Growth": 1.0, "Inflation": 0.5, "Labour": 0.5, "Liquidity": -0.5,
                  "Expectations": 1.0, "Policy": 1.0}

# price used to check if a currency got stronger: (column, +1 if a rise = currency stronger, -1 if weaker)
CURRENCY_PRICE = {"USD": ("USD_INDEX", +1), "EUR": ("EURUSD", +1), "GBP": ("GBPUSD", +1),
                  "JPY": ("USDJPY", -1), "CNY": ("USDCNY", -1)}

# ---------------- PROBABILITIES (from history, never invented) ----------------
# months ahead each engine forecasts
HORIZONS = {"Growth": 3, "Inflation": 3, "Labour": 3, "Liquidity": 3, "Expectations": 3, "Policy": 6, "Currency": 1}
FX_HORIZON = 1                      # pairs: next month

# what each engine's "up" means when checking history
OUTCOME_SOURCE = {"Inflation": "inflation_rate", "Expectations": "market_rate", "Policy": "policy_rate"}

CALIBRATION_BINS = 5                # split past signals into 5 groups (very weak ... very strong)
CALIBRATION_MIN_OBS = 36            # need 3 years of past outcomes before giving a probability
CALIBRATION_PRIOR = 10              # pulls small samples toward 50% so they don't look overconfident

LABELS = {                          # (word for up, word for down)
    "Growth": ("Expansion", "Slowdown"), "Inflation": ("Rising", "Falling"),
    "Labour": ("Strengthening", "Weakening"), "Liquidity": ("Easing", "Tightening"),
    "Expectations": ("Hawkish", "Dovish"), "Policy": ("Tightening", "Easing"),
    "Currency": ("Stronger", "Weaker"),
}

# ---------------- LAYER 3: FX DRIVERS (the "why" behind each pair) ----------------

SAFE_HAVEN = {"USD": 1, "JPY": 1}                  # currencies that rise when markets are scared
COT_MONTHS = 36                                     # positioning compared with the last 3 years

REGIME_WEIGHTS = {
    "NORMAL":          {"RATES": 0.25, "GROWTH": 0.15, "INFLATION_POLICY": 0.15, "LABOUR": 0.08,
                        "LIQUIDITY": 0.05, "CARRY": 0.10, "RISK": 0.10, "POSITIONING": 0.12},
    "RISK_OFF":        {"RATES": 0.15, "GROWTH": 0.10, "INFLATION_POLICY": 0.10, "LABOUR": 0.05,
                        "LIQUIDITY": 0.15, "CARRY": 0.05, "RISK": 0.30, "POSITIONING": 0.10},
    "INFLATION_SHOCK": {"RATES": 0.30, "GROWTH": 0.10, "INFLATION_POLICY": 0.25, "LABOUR": 0.05,
                        "LIQUIDITY": 0.05, "CARRY": 0.10, "RISK": 0.10, "POSITIONING": 0.05},
    "RECESSION":       {"RATES": 0.20, "GROWTH": 0.25, "INFLATION_POLICY": 0.05, "LABOUR": 0.20,
                        "LIQUIDITY": 0.05, "CARRY": 0.05, "RISK": 0.15, "POSITIONING": 0.05},
}

RISK_OFF_VIX_Z = 1.5                # VIX far above normal
INFLATION_SHOCK_LEVEL = 40          # average Inflation engine of all countries above +40
RECESSION_LEVEL = -40               # average Growth engine of all countries below -40