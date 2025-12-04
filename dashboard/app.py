# dashboard/app.py
import os
import sys

# Add project root to sys.path so 'src' is importable no matter where we run from
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd
import streamlit as st

from src.data import get_historical_klines
from src.indicators import add_indicators
from src.strategy import generate_signals
from src.backtester import run_backtest
from src.live_trader import live_step_rsi_v1
from src.wallet import get_equity_snapshot

st.set_page_config(
    page_title="Trading Bot Dashboard",
    page_icon="📈",
    layout="wide",
)


def main():
    st.title("Trading Bot Dashboard")

    tab_backtest, tab_live = st.tabs(["📊 Backtest", "🤖 Live Trading"])

    # ======================================================
    # BACKTEST TAB
    # ======================================================
    with tab_backtest:
        st.subheader("Backtest Engine")

        cfg_col1, cfg_col2, cfg_col3 = st.columns([1.4, 1.4, 1.2])

        # --- Basic settings ---
        with cfg_col1:
            symbol = st.text_input("Symbol", value="BTCUSDT", key="bt_symbol")
            interval = st.selectbox(
                "Interval",
                ["1m", "5m", "15m", "1h", "4h", "1d"],
                index=2,
                key="bt_interval",
            )
            limit = st.slider(
                "Candles (history length)",
                min_value=100,
                max_value=2000,
                value=1000,
                step=100,
                key="bt_limit",
            )

        # --- Strategy selection + params ---
        with cfg_col2:
            strategy_label = st.selectbox(
                "Strategy",
                [
                    "RSI Strategy V1 (recommended)",
                    "RSI Reversal",
                    "RSI + Trend Filter",
                    "SMA Crossover",
                ],
                key="bt_strategy",
            )

            strategy_map = {
                "RSI Strategy V1 (recommended)": "rsi_v1",
                "RSI Reversal": "rsi_reversal",
                "RSI + Trend Filter": "rsi_trend",
                "SMA Crossover": "sma_crossover",
            }
            strategy_name = strategy_map[strategy_label]

            params = {}

            if strategy_name == "rsi_v1":
                st.caption("Use 15m timeframe. No stop-loss. TP around 4% worked well in your tests.")
                entry_rsi = st.slider(
                    "Entry RSI (buy below)",
                    min_value=5,
                    max_value=50,
                    value=25,
                    step=1,
                    key="bt_entry_rsi",
                )
                exit_rsi = st.slider(
                    "Exit RSI (sell above)",
                    min_value=50,
                    max_value=95,
                    value=80,
                    step=1,
                    key="bt_exit_rsi",
                )
                params.update({"entry_rsi": entry_rsi, "exit_rsi": exit_rsi})

            elif strategy_name == "rsi_reversal":
                lower = st.slider(
                    "RSI lower (buy below)",
                    min_value=5,
                    max_value=50,
                    value=30,
                    step=1,
                    key="bt_rsi_lower",
                )
                upper = st.slider(
                    "RSI upper (sell above)",
                    min_value=50,
                    max_value=95,
                    value=70,
                    step=1,
                    key="bt_rsi_upper",
                )
                params.update({"lower": lower, "upper": upper})

            elif strategy_name == "rsi_trend":
                lower = st.slider(
                    "RSI lower (buy below)",
                    min_value=5,
                    max_value=50,
                    value=30,
                    step=1,
                    key="bt_trend_lower",
                )
                upper = st.slider(
                    "RSI upper (exit above)",
                    min_value=50,
                    max_value=95,
                    value=60,
                    step=1,
                    key="bt_trend_upper",
                )
                trend_ma = st.slider(
                    "Trend MA period",
                    min_value=5,
                    max_value=50,
                    value=20,
                    step=1,
                    key="bt_trend_ma",
                )
                params.update({"lower": lower, "upper": upper, "trend_ma": trend_ma})

            elif strategy_name == "sma_crossover":
                fast = st.slider(
                    "Fast SMA",
                    min_value=5,
                    max_value=50,
                    value=10,
                    step=1,
                    key="bt_fast_sma",
                )
                slow = st.slider(
                    "Slow SMA",
                    min_value=5,
                    max_value=50,
                    value=20,
                    step=1,
                    key="bt_slow_sma",
                )
                if fast >= slow:
                    st.warning("Fast SMA should be smaller than Slow SMA.")
                params.update({"fast": fast, "slow": slow})

        # --- Risk management + run button ---
        with cfg_col3:
            st.markdown("**Risk Management (Backtest)**")
            sl_percent = st.slider(
                "Stop-loss (%)",
                min_value=0.0,
                max_value=10.0,
                value=0.0,
                step=0.1,
                key="bt_sl_pct",
            )
            tp_percent = st.slider(
                "Take-profit (%)",
                min_value=0.0,
                max_value=20.0,
                value=4.0,
                step=0.1,
                key="bt_tp_pct",
            )
            stop_loss_pct = sl_percent / 100 if sl_percent > 0 else None
            take_profit_pct = tp_percent / 100 if tp_percent > 0 else None

            run_backtest_btn = st.button("Run Backtest", key="bt_run")

        # --- Run backtest and show results ---
        if run_backtest_btn:
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

            st.markdown(
                f"### Results for **{symbol}** ({interval}) using **{strategy_label}**"
            )
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Initial Balance (USDT)", f"{result['initial_balance']:.2f}")
            col2.metric("Final Equity (USDT)", f"{result['final_equity']:.2f}")
            col3.metric("Total Return (%)", f"{result['total_return_pct']:.2f}")
            col4.metric("Win Rate (%)", f"{stats['win_rate_pct']:.2f}")

            if stats["num_trades"] == 0:
                st.info("No trades triggered with these settings. Try changing the parameters or timeframe.")
            else:
                st.markdown("#### Detailed Stats")
                st.write(f"Trades:          {stats['num_trades']}")
                st.write(f"Avg trade:       {stats['avg_return_pct']:.2f}%")
                st.write(f"Avg win:         {stats['avg_win_pct']:.2f}%")
                st.write(f"Avg loss:        {stats['avg_loss_pct']:.2f}%")
                st.write(f"Max drawdown:    {stats['max_drawdown_pct']:.2f}%")

                if stats["exit_reasons"]:
                    st.markdown("**Exit reasons:**")
                    for reason, count in stats["exit_reasons"].items():
                        st.write(f"- {reason}: {count}")

                st.markdown("#### Equity Curve")
                st.line_chart(result["equity_curve"]["equity"])

                if not result["trades"].empty:
                    st.markdown("#### Trades (first 10)")
                    st.dataframe(result["trades"].head(10))

    # ======================================================
    # LIVE TRADING TAB
    # ======================================================
    with tab_live:
        st.subheader("Live Trading — Strategy V1 (Testnet)")

        # --- Initialize session_state for live bot ---
        if "live_state" not in st.session_state:
            st.session_state["live_state"] = None
        if "live_logs" not in st.session_state:
            st.session_state["live_logs"] = []
        if "live_trades" not in st.session_state:
            st.session_state["live_trades"] = []

        col_cfg, col_state = st.columns([2, 1])

        # --- Live config ---
        with col_cfg:
            st.markdown("**Configuration**")

            symbol_live = st.text_input("Symbol", value="ETHUSDT", key="live_symbol")
            interval_live = st.selectbox(
                "Interval",
                ["15m", "5m", "1m"],
                index=0,
                key="live_interval",
            )
            history_live = st.slider(
                "History candles",
                min_value=100,
                max_value=500,
                value=200,
                step=50,
                key="live_history",
            )

            entry_rsi_live = st.slider(
                "Entry RSI (buy below)",
                min_value=5,
                max_value=50,
                value=25,
                step=1,
                key="live_entry_rsi",
            )
            exit_rsi_live = st.slider(
                "Exit RSI (sell above)",
                min_value=50,
                max_value=95,
                value=80,
                step=1,
                key="live_exit_rsi",
            )
            tp_live = st.slider(
                "Take-profit (%)",
                min_value=0.0,
                max_value=10.0,
                value=4.0,
                step=0.5,
                key="live_tp",
            )

            size_live = st.number_input(
                "Position size (USDT per trade)",
                min_value=10.0,
                max_value=10_000.0,
                value=100.0,
                step=10.0,
                key="live_size",
            )

        # --- Bot & account state ---
        with col_state:
            st.markdown("**Bot & Account State**")
            live_state = st.session_state["live_state"] or {
                "in_position": False,
                "entry_price": None,
                "position_size": 0.0,
            }

            # Get equity snapshot (USDT + BTC + ETH)
            snapshot = get_equity_snapshot(symbols=("BTCUSDT", "ETHUSDT"))

            equity = snapshot["equity_usdt"]
            pnl_pct = snapshot["pnl_pct"]

            col_s1, col_s2, col_s3 = st.columns(3)
            col_s1.metric("Equity (USDT)", f"{equity:.2f}")
            col_s2.metric("PnL vs 10,000 USDT", f"{pnl_pct:.2f}%")
            col_s3.metric("In position", "Yes" if live_state["in_position"] else "No")

            st.write(f"Entry price: {live_state['entry_price']}")
            st.write(f"Position size: {live_state['position_size']}")

        # --- Control buttons ---
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🚀 Run ONE live step now", key="live_step"):
                new_state, logs, new_trades = live_step_rsi_v1(
                    st.session_state["live_state"],
                    symbol=symbol_live,
                    interval=interval_live,
                    history_candles=history_live,
                    position_size_usdt=size_live,
                    entry_rsi=entry_rsi_live,
                    exit_rsi=exit_rsi_live,
                    take_profit_pct=tp_live / 100.0,
                )
                st.session_state["live_state"] = new_state
                st.session_state["live_logs"].extend(logs)
                st.session_state["live_trades"].extend(new_trades)

        with col_btn2:
            if st.button("🔄 Reset state & logs", key="live_reset"):
                st.session_state["live_state"] = None
                st.session_state["live_logs"] = []
                st.session_state["live_trades"] = []
                st.success("Live state & logs reset.")

        # --- Live log ---
        st.markdown("### Live Log")
        log_text = "\n".join(st.session_state["live_logs"][-50:])
        st.text_area("Log output", value=log_text, height=300)

        # --- Live trade history ---
        st.markdown("### Live Trade History")
        if st.session_state["live_trades"]:
            trades_df = pd.DataFrame(st.session_state["live_trades"])
            trades_df = trades_df.iloc[::-1].reset_index(drop=True)
            st.dataframe(trades_df)
        else:
            st.info("No completed live trades yet.")


if __name__ == "__main__":
    main()
