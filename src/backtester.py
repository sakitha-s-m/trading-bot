# src/backtester.py
import pandas as pd

def run_backtest(
    df: pd.DataFrame,
    initial_balance: float = 10_000.0,
    fee_rate: float = 0.0004,  # 0.04% per trade
) -> dict:
    """
    Backtester based on 'signal' column.
    Assumes:
      - signal 1 => go long
      - signal -1 => exit to cash
      - no shorting
    """
    df = df.copy()
    if "signal" not in df:
        raise ValueError("DataFrame must have 'signal' column from strategy.generate_signals")

    balance_usdt = initial_balance
    position_size = 0.0  # amount of coin
    equity_curve = []
    position_state = "CASH"

    trades = []
    entry_price = None
    entry_time = None

    for timestamp, row in df.iterrows():
        price = row["close"]
        sig = row["signal"]

        # ENTER LONG
        if position_state == "CASH" and sig == 1:
            entry_price = price
            entry_time = timestamp

            position_size = (balance_usdt * (1 - fee_rate)) / price
            balance_usdt = 0.0
            position_state = "LONG"

        # EXIT LONG
        elif position_state == "LONG" and sig == -1:
            exit_price = price
            exit_time = timestamp

            balance_usdt = position_size * price * (1 - fee_rate)
            position_size = 0.0
            position_state = "CASH"

            # record trade stats (percentage)
            trade_return_pct = (exit_price - entry_price) / entry_price * 100
            trades.append({
                "entry_time": entry_time,
                "exit_time": exit_time,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "return_pct": trade_return_pct,
            })

            entry_price = None
            entry_time = None

        # Compute equity
        if position_state == "LONG":
            equity = position_size * price
        else:
            equity = balance_usdt

        equity_curve.append({"time": timestamp, "equity": equity})

    eq_df = pd.DataFrame(equity_curve).set_index("time")
    total_return = (eq_df["equity"].iloc[-1] / initial_balance) - 1

    trades_df = pd.DataFrame(trades)

    # Basic stats
    if not trades_df.empty:
        num_trades = len(trades_df)
        wins = (trades_df["return_pct"] > 0).sum()
        losses = (trades_df["return_pct"] <= 0).sum()
        win_rate = (wins / num_trades) * 100
        avg_return = trades_df["return_pct"].mean()
        avg_win = trades_df.loc[trades_df["return_pct"] > 0, "return_pct"].mean()
        avg_loss = trades_df.loc[trades_df["return_pct"] <= 0, "return_pct"].mean()
    else:
        num_trades = wins = losses = 0
        win_rate = avg_return = avg_win = avg_loss = 0.0

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
    }

    return {
        "equity_curve": eq_df,
        "final_equity": eq_df["equity"].iloc[-1],
        "total_return_pct": total_return * 100,
        "initial_balance": initial_balance,
        "trades": trades_df,
        "stats": stats,
    }
