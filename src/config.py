import os 
from dotenv import load_dotenv
from binance.client import Client

# load env
load_dotenv("config/.env")

TRADING_ENV = os.getenv("TRADING_ENV", "testnet")
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

if not API_KEY or not API_SECRET:
    raise RuntimeError("Missing BINANCE_API_KEY or BINANCE_API_SECRET in .env")

def get_binance_client() -> Client:
    """
    Return a Binance client configured for testnet.
    """
    if TRADING_ENV == "testnet":
        client = Client(API_KEY, API_SECRET, testnet=True)
    else:
        # For live trading
        client = Client(API_KEY, API_SECRET)
    
    return client