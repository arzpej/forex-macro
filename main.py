import pandas as pd
from src.FED_US import update_fred
from src.ECB_EU import update_ecb
from src.CHINA_CN import update_china
from src.UK import update_uk
from src.JAPAN import update_japan
from src.database import export_clean
from src.run_log import write_log, last_update, mark_updated, update_needed
from charts import draw_rate_chart, draw_unemployment_chart

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
        macro = export_clean()
        mark_updated()                                   # write today's date in data/last_update.txt
        write_log(f"UPDATED - clean file has {len(macro)} rows")
    except Exception as error:
        write_log(f"FAILED - {error}")
        raise
else:
    write_log(f"SKIPPED - already updated on {last_update()}")

# 3. Charts for every country in the file
df = pd.read_csv("data/macro_clean.csv", parse_dates=["date"])

for country in df["country"].unique():
    draw_rate_chart(df, country)
    draw_unemployment_chart(df, country)

write_log("FINISHED")