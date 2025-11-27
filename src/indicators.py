# src/indicators.py
import pandas as pd

def add_sma(df: pd.DataFrame, period: int, column: str = "close") -> pd.DataFrame:
    df[f"SMA_{period}"] = df[column].rolling(window=period).mean()
    return df

def add_rsi(df: pd.DataFrame, period: int = 14, column: str = "close") -> pd.DataFrame:
    delta = df[column].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    return df

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:

    df = add_sma(df, 10) # fast MA
    df = add_sma(df, 20) # slow MA
    df = add_rsi(df, 14)
    return df
