# src/backtester.py
import itertools
import pandas as pd


def run_backtest(
    df: pd.DataFrame,
    initial_balance: float = 10_000.0,
    fee_rate: float = 0.0004,
    stop_loss_pct: float | None = None,
    take_profit_pct: float | None = None,
    atr_stop_multiplier: float | None = None,
    atr_col: str = "ATR_14",
) -> dict:
    """
    Event-driven backtester.
      - signal  1 → go long
      - signal -1 → exit to cash
      - no shorting

    Stop-loss priority (highest wins):
      atr_stop_multiplier → stop at entry − N×ATR (adaptive)
      stop_loss_pct       → stop at entry × (1 − pct) (fixed %)
    If both are set, atr_stop_multiplier takes precedence.
    When SL and TP both trigger on the same bar, SL wins (conservative).
    """
    df = df.copy()
    if "signal" not in df:
        raise ValueError("DataFrame must have 'signal' column from strategy.generate_signals")

    balance_usdt = initial_balance
    position_size = 0.0
    position_state = "CASH"

    equity_curve = []
    trades = []

    entry_price = None
    entry_time  = None
    stop_level  = None  # computed once on entry, cleared on exit
    tp_level    = None  # computed once on entry, cleared on exit

    for timestamp, row in df.iterrows():
        price_close = row["close"]
        price_high  = row["high"]
        price_low   = row["low"]
        sig = row["signal"]

        # --- Manage open position ---
        if position_state == "LONG":
            hit_tp = tp_level is not None and price_high >= tp_level
            hit_sl = stop_level is not None and price_low <= stop_level

            if hit_sl:
                exit_reason = "stop_loss"
                exit_price  = stop_level
            elif hit_tp:
                exit_reason = "take_profit"
                exit_price  = tp_level
            else:
                exit_reason = None
                exit_price  = None

            if hit_tp or hit_sl:
                balance_usdt   = position_size * exit_price * (1 - fee_rate)
                position_size  = 0.0
                position_state = "CASH"
                trade_return   = (exit_price - entry_price) / entry_price * 100
                trades.append({
                    "entry_time":  entry_time,
                    "exit_time":   timestamp,
                    "entry_price": entry_price,
                    "exit_price":  exit_price,
                    "return_pct":  trade_return,
                    "exit_reason": exit_reason,
                })
                entry_price = entry_time = stop_level = tp_level = None

            elif sig == -1:
                balance_usdt   = position_size * price_close * (1 - fee_rate)
                position_size  = 0.0
                position_state = "CASH"
                trade_return   = (price_close - entry_price) / entry_price * 100
                trades.append({
                    "entry_time":  entry_time,
                    "exit_time":   timestamp,
                    "entry_price": entry_price,
                    "exit_price":  price_close,
                    "return_pct":  trade_return,
                    "exit_reason": "signal",
                })
                entry_price = entry_time = stop_level = tp_level = None

        # --- Check for new entry ---
        if position_state == "CASH" and sig == 1:
            entry_price    = price_close
            entry_time     = timestamp
            position_size  = (balance_usdt * (1 - fee_rate)) / entry_price
            balance_usdt   = 0.0
            position_state = "LONG"

            # Compute stop level once on entry
            atr_val = row.get(atr_col) if atr_col in row.index else None
            if atr_stop_multiplier is not None and atr_val is not None and not pd.isna(atr_val):
                stop_level = entry_price - (atr_stop_multiplier * atr_val)
            elif stop_loss_pct is not None:
                stop_level = entry_price * (1 - stop_loss_pct)
            else:
                stop_level = None

            tp_level = entry_price * (1 + take_profit_pct) if take_profit_pct is not None else None

        # --- Mark-to-market equity ---
        equity = position_size * price_close if position_state == "LONG" else balance_usdt
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


# ---------------------------------------------------------------------------
# Walk-forward optimization
# ---------------------------------------------------------------------------

_ANN_FACTORS: dict[str, int] = {
    "1m":  525_600,
    "5m":  105_120,
    "15m":  35_040,
    "1h":    8_760,
    "4h":    2_190,
    "1d":      365,
}

_DEFAULT_PARAM_GRID: dict[str, list] = {
    "entry_rsi":           [20, 25, 30],
    "exit_rsi":            [65, 70, 75, 80],
    "take_profit_pct":     [0.02, 0.03, 0.04],
    "atr_stop_multiplier": [1.5, 2.0, 2.5],
}


