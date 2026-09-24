import requests
from src.config import OANDA_TOKEN, OANDA_ACCOUNT_ID, OANDA_URL

headers = {"Authorization": "Bearer " + OANDA_TOKEN}   # the token goes in the header

# --- Test 1: check your account ---
url = OANDA_URL + "/v3/accounts/" + OANDA_ACCOUNT_ID + "/summary"
response = requests.get(url, headers=headers, timeout=30)
print("Account status:", response.status_code)          # 200 = OK

account = response.json()["account"]
print("Balance:", account["balance"], account["currency"])

# --- Test 2: get the last 5 EUR/USD hourly candles ---
url = OANDA_URL + "/v3/instruments/EUR_USD/candles"
params = {"granularity": "H1", "count": 5}
response = requests.get(url, headers=headers, params=params, timeout=30)
print("\nCandles status:", response.status_code)

for candle in response.json()["candles"]:
    print(candle["time"][:16],
          "open:", candle["mid"]["o"],
          "close:", candle["mid"]["c"],
          "volume:", candle["volume"])