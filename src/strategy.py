from numpy.char import lower
import pandas as pd

# ===========================================
# Strategy 1 - SMA CROSSOVER
# ===========================================
def sma_crossover_signals(df: pd.DataFrame, fast: int = 10, slow: int = 20) -> pd.DataFrame:
    """
    MA crossover strategy:
        - Buy when fast MA crosses above slow MA
        - Sell when fast MA crosses below slow MA
    """

    df = df.copy()

    fast_col = f"SMA_{fast}"
    slow_col = f"SMA_{slow}"

    if fast_col not in df or slow_col not in df:
        raise ValueError("Missing SMA indicators. Call add_indicators first.")
    
    df["signal"] = 0

    df["prev_fast"] = df[fast_col].shift(1)
    df["prev_slow"] = df[slow_col].shift(1)\

    buy_condition = (df["prev_fast"] <= df["prev_slow"]) & (df[fast_col] > df[slow_col])
    sell_condition = (df["prev_fast"] >= df["prev_slow"]) & (df[fast_col] < df[slow_col])

    df.loc[buy_condition, "signal"] = 1
    df.loc[sell_condition, "signal"] = -1
    
    df.drop(columns=["prev_fast", "prev_slow"], inplace=True)

    return df

# ===========================================
# Strategy 2 - RSI REVERSAL (generic)
# ===========================================

def rsi_reversal_signals(
    df: pd.DataFrame,
    lower: int = 30,
    upper: int = 70
) -> pd.DataFrame:
    """
    Simple RSI mean-reversion concept:
        - Buy when RSI < lower (oversold)
        - Sell wehn RSI > upper (overbought)
    """

    df = df.copy()

    if "RSI" not in df:
        raise ValueError("Missing RSI indicator. Call add_indicators first.")
    
    df["signal"] = 0

    buy_condition = df["RSI"] < lower
    sell_condition = df["RSI"] > upper

    df.loc[buy_condition, "signal"] = 1
    df.loc[sell_condition, "signal"] = -1

    return df

# ===========================================
# Strategy 3 - RSI + TREND FILTER
# ===========================================

def rsi_trend_signals(
    df: pd.DataFrame,
    lower: int = 30,
    upper: int = 60,
    trend_ma: int = 20
) -> pd.DataFrame:
    """
    RSI with trend filter:
        - Defgine uptrend as close > SMA(trend_ma)
        - Enter long when RSI < lower AND in uptrend
        - Exit when RSI > upper OR price falls below trend MA
    """
    df = df.copy()

    trend_col = f"SMA_{trend_ma}"
    if "RSI" not in df or trend_col not in df:
        raise ValueError("Missing RSI or trend SMA. Call add_indicators first.")
    
    df["signal"] = 0

    uptrend = df["close"] > df[trend_col]

    buy_condition = (df["RSI"] < lower) & uptrend
    sell_condition = (df["RSI"] > upper) | (~uptrend)

    df.loc[buy_condition, "signal"] = 1
    df.loc[sell_condition, "signal"] = -1

    return df

# ===========================================
# Strategy 4 - RSI STRATEGY V1 (tuned finalized version)
# ===========================================

def rsi_v1_signals(
    df: pd.DataFrame,
    entry_rsi: float = 25.0,
    exit_rsi: float = 80.0,
) -> pd.DataFrame:

    """
    Strategy V1:
        - Timeframe: 15 min
        - Entry long when RSI < entry_rsi
        - Exit long when RSI > exit_rsi
        - No stop-loss (handled at risk layer; recommended disabled)
        - Optional take-profit (e.g. 4%) handled in backtester / live trader
    """

    df = df.copy()

    if "RSI" not in df:
        raise ValueError("Missing RSI indicator. Call add_indicators first.")

    df["signal"] = 0

    buy_condition = df["RSI"] < entry_rsi
    sell_condition = df["RSI"] > exit_rsi

    df.loc[buy_condition, "signal"] = 1
    df.loc[sell_condition, "signal"] = -1

    return df

# ===========================================
# DISPATCHER (choose strategy)
# ===========================================

def generate_signals(
    df: pd.DataFrame,
    strategy: str = "sma_crossover",
    **params
) -> pd.DataFrame:
    """
    Dispatcher: apply the chosen strategy to the dataframe.
    strategy options:
        - 'sma_crossover'
        - 'rsi_reversal'
        - 'rsi_trend'
        - 'rsi_v1'
    """

    if strategy == "sma_crossover":
        fast = params.get("fast", 10)
        slow = params.get("slow", 20)
        return sma_crossover_signals(df, fast=fast, slow=slow)
    
    elif strategy == "rsi_reversal":
        lower = params.get("lower", 30)
        upper = params.get("upper", 70)
        return rsi_reversal_signals(df, lower=lower, upper=upper)

    elif strategy == "rsi_trend":
        lower = params.get("lower", 30)
        upper = params.get("upper", 60)
        trend_ma = params.get("trend_ma", 20)
        return rsi_trend_signals(df, lower=lower, upper=upper, trend_ma=trend_ma)
    
    elif strategy == "rsi_v1":
        entry_rsi = params.get("entry_rsi", 25.0)
        exit_rsi = params.get("exit_rsi", 80.0)
        return rsi_v1_signals(df, entry_rsi=entry_rsi, exit_rsi=exit_rsi)

    else:
        raise ValueError(f"Unknown strategy: {strategy}")
