import pandas as pd
from typing import Literal
from .config import get_binance_client

Interval = Literal["1m", "5m", "15m", "1h", "4h", "1d"]

def get_historical_klines(
    symbol: str = "BTCUSDT",
    interval: Interval = "1m",
    limit: int = 500
) -> pd.DataFrame:
    """
    Fetch historical OHLCV candles from Binance.
    """

    client = get_binance_client()
    candles = client.get_klines(symbol=symbol, interval=interval, limit=limit)

    cols = [
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "num_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ]

    df = pd.DataFrame(candles, columns=cols)

    # Convert
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df.set_index("open_time", inplace=True)

    return df[["open", "high", "low", "close", "volume"]]