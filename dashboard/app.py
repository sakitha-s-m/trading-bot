# dashboard/app.py
import os
import sys

# Add project root to sys.path
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
from src.wallet import get_equity_snapshot
from src.runtime_state import load_state, update_config_from_dashboard, set_bot_enabled

st.set_page_config(
    page_title="Trading Bot Dashboard",
    page_icon="📈",
    layout="wide",
)


def compute_live_stats(trades_df: pd.DataFrame, initial_equity: float):
    """
    Compute equity curve, PnL, win rate, max drawdown from live trades CSV.
    Expect columns with at least: 'pnl_usdt' or 'pnl_pct'.
    """
    if trades_df.empty:
        return {
            "equity_curve": None,
            "final_equity": initial_equity,
            "total_pnl_usdt": 0.0,
            "total_pnl_pct": 0.0,
            "num_trades": 0,
            "win_rate_pct": 0.0,
            "max_drawdown_pct": 0.0,
        }

    # Prefer pnl_usdt if available; else approximate from pnl_pct
    if "pnl_usdt" in trades_df.columns:
        pnl_usdt = trades_df["pnl_usdt"].astype(float)

    elif "pnl_pct" in trades_df.columns:
        pnl_usdt = initial_equity * trades_df["pnl_pct"].astype(float) / 100.0
    
    elif "return_pct" in trades_df.columns:
        pnl_usdt = initial_equity * trades_df["return_pct"].astype(float) / 100.0
    else:
        # Fallback: no PnL info, treat as 0
        pnl_usdt = pd.Series([0.0] * len(trades_df))

    equity = initial_equity + pnl_usdt.cumsum()
    equity_curve = pd.DataFrame({"equity": equity})

    final_equity = float(equity.iloc[-1])
    total_pnl_usdt = final_equity - initial_equity
    total_pnl_pct = (final_equity / initial_equity - 1.0) * 100.0

    num_trades = len(trades_df)
    if "pnl_usdt" in trades_df.columns:
        wins = (trades_df["pnl_usdt"] > 0).sum()
    elif "pnl_pct" in trades_df.columns:
        wins = (trades_df["pnl_pct"] > 0).sum()
    elif "return_pct" in trades_df.columns:
        wins = (trades_df["return_pct"].astype(float) > 0).sum()
    else:
        wins = 0
    win_rate_pct = (wins / num_trades * 100.0) if num_trades > 0 else 0.0

    # Max drawdown from equity curve
    running_max = equity.cummax()
    drawdown = (equity - running_max) / running_max
    max_drawdown_pct = drawdown.min() * 100.0  # negative value

    return {
        "equity_curve": equity_curve,
        "final_equity": final_equity,
        "total_pnl_usdt": total_pnl_usdt,
        "total_pnl_pct": total_pnl_pct,
        "num_trades": num_trades,
        "win_rate_pct": win_rate_pct,
        "max_drawdown_pct": float(max_drawdown_pct),
    }


