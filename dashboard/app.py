# dashboard/app.py
import os
import sys

# Add project root to sys.path so 'src' is importable no matter where we run from
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
from src.data import get_historical_klines
from src.indicators import add_indicators
from src.strategy import generate_signals
from src.backtester import run_backtest

def main():
    st.title("Trading Bot Dashboard (Backtest)")

    symbol = st.sidebar.text_input("Symbol", value="BTCUSDT")
    interval = st.sidebar.selectbox("Interval", ["1m", "5m", "15m", "1h", "4h", "1d"])
    limit = st.sidebar.slider("Candles (history length)", min_value=100, max_value=1000, value=500, step=50)

    strategy_label = st.sidebar.selectbox(
        "Strategy",
        ["SMA Crossover", "RSI Reversal"]
    )

    # Map label to internal name
    strategy_map = {
        "SMA Crossover": "sma_crossover",
        "RSI Reversal": "rsi_reversal",
    }
    strategy_name = strategy_map[strategy_label]

    if st.sidebar.button("Run Backtest"):
        with st.spinner("Fetching data and running backtest..."):
            df = get_historical_klines(symbol=symbol, interval=interval, limit=limit)
            df = add_indicators(df)
            df = generate_signals(df, strategy=strategy_name)
            result = run_backtest(df)

        st.subheader(f"Results for {symbol} ({interval}) using {strategy_label}")
        st.write(f"Initial balance: {result['initial_balance']:.2f} USDT")
        st.write(f"Final equity:    {result['final_equity']:.2f} USDT")
        st.write(f"Total return:    {result['total_return_pct']:.2f}%")

        stats = result["stats"]
        st.markdown("### Stats")
        st.write(f"Trades:          {stats['num_trades']}")
        st.write(f"Win rate:        {stats['win_rate_pct']:.2f}%")
        st.write(f"Avg trade:       {stats['avg_return_pct']:.2f}%")
        st.write(f"Avg win:         {stats['avg_win_pct']:.2f}%")
        st.write(f"Avg loss:        {stats['avg_loss_pct']:.2f}%")
        st.write(f"Max drawdown:    {stats['max_drawdown_pct']:.2f}%")

        st.markdown("### Equity Curve")
        st.line_chart(result["equity_curve"]["equity"])

        if not result["trades"].empty:
            st.markdown("### Trades (first 10)")
            st.dataframe(result["trades"].head(10))

if __name__ == "__main__":
    main()
