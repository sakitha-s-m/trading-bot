import pandas as pd
from binance.client import Client
from dotenv import load_dotenv
from indicators import add_indicators
from strategy import generate_signal
import os

load_dotenv("config/ .env")

API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

# Connecting to the Binance Testnet
client = Client(API_KEY, API_SECRET, testnet=True)

def get_klines(symbol="BTCUSDT", interval="1m", limit=200):
    """Fetch historical OHLCV price data."""
    candles = client.get_klines(symbol=symbol, interval=interval, limit=limit)

    df = pd.DataFrame(candles, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "num_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])

    # Clean and convert
    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["close"] = df["close"].astype(float)
    df["volume"] = df["volume"].astype(float)

    return df[["open", "high", "low", "close", "volume"]]

if __name__ == "__main__":
    # Fetch data
    df = get_klines()

    # Add indicators
    df = add_indicators(df)

    # Generate signals
    signal = generate_signal(df)

    print(df.tail())
    print("Current Signal:", signal)