def main():
    st.title("Trading Bot Dashboard")

    tab_backtest, tab_live = st.tabs(["📊 Backtest", "🤖 Live Trading"])

    # ======================================================
    # BACKTEST TAB
    # ======================================================
    with tab_backtest:
        st.subheader("Backtest Engine")

        cfg_col1, cfg_col2, cfg_col3 = st.columns([1.4, 1.4, 1.2])

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

        rs = load_state()  # runtime state from JSON

        # === Layout: top config + state ===
        col_cfg, col_state = st.columns([2, 1])

        with col_cfg:
            st.markdown("**Bot Configuration (saved to server)**")

            symbol_live = st.text_input("Symbol", value=rs["symbol"], key="live_symbol")
            interval_live = st.selectbox(
                "Interval",
                ["15m", "5m", "1m"],
                index=["15m", "5m", "1m"].index(rs["interval"]) if rs["interval"] in ["15m", "5m", "1m"] else 0,
                key="live_interval",
            )
            history_live = st.slider(
                "History candles",
                min_value=100,
                max_value=500,
                value=int(rs["history_candles"]),
                step=50,
                key="live_history",
            )

            entry_rsi_live = st.slider(
                "Entry RSI (buy below)",
                min_value=5,
                max_value=50,
                value=int(rs["entry_rsi"]),
                step=1,
                key="live_entry_rsi",
            )
            exit_rsi_live = st.slider(
                "Exit RSI (sell above)",
                min_value=50,
                max_value=95,
                value=int(rs["exit_rsi"]),
                step=1,
                key="live_exit_rsi",
            )
            tp_live = st.slider(
                "Take-profit (%)",
                min_value=0.0,
                max_value=10.0,
                value=float(rs["take_profit_pct"] * 100.0),
                step=0.5,
                key="live_tp",
            )

            size_live = st.number_input(
                "Position size (USDT per trade)",
                min_value=10.0,
                max_value=10_000.0,
                value=float(rs["position_size_usdt"]),
                step=10.0,
                key="live_size",
            )

            initial_eq = st.number_input(
                "Initial equity (USDT) for stats",
                min_value=100.0,
                max_value=1_000_000.0,
                value=float(rs["initial_equity_usdt"]),
                step=100.0,
                key="live_initial_eq",
            )

        with col_state:
            st.markdown("**Account & Bot State**")

            # current wallet snapshot from testnet
            snapshot = get_equity_snapshot(symbols=("BTCUSDT", "ETHUSDT"))
            equity = snapshot["equity_usdt"]
            pnl_pct_vs_initial = (equity / initial_eq - 1.0) * 100.0

            col_s1, col_s2 = st.columns(2)
            col_s1.metric("Initial Equity (USDT)", f"{initial_eq:.2f}")
            col_s2.metric("Current Equity (USDT)", f"{equity:.2f}")

            col_s3, col_s4 = st.columns(2)
            col_s3.metric("PnL vs Initial (%)", f"{pnl_pct_vs_initial:.2f}%")
            col_s4.metric("Bot Enabled", "Yes" if rs["bot_enabled"] else "No")

        # === Bot control buttons ===
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("▶️ Start Bot on Server", key="live_start"):
                update_config_from_dashboard(
                    symbol=symbol_live,
                    interval=interval_live,
                    history_candles=history_live,
                    position_size_usdt=size_live,
                    entry_rsi=entry_rsi_live,
                    exit_rsi=exit_rsi_live,
                    take_profit_pct=tp_live / 100.0,
                    initial_equity_usdt=initial_eq,
                    bot_enabled=True,
                )
                st.success("Bot ENABLED. The server daemon will start trading on next cycle.")

        with col_btn2:
            if st.button("⏸ Stop Bot on Server", key="live_stop"):
                set_bot_enabled(False)
                st.success("Bot DISABLED. The server daemon will stop trading on next cycle.")

        st.markdown("---")

        # === Live performance from CSV ===
        st.markdown("### Live Performance (from trade log)")

        logs_path = os.path.join(PROJECT_ROOT, "logs", "live_trades.csv")
        if os.path.exists(logs_path):
            trades_df = pd.read_csv(logs_path)
            stats = compute_live_stats(trades_df, initial_eq)

            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric("Final Equity (USDT)", f"{stats['final_equity']:.2f}")
            col_m2.metric("Total PnL (USDT)", f"{stats['total_pnl_usdt']:.2f}")
            col_m3.metric("Total PnL (%)", f"{stats['total_pnl_pct']:.2f}%")
            col_m4.metric("Win Rate (%)", f"{stats['win_rate_pct']:.2f}%")

            col_m5, col_m6 = st.columns(2)
            col_m5.metric("Trades", str(stats["num_trades"]))
            col_m6.metric("Max Drawdown (%)", f"{stats['max_drawdown_pct']:.2f}%")

            if stats["equity_curve"] is not None:
                st.markdown("#### Equity Curve (based on closed trades)")
                st.line_chart(stats["equity_curve"]["equity"])

            st.markdown("#### Live Trade History")
            st.dataframe(trades_df.iloc[::-1].reset_index(drop=True))
        else:
            st.info("No live trade log found yet. Once the bot closes trades, a logs/live_trades.csv file will be created.")


if __name__ == "__main__":
    main()
