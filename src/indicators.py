import pandas as pd
import ta

def add_indicators(df):
    """
    Adds RSI, EMA, and MACD indicators to the dataframe.
    df must have a 'close' column.
    """

    #RSI (14)
    df['RSI'] = ta.momentum.RSIIndicator(
        close=df['close'],
        window=14
    ).rsi()

    #EMA indicators (20, 50, 200)
    df['EMA20'] = ta.trend.EMAIndicator(
        close=df['close'],
        window=20
    ).ema_indicator()

    df['EMA50'] = ta.trend.EMAIndicator(
        close=df['close'],
        window=50
    ).ema_indicator()

    df['EMA200'] = ta.trend.EMAIndicator(
        close=df['close'],
        window=200
    ).ema_indicator()

    # MACD indicators (12, 26, 9)
    macd = ta.trend.MACD(
        close=df['close'],
        window_slow=26,
        window_fast=12,
        window_sign=9
    )
    
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    df['MACD_diff'] = macd.macd_diff()

    return df