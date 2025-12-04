# src/config.py
import os
from dotenv import load_dotenv
from binance.client import Client

# Load .env from config/.env
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, "config", ".env")
load_dotenv(ENV_PATH)

TRADING_ENV = os.getenv("TRADING_ENV", "testnet").lower()
LIVE_TRADING_CONFIRMATION = os.getenv("LIVE_TRADING_CONFIRMATION", "")


def get_binance_client() -> Client:
    """
    Return a Binance client configured for either testnet or live,
    based on TRADING_ENV in .env.
    """
    if TRADING_ENV == "testnet":
        api_key = os.getenv("BINANCE_TESTNET_API_KEY") or os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_TESTNET_API_SECRET") or os.getenv("BINANCE_API_SECRET")
        if not api_key or not api_secret:
            raise RuntimeError("Missing BINANCE_TESTNET_API_KEY / BINANCE_TESTNET_API_SECRET in .env")
        return Client(api_key, api_secret, testnet=True)

    if TRADING_ENV == "live":
        api_key = os.getenv("BINANCE_LIVE_API_KEY")
        api_secret = os.getenv("BINANCE_LIVE_API_SECRET")
        if not api_key or not api_secret:
            raise RuntimeError("Missing BINANCE_LIVE_API_KEY / BINANCE_LIVE_API_SECRET in .env")
        # Live Spot client (testnet=False)
        return Client(api_key, api_secret, testnet=False)

    raise RuntimeError(f"Unknown TRADING_ENV: {TRADING_ENV}")


def ensure_live_trading_allowed():
    """
    Hard safety gate: prevents live trading unless confirmation flag is set.
    """
    if TRADING_ENV == "live":
        if LIVE_TRADING_CONFIRMATION != "YES_I_UNDERSTAND_THE_RISK":
            raise RuntimeError(
                "Live trading is BLOCKED.\n"
                "To enable, set LIVE_TRADING_CONFIRMATION=YES_I_UNDERSTAND_THE_RISK in config/.env"
            )
