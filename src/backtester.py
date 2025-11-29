# src/backtester.py
import pandas as pd


def run_backtest(
    df: pd.DataFrame,
    initial_balance: float = 10_000.0,
    fee_rate: float = 0.0004,            # 0.04% per trade
    stop_loss_pct: float | None = None,  # e.g. 0.02 for 2%
    take_profit_pct: float | None = None # e.g. 0.04 for 4%
) -> dict:
    """
    Backtester based on 'signal' column.
    Assumes:
      - signal 1 => go long
      - signal -1 => exit to cash
      - no shorting

    If stop_loss_pct / take_profit_pct are provided, exits can happen earlier,
    based on intrabar high/low (conservative assumption when both hit).
    """
    df = df.copy()
    if "signal" not in df:
        raise ValueError("DataFrame must have 'signal' column from strategy.generate_signals")

    balance_usdt = initial_balance
    position_size = 0.0           # amount of coin
    position_state = "CASH"

    equity_curve = []
    trades = []

    entry_price = None
    entry_time = None

    for timestamp, row in df.iterrows():
        price_close = row["close"]
        price_high = row["high"]
        price_low = row["low"]
        sig = row["signal"]

        # --- Manage open position first (SL/TP + signal exit) ---
        if position_state == "LONG":
            hit_tp = False
            hit_sl = False
            exit_reason = None
            exit_price = None

            # Take-profit condition
            if take_profit_pct is not None and entry_price is not None:
                tp_level = entry_price * (1 + take_profit_pct)
                if price_high >= tp_level:
                    hit_tp = True
                    exit_reason = "take_profit"
                    exit_price = tp_level

            # Stop-loss condition
            if stop_loss_pct is not None and entry_price is not None:
                sl_level = entry_price * (1 - stop_loss_pct)
                if price_low <= sl_level:
                    # If both SL and TP hit same bar, assume worst case (SL first)
                    hit_sl = True
                    exit_reason = "stop_loss"
                    exit_price = sl_level

            # If SL/TP hit, exit immediately
            if hit_tp or hit_sl:
                exit_time = timestamp

                balance_usdt = position_size * exit_price * (1 - fee_rate)
                position_size = 0.0
                position_state = "CASH"

                trade_return_pct = (exit_price - entry_price) / entry_price * 100
                trades.append({
                    "entry_time": entry_time,
                    "exit_time": exit_time,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "return_pct": trade_return_pct,
                    "exit_reason": exit_reason,
                })

                entry_price = None
                entry_time = None

            # If still long after SL/TP logic, check strategy exit signal
            elif sig == -1:
                exit_reason = "signal"
                exit_price = price_close
                exit_time = timestamp

                balance_usdt = position_size * exit_price * (1 - fee_rate)
                position_size = 0.0
                position_state = "CASH"

                trade_return_pct = (exit_price - entry_price) / entry_price * 100
                trades.append({
                    "entry_time": entry_time,
                    "exit_time": exit_time,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "return_pct": trade_return_pct,
                    "exit_reason": exit_reason,
                })

                entry_price = None
                entry_time = None

        # --- Check for new entries (after exits) ---
        if position_state == "CASH" and sig == 1:
            # enter long using all balance
            entry_price = price_close
            entry_time = timestamp

            position_size = (balance_usdt * (1 - fee_rate)) / entry_price
            balance_usdt = 0.0
            position_state = "LONG"

        # --- Compute equity at this bar ---
        if position_state == "LONG":
            equity = position_size * price_close
        else:
            equity = balance_usdt

        equity_curve.append({"time": timestamp, "equity": equity})

    # Build equity curve df
    eq_df = pd.DataFrame(equity_curve).set_index("time")
    total_return = (eq_df["equity"].iloc[-1] / initial_balance) - 1

    trades_df = pd.DataFrame(trades)

    # ---- Basic stats ----
    if not trades_df.empty:
        num_trades = len(trades_df)
        wins = (trades_df["return_pct"] > 0).sum()
        losses = (trades_df["return_pct"] <= 0).sum()
        win_rate = (wins / num_trades) * 100
        avg_return = trades_df["return_pct"].mean()
        avg_win = trades_df.loc[trades_df["return_pct"] > 0, "return_pct"].mean()
        avg_loss = trades_df.loc[trades_df["return_pct"] <= 0, "return_pct"].mean()

        exit_reason_counts = trades_df["exit_reason"].value_counts().to_dict()
    else:
        num_trades = wins = losses = 0
        win_rate = avg_return = avg_win = avg_loss = 0.0
        exit_reason_counts = {}

    # Max drawdown
    rolling_max = eq_df["equity"].cummax()
    drawdown = eq_df["equity"] / rolling_max - 1
    max_drawdown_pct = drawdown.min() * 100

    stats = {
        "num_trades": num_trades,
        "wins": wins,
        "losses": losses,
        "win_rate_pct": win_rate,
        "avg_return_pct": avg_return,
        "avg_win_pct": avg_win if pd.notna(avg_win) else 0.0,
        "avg_loss_pct": avg_loss if pd.notna(avg_loss) else 0.0,
        "max_drawdown_pct": max_drawdown_pct,
        "exit_reasons": exit_reason_counts,
    }

    return {
        "equity_curve": eq_df,
        "final_equity": eq_df["equity"].iloc[-1],
        "total_return_pct": total_return * 100,
        "initial_balance": initial_balance,
        "trades": trades_df,
        "stats": stats,
    }
