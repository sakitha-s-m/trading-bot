from binance.client import Client
from dotenv import load_dotenv
import os

load_dotenv("config/.env")

api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")

client = Client(api_key, api_secret, testnet=True)

try:
    print(client.get_account())
except Exception as e:
    print("Error:", e)