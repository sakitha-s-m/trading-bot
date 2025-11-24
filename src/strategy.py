def generate_signal(df):
    """
    Uses the last candle and indicators to decide:
    BUY / SELL / HOLD
    """

    # Get the last candle
    last = df.iloc[-1]

    # BUY CONDITIONS
    buy_condition = (
        last['RSI'] < 30 and
        last['close'] > last['EMA20'] and
        last['MACD'] > last['MACD_signal']
    )

    # SELL CONDITIONS
    sell_condition = (
        last['RSI'] > 70 or
        last['MACD'] < last['MACD_signal']
    )

    # Decide the output
    if buy_condition:
        return "BUY"
    
    if sell_condition:
        return "SELL"
    
    return "HOLD"