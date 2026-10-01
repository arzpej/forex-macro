import pandas as pd
from src.FED_US import update_fred
from src.ECB_EU import update_ecb
from src.CHINA_CN import update_china
from src.UK import update_uk
from src.JAPAN import update_japan
from src.COT import update_cot
from src.database import export_clean
from src.run_log import write_log, last_update, mark_updated, update_needed
from charts import draw_rate_chart, draw_unemployment_chart
from fx_model import run_model
from model_charts import draw_model_charts

FORCE_UPDATE = False           # True = update now, even if already updated today

write_log("STARTED")

# 1 + 2. Update database and clean file - only if not updated today
if FORCE_UPDATE or update_needed():
    try:
        update_fred()
        update_ecb()
        update_china()
        update_uk()
        update_japan()
        update_cot()                                     # speculator positioning (CFTC)
        macro = export_clean()
        mark_updated()
        write_log(f"UPDATED - clean file has {len(macro)} rows")
    except Exception as error:
        write_log(f"FAILED - {error}")
        raise
else:
    write_log(f"SKIPPED - already updated on {last_update()}")

df = pd.read_csv("data/macro_clean.csv", parse_dates=["date"])

# 3. Country charts (rates, jobs)
for country in df["country"].unique():
    draw_rate_chart(df, country)
    draw_unemployment_chart(df, country)

# 4. The 3-layer model: economy -> policy -> FX pairs (with the WHY)
cs, pairs, regime = run_model(df)
draw_model_charts(cs, pairs, regime)

write_log("FINISHED")