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
        ["RSI Strategy V1 (recommended)", "RSI Reversal", "RSI + Trend Filter", "SMA Crossover"]
    )

    strategy_map = {
        "RSI Strategy V1 (recommended)": "rsi_v1",
        "RSI Reversal": "rsi_reversal",
        "RSI + Trend Filter": "rsi_trend",
        "SMA Crossover": "sma_crossover",
    }
    strategy_name = strategy_map[strategy_label]

    # ---- Strategy-specific parameters ----
    params = {}

    if strategy_name == "rsi_v1":
        st.sidebar.caption("Use 15m timeframe. No stop-loss. TP around 4% works well.")
        entry_rsi = st.sidebar.slider("Entry RSI (buy below)", min_value=5, max_value=50, value=25, step=1)
        exit_rsi = st.sidebar.slider("Exit RSI (sell above)", min_value=50, max_value=95, value=80, step=1)
        params.update({"entry_rsi": entry_rsi, "exit_rsi": exit_rsi})

    elif strategy_name == "rsi_reversal":
        lower = st.sidebar.slider("RSI lower (buy below)", min_value=5, max_value=50, value=30, step=1)
        upper = st.sidebar.slider("RSI upper (sell above)", min_value=50, max_value=95, value=70, step=1)
        params.update({"lower": lower, "upper": upper})

    elif strategy_name == "rsi_trend":
        lower = st.sidebar.slider("RSI lower (buy below)", min_value=5, max_value=50, value=30, step=1)
        upper = st.sidebar.slider("RSI upper (exit above)", min_value=50, max_value=95, value=60, step=1)
        trend_ma = st.sidebar.slider("Trend MA period", min_value=5, max_value=50, value=20, step=1)
        params.update({"lower": lower, "upper": upper, "trend_ma": trend_ma})

    elif strategy_name == "sma_crossover":
        fast = st.sidebar.slider("Fast SMA", min_value=5, max_value=50, value=10, step=1)
        slow = st.sidebar.slider("Slow SMA", min_value=5, max_value=50, value=20, step=1)
        if fast >= slow:
            st.sidebar.warning("Fast SMA should be smaller than Slow SMA.")
        params.update({"fast": fast, "slow": slow})

    # ---- Risk management: SL / TP ----
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Risk Management**")

    sl_percent = st.sidebar.slider("Stop-loss (%)", min_value=0.0, max_value=10.0, value=2.0, step=0.1)
    tp_percent = st.sidebar.slider("Take-profit (%)", min_value=0.0, max_value=20.0, value=4.0, step=0.1)

    stop_loss_pct = sl_percent / 100 if sl_percent > 0 else None
    take_profit_pct = tp_percent / 100 if tp_percent > 0 else None

    # ---- Run backtest ----
    if st.sidebar.button("Run Backtest"):
        with st.spinner("Fetching data and running backtest..."):
            df = get_historical_klines(symbol=symbol, interval=interval, limit=limit)
            df = add_indicators(df)
            df = generate_signals(df, strategy=strategy_name, **params)
            result = run_backtest(
                df,
                initial_balance=10_000.0,
                fee_rate=0.0004,
                stop_loss_pct=stop_loss_pct,
                take_profit_pct=take_profit_pct,
            )

        stats = result["stats"]

        st.subheader(f"Results for {symbol} ({interval}) using {strategy_label}")
        st.write(f"Initial balance: {result['initial_balance']:.2f} USDT")
        st.write(f"Final equity:    {result['final_equity']:.2f} USDT")
        st.write(f"Total return:    {result['total_return_pct']:.2f}%")

        if stats["num_trades"] == 0:
            st.info("No trades triggered with these settings. Try changing the parameters or timeframe.")
            return

        st.markdown("### Stats")
        st.write(f"Trades:          {stats['num_trades']}")
        st.write(f"Win rate:        {stats['win_rate_pct']:.2f}%")
        st.write(f"Avg trade:       {stats['avg_return_pct']:.2f}%")
        st.write(f"Avg win:         {stats['avg_win_pct']:.2f}%")
        st.write(f"Avg loss:        {stats['avg_loss_pct']:.2f}%")
        st.write(f"Max drawdown:    {stats['max_drawdown_pct']:.2f}%")

        if stats["exit_reasons"]:
            st.markdown("**Exit reasons:**")
            for reason, count in stats["exit_reasons"].items():
                st.write(f"- {reason}: {count}")

        st.markdown("### Equity Curve")
        st.line_chart(result["equity_curve"]["equity"])

        if not result["trades"].empty:
            st.markdown("### Trades (first 10)")
            st.dataframe(result["trades"].head(10))



if __name__ == "__main__":
    main()
