# Forex Macro AI — Module 1: Data Collection

Downloads everything the project needs into `data/raw/`:

| Source | File | What you get |
|---|---|---|
| FRED | `src/data/fred_source.py` | EUR/USD, Fed & ECB rates, US & German yields, CPI, unemployment, yield curve, CPI first-release dates |
| OANDA | `src/data/oanda_source.py` | EUR/USD daily (since 2010) and hourly (last 2 years) with bid, ask, spread and tick volume |
| Forex Factory | `src/data/forexfactory_source.py` | This week's economic calendar, plus a history file that grows every week |
| Yahoo | `src/data/yahoo_source.py` | DXY, VIX, S&P 500, Gold, EUR/USD (daily) |

## Setup (Windows)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        # then open .env and paste your keys
```

Mac/Linux: `source .venv/bin/activate` and `cp .env.example .env`.

## Run

```bash
python update_all.py              # all sources
python update_all.py fred ff      # only FRED and Forex Factory
pytest                            # run the tests (no internet needed)
```

Choices for `update_all.py`: `fred`, `oanda`, `ff`, `yahoo`.

## Project structure

```
forex-macro-ai/
├── src/
│   ├── config.py                 settings + keys from .env
│   ├── logger.py                 logging to screen and logs/pipeline.log
│   └── data/
│       ├── base.py               DataSource parent class (retries, save)
│       ├── fred_source.py
│       ├── oanda_source.py
│       ├── forexfactory_source.py
│       └── yahoo_source.py
├── tests/test_sources.py         23 tests with fake API responses
├── update_all.py                 runs everything, prints a summary
├── docs/LESSONS.md               what each module teaches
├── .env.example                  template for your keys
└── .gitignore                    keeps .env, data and logs off GitHub
```

## Acceptance criteria

- [ ] `pytest` shows all tests passing
- [ ] `python update_all.py` ends with a summary where every line says OK
- [ ] `data/raw/` contains one Parquet file per series
- [ ] `.env` does not appear on GitHub
- [ ] All timestamps are UTC
