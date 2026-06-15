# main_walkforward.py
import os
import pandas as pd

from src.data import get_historical_klines_extended
from src.backtester import walk_forward

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SYMBOL        = "ETHUSDT"
INTERVAL      = "1h"
TOTAL_CANDLES = 8760    # ~1 year of 1h data
TRAIN_SIZE    = 2000    # ~83 days per training window
TEST_SIZE     = 500     # ~21 days per test window  (~13 windows total)
INITIAL_BAL   = 1_000.0
FEE_RATE      = 0.001   # 0.1% Binance standard

# Param grid: grid-searched on each training window
PARAM_GRID = {
    "entry_rsi":           [20, 25, 30, 35],
    "exit_rsi":            [65, 70, 75, 80],
    "take_profit_pct":     [0.02, 0.03, 0.04, 0.05],
    "atr_stop_multiplier": [1.5, 2.0, 2.5],
}


def print_window_table(windows: list[dict]) -> None:
    col = (
        f"{'#':>3}  "
        f"{'Test Period':^23}  "
        f"{'Entry':>5}  "
        f"{'Exit':>4}  "
        f"{'TP%':>4}  "
        f"{'Trades':>6}  "
        f"{'Win%':>5}  "
        f"{'Ret%':>6}  "
        f"{'Sharpe':>7}  "
        f"{'DD%':>6}  "
        f"{'PF':>5}"
    )
    print(col)
    print("-" * len(col))

    for w in windows:
        p = w["best_params"]
        print(
            f"{w['window']:>3}  "
            f"{w['test_start']} → {w['test_end']}  "
            f"{p['entry_rsi']:>5}  "
            f"{p['exit_rsi']:>4}  "
            f"{p['take_profit_pct']*100:>3.0f}%  "
            f"{w['test_num_trades']:>6}  "
            f"{w['test_win_rate_pct']:>5.1f}  "
            f"{w['test_return_pct']:>+6.2f}  "
            f"{w['test_sharpe']:>7.3f}  "
            f"{w['test_max_drawdown_pct']:>6.2f}  "
            f"{str(w['test_profit_factor']):>5}"
        )


def print_overall(metrics: dict, initial_bal: float, final_bal: float) -> None:
    print(f"\n{'='*55}")
    print("  Overall Out-of-Sample Performance")
    print(f"{'='*55}")
    print(f"  Starting capital : ${initial_bal:,.2f}")
    print(f"  Final equity     : ${final_bal:,.2f}")
    print(f"  Total return     : {metrics['total_return_pct']:+.2f}%")
    print(f"  Sharpe ratio     : {metrics['sharpe']:.3f}")
    print(f"  Sortino ratio    : {metrics['sortino']:.3f}")
    print(f"  Calmar ratio     : {metrics['calmar']:.3f}")
    print(f"  Max drawdown     : {metrics['max_drawdown_pct']:.2f}%")
    print(f"{'='*55}")
    print()
    print("  How to read these numbers:")
    print("  Sharpe > 1.0  → good risk-adjusted return")
    print("  Sharpe > 2.0  → excellent")
    print("  Max DD < -10% → strategy risks a 10%+ losing streak")
    print("  Profit Factor > 1.5 → wins outweigh losses by 1.5×")


def main() -> None:
    print(f"=== Walk-Forward Backtest: {SYMBOL} {INTERVAL} ===\n")
    print(f"Fetching {TOTAL_CANDLES} candles from Binance...")

    df = get_historical_klines_extended(
        symbol=SYMBOL, interval=INTERVAL, total_candles=TOTAL_CANDLES
    )
    print(
        f"Data: {df.index[0].date()} → {df.index[-1].date()} "
        f"({len(df)} candles)\n"
    )

    result = walk_forward(
        df,
        train_size=TRAIN_SIZE,
        test_size=TEST_SIZE,
        param_grid=PARAM_GRID,
        initial_balance=INITIAL_BAL,
        fee_rate=FEE_RATE,
        interval=INTERVAL,
    )

    print("\n--- Per-Window Results (out-of-sample) ---")
    print_window_table(result["windows"])

    final_equity = float(result["oos_equity"].iloc[-1])
    print_overall(result["overall_metrics"], INITIAL_BAL, final_equity)

    # Save OOS equity curve
    os.makedirs("logs", exist_ok=True)
    oos_path = "logs/oos_equity.csv"
    result["oos_equity"].rename("equity").to_csv(oos_path)
    print(f"\nOOS equity curve saved → {oos_path}")
    print("Tip: plot it with `pd.read_csv('logs/oos_equity.csv', index_col=0).plot()`\n")


if __name__ == "__main__":
    main()
