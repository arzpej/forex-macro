# Module 1 Lessons — Data Collection

Read one lesson, open the file it describes, and run the matching tests.
Each lesson ends with **Check yourself** questions and **Your task**.

---

## Lesson 0 — The shared parts (`config.py`, `logger.py`, `base.py`)

**Course link:** SCOOP sessions 10–12 (modules, OOP), ICTPRG302 session 9 (files, errors)

### What an API is
An API is a website made for programs instead of people. You send a URL with
parameters, and it sends back data (usually JSON).

```
Request:   GET https://api.stlouisfed.org/fred/series/observations?series_id=CPIAUCSL&api_key=...&file_type=json
Response:  {"observations": [{"date": "2026-01-01", "value": "320.1"}, ...]}
```

### Why keys live in `.env`
If your key is written in the code, it goes to GitHub and anyone can use it.
`config.py` reads keys with `os.getenv()` after `load_dotenv()` loads `.env`.
`.gitignore` stops `.env` from being uploaded.

### The base class and the four pillars of OOP
| Pillar | Where you see it |
|---|---|
| **Abstraction** | `download()` is marked `@abstractmethod`: every source *must* have it |
| **Encapsulation** | `_save_dir`, `_session`, `_api_key` start with `_` = "private, don't touch" |
| **Inheritance** | `FredSource(DataSource)` gets `save()` and `_get_json()` for free |
| **Polymorphism** | `update_all.py` calls `.download()` on every source in the same way |

### Retries (`_get_json`)
Networks fail. The method tries 3 times and waits longer each time (2s, 4s).
But it does **not** retry errors 400/401/403/404, because those are your
mistakes (wrong key, wrong URL) — retrying cannot fix them.

HTTP codes to remember:
| Code | Meaning | Retry? |
|---|---|---|
| 200 | OK | — |
| 400 | Bad request (wrong parameter) | No |
| 401 / 403 | Wrong or missing key / not allowed | No |
| 404 | Wrong URL or symbol | No |
| 429 | Too many requests | Yes, after waiting |
| 500–503 | Server problem | Yes |

### Why Parquet, not CSV
Parquet keeps data types (dates stay dates, numbers stay numbers), is smaller
and loads much faster. CSV turns everything into text.

### Why logging, not print
Logging adds a time and level (INFO, WARNING) and also writes to
`logs/pipeline.log`, so you can see what happened while you were away.

**Check yourself**
1. What happens if you forget `.gitignore` before your first commit?
2. Why does `save()` refuse an empty table?
3. Which HTTP errors are retried, and why not the others?

**Your task:** add `print(fred)` in a notebook. Which method controls what is printed? (`__repr__`)

---

## Lesson 1 — FRED (`fred_source.py`)

**Course link:** Data Wrangling session 2 (data collection)

### Step by step
1. Create a free account at https://fredaccount.stlouisfed.org and request an API key.
2. Paste it into `.env` as `FRED_API_KEY=...`
3. Run `python update_all.py fred`

### How the code works
1. `_request()` builds the parameters: `series_id`, `api_key`, `file_type=json`, `observation_start`.
2. FRED writes missing values as `"."`. `_to_frame()` turns them into `NaN` with `pd.to_numeric(..., errors="coerce")`.
3. Dates are converted to UTC with `pd.to_datetime(..., utc=True)`.

### The most important idea: first release vs revised data
CPI for **August** is published in **mid-September**. Later it may be revised.

| Method | Gives you | Use for |
|---|---|---|
| `download()` | Today's revised values | Charts, understanding history |
| `download_first_release()` | The first published value + `release_date` | Training your AI model |

If your model uses August CPI on 1 August, it is "seeing the future". This is
called **look-ahead bias**, and it is the number one reason trading models look
great in testing and fail live. `output_type=4` asks FRED for the initial
release only, and `realtime_start` tells you the day it became public.

