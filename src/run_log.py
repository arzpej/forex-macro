from datetime import date, datetime
import getpass

LOG_FILE = "data/run_log.txt"          # history of every run
UPDATE_FILE = "data/last_update.txt"   # holds only one thing: the date of the last good update
UPDATE_EVERY_DAYS = 1                  # 1 = once a day, 7 = once a week, 30 = once a month


def write_log(message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{now} | {getpass.getuser()} | {message}"
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")
    print(line)


def last_update():
    # date of the last good update (None = never)
    try:
        with open(UPDATE_FILE) as f:
            return date.fromisoformat(f.read().strip())
    except FileNotFoundError:
        return None


def mark_updated():
    # write today's date into the update file
    with open(UPDATE_FILE, "w") as f:
        f.write(date.today().isoformat())


def update_needed():
    last = last_update()
    return last is None or (date.today() - last).days >= UPDATE_EVERY_DAYS