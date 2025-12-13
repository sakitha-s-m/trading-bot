import os
import sys
from datetime import datetime

import pandas as pd
import streamlit as st

# Make 'src' importable
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.wallet import get_equity_snapshot  # you already have this

LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
TRADES_CSV_PATH = os.path.join(LOGS_DIR, "live_trades.csv")

# -------------------------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------------------------
def format_trade_time(ts: str) -> str:
    """
    Convert ISO timestamp to redable UTC time.
    """
    try:
        dt = datetime.fromisoformat(ts.replace("Z", ""))
        return dt.strftime("%d %b %Y . %H:%M UTC")
    except Exception:
        return ts

def format_exit_reason(reason: str) -> str:
    """
    Map internal exit reasons to human-friendly labels.
    """
    mapping = {
        "take_profit": "Take Profit",
        "signal": "RSI Exit",
        "stop_loss": "Stop Loss",
        "manual": "Manual Exit",
    }
    return mapping.get(reason, reason.replace("_", " ").title())

# -------------------------------------------------------------------
# STYLING
# -------------------------------------------------------------------
def inject_global_css():
    css = """
    /* Global background */
    .stApp {
        background: radial-gradient(circle at top left, #141927, #05060a 60%);
        color: #f3f4f6;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "SF Pro Text",
                     "Inter", sans-serif;
    }

    /* Main title */
    .main-title {
        font-size: 2.1rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        background: linear-gradient(90deg, #38bdf8, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.25rem;
    }

    .main-subtitle {
        font-size: 0.95rem;
        color: #9ca3af;
        margin-bottom: 1.5rem;
    }

    /* KPI cards container */
    .kpi-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.75rem;
        margin-bottom: 1.25rem;
    }

    .kpi-card {
        flex: 1 1 150px;
        background: radial-gradient(circle at top, #1a2236, #050814 90%);
        border-radius: 0.9rem;
        padding: 0.9rem 1rem;
        border: 1px solid rgba(148, 163, 184, 0.18);
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.9);
    }

    .kpi-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #9ca3af;
    }

    .kpi-value {
        margin-top: 0.25rem;
        font-size: 1.4rem;
        font-weight: 600;
    }

    .kpi-value.green {
        color: #4ade80;
    }

    .kpi-value.red {
        color: #f97373;
    }

    .kpi-meta {
        font-size: 0.7rem;
        color: #6b7280;
        margin-top: 0.1rem;
    }

    /* Section headers */
    .section-title {
        font-size: 1.05rem;
        font-weight: 600;
        margin-top: 1.5rem;
        margin-bottom: 0.2rem;
    }

    .section-subtitle {
        font-size: 0.8rem;
        color: #9ca3af;
        margin-bottom: 0.8rem;
    }

    /* Dataframe tweaks */
    .dataframe tbody tr:hover {
        background-color: rgba(55, 65, 81, 0.4);
    }

    /* Small badge */
    .pill {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        border-radius: 999px;
        padding: 0.25rem 0.65rem;
        font-size: 0.7rem;
        border: 1px solid rgba(148, 163, 184, 0.35);
        background: rgba(15, 23, 42, 0.8);
        color: #e5e7eb;
    }

    .pill-dot-green {
        width: 7px;
        height: 7px;
        border-radius: 999px;
        background: #4ade80;
        box-shadow: 0 0 10px rgba(74, 222, 128, 0.9);
    }

    .pill-dot-red {
        width: 7px;
        height: 7px;
        border-radius: 999px;
        background: #f97373;
        box-shadow: 0 0 10px rgba(248, 113, 113, 0.9);
    }
    """
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


