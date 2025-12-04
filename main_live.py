# main_live.py
import time

from src.config import TRADING_ENV
from src.live_trader import live_step_rsi_v1
from src.runtime_state import load_state

POLL_SECONDS = 60  # how often to trade/check


def main():
    print("=== Smart Trading Bot — Live Daemon (DEMO / TESTNET) ===")
    print(f"TRADING_ENV: {TRADING_ENV}")
    if TRADING_ENV != "testnet":
        raise RuntimeError("For demo running, TRADING_ENV must be 'testnet' in config/.env")

    state = None  # internal bot position state

    while True:
        try:
            rs = load_state()

            if not rs["bot_enabled"]:
                print("[INFO] Bot is currently DISABLED (set via dashboard). Sleeping...")
            else:
                print(f"[INFO] Bot ENABLED for {rs['symbol']} ({rs['interval']})")
                state, logs, completed_trades = live_step_rsi_v1(
                    state,
                    symbol=rs["symbol"],
                    interval=rs["interval"],
                    history_candles=rs["history_candles"],
                    position_size_usdt=rs["position_size_usdt"],
                    entry_rsi=rs["entry_rsi"],
                    exit_rsi=rs["exit_rsi"],
                    take_profit_pct=rs["take_profit_pct"],
                )

                for line in logs:
                    print(line)

                if completed_trades:
                    print(f"[TRADES] Closed {len(completed_trades)} trade(s) this step.")

        except Exception as e:
            print("[ERROR] Exception in main loop:", e)

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
