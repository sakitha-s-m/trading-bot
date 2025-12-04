# main_live.py
import time

from src.config import TRADING_ENV
from src.live_trader import live_step_rsi_v1


def main():
    print("=== Smart Trading Bot — Live Daemon (DEMO / TESTNET) ===")
    print(f"TRADING_ENV: {TRADING_ENV}")
    if TRADING_ENV != "testnet":
        raise RuntimeError("For demo running, TRADING_ENV must be 'testnet' in config/.env")

    # Internal bot state (position, entry price, etc.)
    state = None

    # V1 recommended defaults
    symbol = "ETHUSDT"
    interval = "15m"
    history_candles = 200
    position_size_usdt = 100.0      # testnet demo size
    entry_rsi = 25.0
    exit_rsi = 80.0
    take_profit_pct = 0.04          # 4% TP
    poll_seconds = 60               # run once per minute

    print(f"Running RSI Strategy V1 on {symbol} ({interval}), position size ≈ {position_size_usdt} USDT per trade")
    print(f"Entry RSI < {entry_rsi}, Exit RSI > {exit_rsi}, TP = {take_profit_pct * 100:.1f}%")
    print(f"Polling every {poll_seconds} seconds...\n")

    while True:
        try:
            state, logs, completed_trades = live_step_rsi_v1(
                state,
                symbol=symbol,
                interval=interval,
                history_candles=history_candles,
                position_size_usdt=position_size_usdt,
                entry_rsi=entry_rsi,
                exit_rsi=exit_rsi,
                take_profit_pct=take_profit_pct,
            )

            # Print logs for this step
            for line in logs:
                print(line)

            # Completed trades are already appended to CSV inside live_step_rsi_v1,
            # but you could also inspect them here if you want.
            if completed_trades:
                print(f"[TRADES] Closed {len(completed_trades)} trade(s) this step.")

        except Exception as e:
            print("[ERROR] Exception in main loop:", e)

        time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