# -------------------------------------------------------------------
# STATS
# -------------------------------------------------------------------
def compute_live_stats(trades_df: pd.DataFrame, initial_equity: float):
    """
    Compute equity, pnl, winrate, max drawdown, using return_pct / pnl_pct / pnl_usdt.
    """
    if trades_df.empty:
        return {
            "final_equity": initial_equity,
            "total_pnl_usdt": 0.0,
            "total_pnl_pct": 0.0,
            "num_trades": 0,
            "win_rate_pct": 0.0,
            "max_drawdown_pct": 0.0,
        }

    # Determine per-trade PnL in USDT
    if "pnl_usdt" in trades_df.columns:
        pnl_usdt = trades_df["pnl_usdt"].astype(float)

    elif "pnl_pct" in trades_df.columns:
        pnl_usdt = initial_equity * trades_df["pnl_pct"].astype(float) / 100.0

    elif "return_pct" in trades_df.columns:
        pnl_usdt = initial_equity * trades_df["return_pct"].astype(float) / 100.0

    else:
        pnl_usdt = pd.Series([0.0] * len(trades_df))

    # Equity curve
    equity_curve = initial_equity + pnl_usdt.cumsum()

    # Win rate
    if "pnl_usdt" in trades_df.columns:
        wins = (trades_df["pnl_usdt"].astype(float) > 0).sum()
    elif "pnl_pct" in trades_df.columns:
        wins = (trades_df["pnl_pct"].astype(float) > 0).sum()
    elif "return_pct" in trades_df.columns:
        wins = (trades_df["return_pct"].astype(float) > 0).sum()
    else:
        wins = 0

    num_trades = len(trades_df)
    win_rate_pct = (wins / num_trades) * 100 if num_trades > 0 else 0.0

    total_pnl_usdt = float(pnl_usdt.sum())
    final_equity = float(equity_curve.iloc[-1])
    total_pnl_pct = (final_equity / initial_equity - 1.0) * 100 if initial_equity > 0 else 0.0

    # Max drawdown
    roll_max = equity_curve.cummax()
    drawdown = (equity_curve - roll_max) / roll_max
    max_drawdown_pct = float(drawdown.min() * 100.0)

    return {
        "final_equity": final_equity,
        "total_pnl_usdt": total_pnl_usdt,
        "total_pnl_pct": total_pnl_pct,
        "num_trades": num_trades,
        "win_rate_pct": win_rate_pct,
        "max_drawdown_pct": max_drawdown_pct,
    }


