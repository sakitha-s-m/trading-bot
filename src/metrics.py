import numpy as np
import pandas as pd


def compute_metrics(
    equity_curve: pd.Series,
    trades_df: pd.DataFrame,
    ann_factor: float = 252,
) -> dict:
    """
    Compute risk-adjusted performance metrics from an equity curve and trade list.

    ann_factor: periods per year for annualizing returns.
      - 15m candles → 35_040
      - 1h  candles →  8_760
      - 1d  candles →    365
    """
    metrics: dict = {}

    returns = equity_curve.pct_change().dropna()
    n = len(returns)

    # --- Sharpe ratio ---
    if n > 1 and returns.std() > 0:
        metrics["sharpe"] = float((returns.mean() / returns.std()) * np.sqrt(ann_factor))
    else:
        metrics["sharpe"] = 0.0

    # --- Sortino ratio (penalises downside volatility only) ---
    downside = returns[returns < 0]
    if len(downside) > 1 and downside.std() > 0:
        metrics["sortino"] = float((returns.mean() / downside.std()) * np.sqrt(ann_factor))
    else:
        metrics["sortino"] = 0.0

    # --- Total return ---
    if len(equity_curve) >= 2:
        metrics["total_return_pct"] = float(
            (equity_curve.iloc[-1] / equity_curve.iloc[0] - 1) * 100
        )
    else:
        metrics["total_return_pct"] = 0.0

    # --- Max drawdown ---
    rolling_max = equity_curve.cummax()
    drawdown = (equity_curve - rolling_max) / rolling_max
    metrics["max_drawdown_pct"] = float(drawdown.min() * 100)

    # --- Calmar ratio (annualised return / max drawdown) ---
    if metrics["max_drawdown_pct"] < 0 and n > 0:
        ann_return = (1 + metrics["total_return_pct"] / 100) ** (ann_factor / n) - 1
        metrics["calmar"] = float(ann_return / abs(metrics["max_drawdown_pct"] / 100))
    else:
        metrics["calmar"] = 0.0

    # --- Trade-level stats ---
    if not trades_df.empty and "return_pct" in trades_df.columns:
        metrics["num_trades"] = len(trades_df)
        wins = trades_df["return_pct"] > 0
        metrics["win_rate_pct"] = float(wins.mean() * 100)
        metrics["avg_return_pct"] = float(trades_df["return_pct"].mean())

        gross_wins = trades_df.loc[wins, "return_pct"].sum()
        gross_losses = abs(trades_df.loc[~wins, "return_pct"].sum())
        metrics["profit_factor"] = (
            float(gross_wins / gross_losses) if gross_losses > 0 else float("inf")
        )
    else:
        metrics["num_trades"] = 0
        metrics["win_rate_pct"] = 0.0
        metrics["avg_return_pct"] = 0.0
        metrics["profit_factor"] = 0.0

    return metrics