### The series we download
| ID | Meaning | Frequency |
|---|---|---|
| DEXUSEU | EUR/USD rate | Daily |
| FEDFUNDS | Fed Funds rate | Monthly |
| ECBDFR | ECB deposit rate | Daily |
| DGS10 | US 10-year yield | Daily |
| IRLTLT01DEM156N | Germany 10-year yield | Monthly |
| CPIAUCSL | US CPI | Monthly |
| UNRATE | US unemployment | Monthly |
| T10Y2Y | US yield curve | Daily |

**Why these?** EUR/USD mostly follows the **difference** between US and
Eurozone interest rates. When US rates rise faster than Eurozone rates,
money flows to the dollar and EUR/USD tends to fall.

**Check yourself**
1. Why are there fewer rows after `download()` than FRED shows on its website?
2. In `fred_CPIAUCSL_first_release.parquet`, how many days after the month-end is CPI usually released?

**Your task:** add `PCEPI` (the Fed's favourite inflation measure) to `FRED_SERIES` in `config.py` and run again.

---

## Lesson 2 — OANDA (`oanda_source.py`)

**Course link:** ICTPRG302 session 4 (loops), SCOOP session 12 (OOP)

### Step by step
1. Open a free **practice** account at oanda.com.
2. My Account → Manage API Access → Generate token.
3. Paste into `.env`: `OANDA_TOKEN`, `OANDA_ACCOUNT_ID`, `OANDA_ENV=practice`
4. Run `python update_all.py oanda`

### How the code works
- **Authentication:** the token goes in a header: `Authorization: Bearer <token>`. Not in the URL.
- **Practice vs live:** two different base URLs. The code only allows `"practice"` or `"live"`.
- **Pagination loop:** OANDA returns at most **5,000 candles** per request. Two years of hourly data is about 12,000 candles, so the `while` loop asks page by page, moving `cursor` forward to the last candle received. A safety check stops the loop if it stops moving forward (no infinite loops).
- **`complete`:** the newest candle is still forming. We skip it, because its close will change.
- **`price="MBA"`:** we ask for Mid, Bid and Ask. `spread = ask - bid` is your trading cost.

### Forex facts to understand
- **Pip:** for EUR/USD, 0.0001. A spread of 0.00008 = 0.8 pips.
- **Tick volume ≠ real volume.** Forex has no central exchange, so nobody knows the total volume. OANDA counts how many times the price changed. It still rises when the market is busy, so it's a useful proxy. For real volume and order flow, later you'll use CME Euro futures (6E).
- **Granularity:** `M1, M5, M15, M30, H1, H4, D, W`.
- **Daily candle time:** OANDA daily candles close at 17:00 New York time by default.

**Check yourself**
1. Why is the token sent in a header and not in the URL?
2. What would happen without the "not moving forward" check?
3. Why is the average spread larger at 05:00 Perth time than at 15:00?

**Your task:** download `GBP_USD` and `XAU_USD` H4 candles. Compare their average spread in pips.

---

## Lesson 3 — Forex Factory calendar (`forexfactory_source.py`)

**Course link:** ICTPRG302 session 6 (strings), Data Wrangling sessions 4–5 (cleaning, validation)

### Where the data comes from
Forex Factory has no official API. It publishes a free weekly JSON file:
`https://nfs.faireconomy.media/ff_calendar_thisweek.json`

Each event looks like this (real row):
```json
{"title": "Unemployment Claims", "country": "USD", "date": "2026-09-24T08:30:00-04:00",
 "impact": "Medium", "forecast": "201K", "previous": "196K"}
```

### Three limits you must know
1. **Only this week.** There is no history. That's why `save_history()` exists: run it every week and the history file grows. Duplicates are removed with `event_id`.
2. **No `actual` column.** The feed shows forecast and previous only. For your *surprise* feature (`actual - forecast`) you need actual values from another place — for US data, FRED first-release values are the best source. The column `actual_value` is ready to fill.
3. **Be polite.** Download a few times per day at most. The site can block you if you download too often.

### Cleaning steps in `clean()`
| Problem | Fix |
|---|---|
| `"country"` is really a currency | Rename to `currency`, add a real `country` column |
| Time is New York time (`-04:00`) | `pd.to_datetime(..., utc=True)` → 08:30 NY becomes 12:30 UTC (20:30 Perth) |
| Values are text: `"201K"`, `"4.5%"`, `"-258B"` | `parse_value()` turns them into numbers |
| Impact is a word | `impact_level`: Holiday 0, Low 1, Medium 2, High 3 |
| Feed format might change one day | `clean()` checks the required columns and raises a clear error |

### `parse_value()` — string skills
It uses a **regular expression**: `([<>]?)(-?\d+(?:\.\d+)?)([KMBT%]?)`
- `-?` optional minus sign
- `\d+(?:\.\d+)?` a number, maybe with decimals
- `[KMBT%]?` an optional suffix
Then it multiplies: K = 1,000, M = 1,000,000, B = 1,000,000,000.

**Check yourself**
1. What is 09:45 New York time (EDT, UTC−4) in UTC and in Perth time?
2. Why can't you calculate the surprise from this feed alone?
3. What happens if you run `save_history()` twice in the same week?

**Your task:** use `filter_events()` to list only High-impact USD events this week, and schedule `python update_all.py ff` to run every Sunday (Windows Task Scheduler).

---

## Lesson 4 — Yahoo Finance (`yahoo_source.py`)

**Course link:** Data Wrangling session 3 (unifying data)

### What it gives you
Daily data for markets that affect EUR/USD:
| Ticker | Market | Why it matters |
|---|---|---|
| DX-Y.NYB | US Dollar Index | EUR is about 58% of DXY — they move almost opposite |
| ^VIX | Fear index | High VIX = "risk-off" = money goes to USD |
| ^GSPC | S&P 500 | Risk mood |
| GC=F | Gold | Often moves opposite to the dollar |
| EURUSD=X | EUR/USD | A second source to compare with OANDA |

### How the code works
- `yfinance` is **unofficial** (it reads Yahoo's website). Fine for learning, not for live trading.
- New versions return two-level column names (`Close`, `^VIX`). `tidy()` flattens them and makes names lower-case.
- Yahoo sometimes returns an empty table for no reason, so `download()` tries 3 times.

**Check yourself**
1. Why do we keep our own `tidy()` instead of using Yahoo's columns directly?
2. Compare `yahoo_EURUSD_X.parquet` with `oanda_EUR_USD_D.parquet` for the same day. Why are the closes slightly different?

**Your task:** add `^TNX` (US 10-year yield) and compare it with FRED `DGS10`.

---

## Lesson 5 — The pipeline (`update_all.py`) and tests

**Course link:** SCOOP sessions 13 and 0x0F (acceptance criteria, unit testing)

### Why one failure doesn't stop everything
Each source runs inside `try/except`. If OANDA fails, FRED and Yahoo still
download. At the end, a summary lists OK / FAILED / SKIPPED, and the script
exits with code 1 if anything failed (useful for schedulers).

### How the tests work without internet
`unittest.mock.patch` replaces `_get_json` with a fake that returns fixed data.
So we test *our* code (cleaning, loops, UTC conversion), not the internet.
`tmp_path` is a temporary folder from pytest, so tests never touch your real `data/`.

`@pytest.mark.parametrize` runs one test with many inputs (see `test_parse_value`).

**Check yourself**
1. Why is it good that tests don't need internet?
2. Which test proves that the OANDA loop collects all pages?

**Your task:** write one new test: `parse_value("1.2T")` should return 1.2e12.

---

## After Module 1 — what comes next

Module 2 (Data Engineering) uses these raw files to:
merge daily prices with monthly macro data using release dates (`merge_asof`),
clean, validate, and build `rate_diff` and `yield_spread`.