# -------------------------------------------------------------------
# MAIN UI
# -------------------------------------------------------------------
def main():
    st.set_page_config(
        page_title="Smart Trading Bot – Live Monitor",
        page_icon="📈",
        layout="wide",
    )
    inject_global_css()

    # HEADER
    st.markdown('<div class="main-title">Smart Trading Bot</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="main-subtitle">Live performance monitor for ETH/USDT RSI V1 strategy.</div>',
        unsafe_allow_html=True,
    )

    # Load live trade log
    initial_equity = 10_000.0  # adjust if your bot started with a different testnet size
    if os.path.exists(TRADES_CSV_PATH):
        trades_df = pd.read_csv(TRADES_CSV_PATH)
    else:
        trades_df = pd.DataFrame()

    # Compute stats
    stats = compute_live_stats(trades_df, initial_equity=initial_equity)

    # Get equity snapshot from wallet (USDT + BTC/ETH holdings)
    snapshot = get_equity_snapshot(symbols=("BTCUSDT", "ETHUSDT"))
    live_equity = snapshot["equity_usdt"]
    pnl_vs_start = snapshot["pnl_pct"]

    # TOP KPI ROW
    kpi_cols = st.columns(5)
    with kpi_cols[0]:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">Initial Equity</div>
                <div class="kpi-value">${initial_equity:,.2f}</div>
                <div class="kpi-meta">Baseline (Day 0)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with kpi_cols[1]:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">Current Equity (Wallet)</div>
                <div class="kpi-value">{live_equity:,.2f} USDT</div>
                <div class="kpi-meta">Includes coins + USDT</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with kpi_cols[2]:
        pnl_color = "green" if stats["total_pnl_usdt"] >= 0 else "red"
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">Total PnL (from trade log)</div>
                <div class="kpi-value {pnl_color}">
                    {stats["total_pnl_usdt"]:,.2f} USDT
                </div>
                <div class="kpi-meta">{stats["total_pnl_pct"]:,.2f}% vs initial</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with kpi_cols[3]:
        win_color = "green" if stats["win_rate_pct"] >= 50 else "red"
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">Win Rate</div>
                <div class="kpi-value {win_color}">
                    {stats["win_rate_pct"]:,.2f}%
                </div>
                <div class="kpi-meta">{stats["num_trades"]} closed trades</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with kpi_cols[4]:
        dd_color = "green" if stats["max_drawdown_pct"] > -5 else "red"
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">Max Drawdown</div>
                <div class="kpi-value {dd_color}">
                    {stats["max_drawdown_pct"]:,.2f}%
                </div>
                <div class="kpi-meta">From equity peaks</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # BOT STATUS PILL
    col_status, col_spacer = st.columns([1, 3])
    with col_status:
        is_up = True  # we can't 100% know from this UI; assume up if trades are appearing
        dot_class = "pill-dot-green" if is_up else "pill-dot-red"
        status_text = "LIVE BOT ACTIVE" if is_up else "BOT OFFLINE"
        st.markdown(
            f"""
            <div class="pill">
                <div class="{dot_class}"></div>
                <span>{status_text}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

# -------------------------------------------------------------------
# LIVE PERFORMANCE CARDS
# -------------------------------------------------------------------
    st.markdown('<div class="section-title">Live Performance</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Based on closed trades only.</div>',unsafe_allow_html=True)

    p1, p2, p3, p4, p5, p6 = st.columns(6)
    cards = [
        ("Final Equity", f"{stats['final_equity']:,.2f}"),
        ("Total PnL", f"{stats['total_pnl_usdt']:,.2f} USDT"),
        ("PnL %", f"{stats['total_pnl_pct']:.2f}%"),
        ("Win Rate", f"{stats['win_rate_pct']:.2f}%"),
        ("Trades", str(stats["num_trades"])),
        ("Max Drawdown", f"{stats['max_drawdown_pct']:.2f}%"),
    ]

    for col, (label, value) in zip([p1, p2, p3, p4, p5, p6], cards):
        col.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# -------------------------------------------------------------------
# EQUITY CURVE
# -------------------------------------------------------------------
    st.markdown('<div class="section-title">Equity Curve</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subtitle">Cumulative equity from closed trades</div>',
        unsafe_allow_html=True,
    )

    if not trades_df.empty:
        pnl_pct = trades_df["return_pct"].astype(float)
        equity = initial_equity + (initial_equity * pnl_pct / 100).cumsum()
        st.line_chart(equity)
    else:
        st.info("No closed trades yet.")

# -------------------------------------------------------------------
# TRADE HISTORY
# -------------------------------------------------------------------
    st.markdown('<div class="section-title">Live Trade History</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subtitle">Most recent trades first. Pulled from logs/live_trades.csv.</div>',
        unsafe_allow_html=True,
    )

    if not trades_df.empty:
        df = trades_df.copy()

        # ---- format time + exit_reason BEFORE renaming ----
        if "time" in df.columns:
            df["Time"] = df["time"].apply(format_trade_time)
            df["time_parsed"] = pd.to_datetime(df["time"], errors="coerce")
        else:
            df["Time"] = ""

        if "exit_reason" in df.columns:
            df["Exit Reason"] = df["exit_reason"].apply(format_exit_reason)
        else:
            df["Exit Reason"] = ""

        # ---- rename the rest nicely ----
        df = df.rename(
            columns={
                "symbol": "Symbol",
                "side": "Side",
                "size": "Size",
                "entry_price": "Entry Price",
                "exit_price": "Exit Price",
                "return_pct": "Return (%)",
            }
        )

        # ---- sort newest first ----
        if "time_parsed" in df.columns:
            df = df.sort_values("time_parsed", ascending=False).drop(columns=["time_parsed"])
        else:
            df = df.iloc[::-1]

        # ---- show only clean columns (no raw snake_case) ----
        wanted_cols = [
            "Time",
            "Symbol",
            "Side",
            "Size",
            "Entry Price",
            "Exit Price",
            "Return (%)",
            "Exit Reason",
        ]
        wanted_cols = [c for c in wanted_cols if c in df.columns]

        st.dataframe(df[wanted_cols], use_container_width=True, hide_index=True)

    else:
        st.info("No live trades logged yet.")


if __name__ == "__main__":
    main()
