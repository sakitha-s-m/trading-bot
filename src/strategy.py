import pandas as pd

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add a 'signal' column:
    1 = long (buy / hold long)
    -1 = flat/exit (sell)
    0 = no position
    """
    df = df.copy()

    if "SMA_20" not in df or "SMA_50" not in df:
        raise ValueError("Missing SMA indicators. Call add_indicators first.")

    df["signal"] = 0

    # Simple crossover logic for the mvp
    df["prev_SMA_20"] = df["SMA_20"].shift(1)
    df["prev_SMA_50"] = df["SMA_50"].shift(1)

    # Buy signal: 20 crosses above 50
    buy_condition = (df["prev_SMA_20"] <= df["prev_SMA_50"]) & (df["SMA_20"] > df["SMA_50"])

    # Sell signal: 20 crosses above 50
    sell_condition = (df["prev_SMA_20"] >= df["prev_SMA_50"]) & (df["SMA_20"] < df["SMA_50"])

    # Optional: Use RSI filter
    df.loc[df["RSI"] < 50, "signal"] = -1

    # Clean up helper cols
    df.drop(columns=["prev_SMA_20", "prev_SMA_50"], inplace=True)

    return df

