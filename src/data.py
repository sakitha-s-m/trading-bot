import pandas as pd
from typing import Literal
from .config import get_binance_client

Interval = Literal["1m", "5m", "15m", "1h", "4h", "1d"]

_KLINE_COLS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_asset_volume", "num_trades",
    "taker_buy_base", "taker_buy_quote", "ignore",
]


def _parse_klines(candles: list) -> pd.DataFrame:
    df = pd.DataFrame(candles, columns=_KLINE_COLS)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"].astype("int64"), unit="ms")
    df = df.set_index("open_time")
    return df[["open", "high", "low", "close", "volume"]]


def get_historical_klines(
    symbol: str = "BTCUSDT",
    interval: Interval = "1m",
    limit: int = 500,
) -> pd.DataFrame:
    """Fetch up to 1000 candles from Binance (single request)."""
    client = get_binance_client()
    candles = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    return _parse_klines(candles)


def get_historical_klines_extended(
    symbol: str = "ETHUSDT",
    interval: Interval = "15m",
    total_candles: int = 3000,
) -> pd.DataFrame:
    """
    Fetch more than the Binance 1000-candle limit by paginating backwards.
    Starts from the current time and walks back until total_candles are collected.
    """
    client = get_binance_client()

    batches: list[pd.DataFrame] = []
    end_time: int | None = None
    fetched = 0

    while fetched < total_candles:
        limit = min(1000, total_candles - fetched)
        kwargs: dict = dict(symbol=symbol, interval=interval, limit=limit)
        if end_time is not None:
            kwargs["endTime"] = end_time

        raw = client.get_klines(**kwargs)
        if not raw:
            break

        batches.insert(0, _parse_klines(raw))
        fetched += len(raw)
        end_time = int(raw[0][0]) - 1  # one ms before the earliest candle in this batch

    if not batches:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    df = pd.concat(batches).sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df