def _grid_search(
    df: pd.DataFrame,
    param_grid: dict,
    initial_balance: float,
    fee_rate: float,
    ann_factor: float,
    min_trades: int = 3,
) -> tuple[dict, float]:
    """
    Grid-search param_grid on df, optimising for Sharpe ratio.
    Returns (best_params, best_sharpe).
    """
    from .indicators import add_indicators
    from .strategy import generate_signals
    from .metrics import compute_metrics

    best_sharpe = -float("inf")
    best_params = {k: v[0] for k, v in param_grid.items()}

    keys = list(param_grid.keys())
    for combo in itertools.product(*param_grid.values()):
        params = dict(zip(keys, combo))

        entry_rsi           = params.get("entry_rsi", 25)
        exit_rsi            = params.get("exit_rsi", 80)
        take_profit_pct     = params.get("take_profit_pct", 0.04)
        atr_stop_multiplier = params.get("atr_stop_multiplier", 2.0)

        df_i = add_indicators(df.copy())
        df_s = generate_signals(df_i, strategy="rsi_v1", entry_rsi=entry_rsi, exit_rsi=exit_rsi)
        result = run_backtest(
            df_s,
            initial_balance=initial_balance,
            fee_rate=fee_rate,
            take_profit_pct=take_profit_pct,
            atr_stop_multiplier=atr_stop_multiplier,
        )

        if result["stats"]["num_trades"] < min_trades:
            continue

        eq = result["equity_curve"]["equity"]
        m = compute_metrics(eq, result["trades"], ann_factor=ann_factor)

        if m["sharpe"] > best_sharpe:
            best_sharpe = m["sharpe"]
            best_params = params

    return best_params, best_sharpe


def walk_forward(
    df: pd.DataFrame,
    train_size: int = 2000,
    test_size: int = 500,
    param_grid: dict | None = None,
    initial_balance: float = 10_000.0,
    fee_rate: float = 0.001,
    interval: str = "15m",
) -> dict:
    """
    Walk-forward optimisation and out-of-sample (OOS) evaluation.

    For each rolling window:
      1. Grid-search param_grid on the training slice → maximise Sharpe.
      2. Evaluate out-of-sample on the test slice with those params.
      3. Roll forward by test_size candles.

    Returns:
      windows        — list of per-window dicts (params, metrics)
      oos_equity     — pd.Series: chained OOS equity curve
      overall_metrics — metrics over the full OOS period
    """
    from .indicators import add_indicators
    from .strategy import generate_signals
    from .metrics import compute_metrics

    if param_grid is None:
        param_grid = _DEFAULT_PARAM_GRID

    ann_factor = float(_ANN_FACTORS.get(interval, 252))

    windows: list[dict] = []
    oos_pieces: list[pd.Series] = []
    current_balance = initial_balance

    start = 0
    window_num = 1

    while start + train_size + test_size <= len(df):
        df_train = df.iloc[start : start + train_size]
        df_test  = df.iloc[start + train_size : start + train_size + test_size]

        print(
            f"[WF] Window {window_num:>2}: "
            f"train {df_train.index[0].date()} → {df_train.index[-1].date()} | "
            f"test  {df_test.index[0].date()} → {df_test.index[-1].date()}"
        )

        best_params, train_sharpe = _grid_search(
            df_train, param_grid, initial_balance, fee_rate, ann_factor
        )

        df_test_i = add_indicators(df_test.copy())
        df_test_s = generate_signals(
            df_test_i,
            strategy="rsi_v1",
            entry_rsi=best_params["entry_rsi"],
            exit_rsi=best_params["exit_rsi"],
        )
        test_result = run_backtest(
            df_test_s,
            initial_balance=current_balance,
            fee_rate=fee_rate,
            take_profit_pct=best_params["take_profit_pct"],
            atr_stop_multiplier=best_params["atr_stop_multiplier"],
        )

        eq = test_result["equity_curve"]["equity"]
        test_m = compute_metrics(eq, test_result["trades"], ann_factor=ann_factor)

        pf = test_m["profit_factor"]
        windows.append(
            {
                "window":                window_num,
                "train_start":           str(df_train.index[0].date()),
                "train_end":             str(df_train.index[-1].date()),
                "test_start":            str(df_test.index[0].date()),
                "test_end":              str(df_test.index[-1].date()),
                "best_params":           best_params,
                "train_sharpe":          round(train_sharpe, 3),
                "test_sharpe":           round(test_m["sharpe"], 3),
                "test_sortino":          round(test_m["sortino"], 3),
                "test_return_pct":       round(test_m["total_return_pct"], 2),
                "test_num_trades":       test_m["num_trades"],
                "test_win_rate_pct":     round(test_m["win_rate_pct"], 1),
                "test_max_drawdown_pct": round(test_m["max_drawdown_pct"], 2),
                "test_profit_factor":    round(pf, 2) if pf != float("inf") else "inf",
            }
        )

        current_balance = test_result["final_equity"]
        oos_pieces.append(eq)
        start += test_size
        window_num += 1

    if not oos_pieces:
        raise ValueError(
            f"Not enough data for a single walk-forward window. "
            f"Need {train_size + test_size} candles, got {len(df)}."
        )

    oos_equity = pd.concat(oos_pieces)
    overall = compute_metrics(oos_equity, pd.DataFrame(), ann_factor=ann_factor)

    return {
        "windows":         windows,
        "oos_equity":      oos_equity,
        "overall_metrics": overall,
    }
