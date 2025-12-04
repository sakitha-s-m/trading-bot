from binance.client import Client
from dotenv import load_dotenv
import os

load_dotenv("config/.env")

api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")

client = Client(api_key, api_secret, testnet=True)

account = client.get_account()

print("=== BALANCES ===")
for bal in account["balances"]:
    free = float(bal["free"])
    locked = float(bal["locked"])
    if free > 0 or locked > 0:
        print(f"{bal['asset']}: free={bal['free']} locked={bal['locked']}")