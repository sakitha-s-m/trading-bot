# main_backtest.py
from src.data import get_historical_klines
from src.indicators import add_indicators
from src.strategy import generate_signals
from src.backtester import run_backtest

def main():
    symbol = "BTCUSDT"
    interval = "1m"
    limit = 500

    df = get_historical_klines(symbol=symbol, interval=interval, limit=limit)
    df = add_indicators(df)
    df = generate_signals(df)


    result = run_backtest(df)

    print(f"Backtest for {symbol} | {interval}")
    print(f"Initial balance: {result['initial_balance']:.2f} USDT")
    print(f"Final equity:    {result['final_equity']:.2f} USDT")
    print(f"Total return:    {result['total_return_pct']:.2f}%")

if __name__ == "__main__":
    main()
