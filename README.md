# Smart Trading Bot

An automated cryptocurrency trading bot built on the Binance API. Implements multiple technical analysis strategies, a vectorised backtester, live order execution, and a real-time Streamlit dashboard.

Built as a personal project to learn algorithmic trading, API integration, and quantitative finance concepts.

---

## Features

- **Live trading daemon** — polls Binance every 60 seconds and executes market orders automatically
- **Multiple strategies** — SMA crossover, RSI reversal, RSI + trend filter, and a tuned RSI V1 strategy
- **Vectorised backtester** — simulates strategies on historical OHLCV data with fees, stop-loss, and take-profit
- **Streamlit dashboard** — real-time PnL, equity curve, win rate, max drawdown, and trade history
- **Testnet / live switching** — full environment separation with a hard safety gate before any live order
- **Binance LOT_SIZE compliance** — auto-adjusts order quantities to satisfy exchange filters
- **Persistent runtime config** — bot parameters (symbol, RSI levels, position size) editable at runtime without restarting

---

## Architecture

```
Trading_Bot/
├── main_live.py          # Live trading daemon (60s poll loop)
├── main_backtest.py      # Backtesting entry point
├── dashboard/
│   └── app_pretty.py    # Streamlit monitoring dashboard
├── src/
│   ├── config.py        # Binance client factory, testnet/live switching, safety gate
│   ├── data.py          # Historical OHLCV data fetching
│   ├── indicators.py    # SMA and RSI calculations
│   ├── strategy.py      # Strategy dispatcher (4 strategies)
│   ├── backtester.py    # Event-driven backtester with fees, SL/TP, equity curve
│   ├── live_trader.py   # Order placement, position management, trade logging
│   ├── runtime_state.py # Thread-safe JSON state persistence
│   └── wallet.py        # Live wallet equity snapshot
├── config/
│   └── .env             # API keys and environment config (not committed)
└── logs/
    └── live_trades.csv  # Trade log (auto-created)
```

---

## Strategies

| Strategy | Entry | Exit |
|---|---|---|
| SMA Crossover | Fast MA crosses above slow MA | Fast MA crosses below slow MA |
| RSI Reversal | RSI < 30 (oversold) | RSI > 70 (overbought) |
| RSI + Trend Filter | RSI < 30 AND price above SMA(20) | RSI > 60 OR price below SMA(20) |
| **RSI V1** (active) | RSI < 25 | RSI > 80 or +4% take-profit |

The active live strategy is **RSI V1** running on ETH/USDT 15-minute candles.

---

## Setup

### Prerequisites

- Python 3.11+
- Binance account (testnet or live)

### Installation

```bash
git clone https://github.com/sakitha-s-m/Trading_Bot.git
cd Trading_Bot
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration

Create `config/.env`:

```env
# Testnet (safe for development)
TRADING_ENV=testnet
BINANCE_TESTNET_API_KEY=your_testnet_api_key
BINANCE_TESTNET_API_SECRET=your_testnet_api_secret

# Live (requires confirmation flag)
# TRADING_ENV=live
# BINANCE_LIVE_API_KEY=your_live_api_key
# BINANCE_LIVE_API_SECRET=your_live_api_secret
# LIVE_TRADING_CONFIRMATION=YES_I_UNDERSTAND_THE_RISK
```

---

## Usage

### Run the live trading daemon

```bash
python main_live.py
```

### Run a backtest

```bash
python main_backtest.py
```

### Launch the dashboard

```bash
streamlit run dashboard/app_pretty.py
```

---

## Dashboard

The Streamlit dashboard provides a live view of:

- Current wallet equity vs initial equity
- Total PnL (USDT and %)
- Win rate and trade count
- Max drawdown
- Equity curve chart
- Full trade history table (most recent first)

---

## Safety

Live trading is blocked by default. To enable it, two conditions must both be true in `config/.env`:

1. `TRADING_ENV=live`
2. `LIVE_TRADING_CONFIRMATION=YES_I_UNDERSTAND_THE_RISK`

All orders are validated against Binance's LOT_SIZE filter before placement. If the adjusted quantity falls below the minimum, the order is skipped rather than failing at the exchange.

---

## Tech Stack

- **Python 3.11**
- **python-binance** — Binance REST API client
- **pandas** — data manipulation and indicator calculation
- **Streamlit** — dashboard UI
- **python-dotenv** — environment config

---

## What I Learned

- Connecting to and working with a financial exchange API in a production-like setup
- The gap between backtested and live performance (slippage, fees, look-ahead bias)
- Importance of out-of-sample validation before deploying any strategy
- Thread-safe state management for a long-running daemon process
- Building end-to-end: data pipeline → signal generation → execution → monitoring

---

## Roadmap

- Walk-forward backtesting to reduce overfitting
- Proper Sharpe ratio and risk-adjusted return metrics
- Stop-loss implementation
- Multi-symbol support
- Telegram/email trade notifications
