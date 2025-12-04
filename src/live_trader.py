from http import client
import time
from typing import Literal
import math
import os
import csv
from datetime import datetime

from binance.exceptions import BinanceAPIException
from numpy import sign

from .config import get_binance_client, TRADING_ENV, ensure_live_trading_allowed
from .data import get_historical_klines
from .indicators import add_indicators
from .strategy import generate_signals

LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
TRADES_CSV_PATH = os.path.join(LOGS_DIR, "live_trades.csv")

def append_trade_to_csv(trade: dict, path: str = TRADES_CSV_PATH):
    """
    Append a single trade dict to CSV file. Creates header if file doesn't exit.
    """
    fieldnames = [
        "time",
        "symbol",
        "side",
        "size",
        "entry_price",
        "exit_price",
        "return_pct",
        "exit_reason"
    ]

    file_exists = os.path.exists(path)

    with open(path, mode="a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(trade)

Side = Literal["BUY", "SELL"]

def _format_quantity_for_symbol(client, symbol: str, quantity: float) -> float:
    """
    Adjust raw quantity to satisfy Binance LOT_SIZE filter for this symbol.
    Floors to nearest valid step size and enforces minQty.
    """
    info = client.get_symbol_info(symbol)
    if not info:
        return quantity # fallback, shouldn't happen often
    
    lot_filter = None
    for f in info["filters"]:
        if f["filterType"] == "LOT_SIZE":
            lot_filter = f
            break
    
    if lot_filter is None:
        return quantity
    
    min_qty = float(lot_filter["minQty"])
    max_qty = float(lot_filter["maxQty"])
    step_size = float(lot_filter["stepSize"])

    # clamp to [min_qty, max_qty]
    qty = max(min_qty, min(quantity, max_qty))

    # floor to step size
    if step_size > 0:
        steps = math.floor(qty / step_size)
        qty = steps * step_size
    
    # prevent negative / zero issues
    if qty < min_qty:
        return 0.0
    
    # round to a reasonable number of decimals based on step_size
    decimals = max(0, -int(math.log10(step_size))) if step_size < 1 else 0
    return round(qty, decimals)

def place_market_order(symbol: str, side: Side, quantity: float):
    """
    Place a market order on Binance.

        - Uses testnet or live based on TRADING_ENV
        - For live, requires LIVE_TRADING_CONFIRMATION to be set in .env
        - Auto-adjusts quantity to satisfy Binance LOT_SIZE filter
    """
    
    # Safety gate for live trading
    ensure_live_trading_allowed()

    client = get_binance_client()

    # Normalize quantity for this symbol (LOT_SIZE)
    qty = _format_quantity_for_symbol(client, symbol, quantity)

    if qty <= 0:
        print(f"[WARN] After LOT_SIZE adjustment, quantity <= 0 for {symbol}. Skipping order.")
        return None
    
    env_label = "TESTNET" if TRADING_ENV == "testnet" else "LIVE"
    try:
        print(f"[ORDER] ENV={env_label} {side} {qty} {symbol}")
        order = client.order_market(
            symbol=symbol,
            side=side,
            quantity=qty
        )
        print("[ORDER RESULT]", order)
        return order
    except BinanceAPIException as e:
        print(f"[ERROR] Order failed: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Unexpected error placing order: {e}")
        return None

def live_step_rsi_v1(
    state: dict | None,
    symbol: str = "ETHUSDT",
    interval: str = "15m",
    history_candles: int = 200,
    position_size_usdt: float = 100.0,
    entry_rsi: float = 25.0,
    exit_rsi: float = 80.0,
    take_profit_pct: float = 0.04,
) -> tuple[dict, list[str], list[dict]]:
    """
    Run ONE live trading step of RSI Strategy V1.

    Returns:
      - updated state dict
      - list of log strings describing what happened
      - list of completed trades (if any), each as a dict

    This is designed for Streamlit: you call it on button click,
    and store the 'state' in st.session_state.
    """
    if TRADING_ENV != "testnet":
        raise RuntimeError("TRADING_ENV must be 'testnet' for live_step_rsi_v1 (safety).")

    client = get_binance_client()

    # Initialize state if first run
    if state is None:
        state = {
            "in_position": False,
            "entry_price": None,
            "position_size": 0.0,
        }
    
    logs: list[str] = []
    completed_trades: list[dict] = []


    # 1) Fetch latest candles + indicators + signals
    df = get_historical_klines(symbol=symbol, interval=interval, limit=history_candles)
    df = add_indicators(df)
    df = generate_signals(
        df,
        strategy="rsi_v1",
        entry_rsi=entry_rsi,
        exit_rsi=exit_rsi,
    )

    latest = df.iloc[-1]
    price = latest["close"]
    rsi = latest["RSI"]
    signal = latest["signal"]

    logs.append(
        f"[{symbol}] Price: {price:.2f} | RSI: {rsi:.2f} | signal: {signal} | in_position: {state['in_position']}"
    )

    # 2) If in position, check TP or exit
    if state["in_position"]:
        entry_price = state["entry_price"]
        tp_level = entry_price * (1 + take_profit_pct)

        # Take-profit
        # Take-profit
        if price >= tp_level:
            logs.append(f"[TP] Price {price:.2f} >= TP {tp_level:.2f}, closing position.")
            order = place_market_order(symbol, "SELL", state["position_size"])
            if order is not None:
                # compute trade stats
                ret_pct = (price - entry_price) / entry_price * 100
                trade = {
                    "time": datetime.utcnow().isoformat(),
                    "symbol": symbol,
                    "side": "LONG",
                    "size": state["position_size"],
                    "entry_price": entry_price,
                    "exit_price": price,
                    "return_pct": ret_pct,
                    "exit_reason": "take_profit",
                }
                completed_trades.append(trade)
                append_trade_to_csv(trade)

                state["in_position"] = False
                state["entry_price"] = None
                state["position_size"] = 0.0
                logs.append("[TP] SELL order filled.")
            else:
                logs.append("[TP] SELL order failed, staying in position.")

        # Signal-based exit
        elif signal == -1:
            logs.append(f"[EXIT] RSI exit signal triggered at {price:.2f}.")
            order = place_market_order(symbol, "SELL", state["position_size"])
            if order is not None:
                ret_pct = (price - entry_price) / entry_price * 100
                trade = {
                    "time": datetime.utcnow().isoformat(),
                    "symbol": symbol,
                    "side": "LONG",
                    "size": state["position_size"],
                    "entry_price": entry_price,
                    "exit_price": price,
                    "return_pct": ret_pct,
                    "exit_reason": "signal",
                }
                completed_trades.append(trade)
                append_trade_to_csv(trade)

                state["in_position"] = False
                state["entry_price"] = None
                state["position_size"] = 0.0
                logs.append("[EXIT] SELL order filled.")
            else:
                logs.append("[EXIT] SELL order failed, staying in position.")


    # 3) If NOT in position, check for entry
    else:
        if signal == 1:
            qty = position_size_usdt / price
            logs.append(
                f"[ENTRY] Entry signal detected. Buying approx {qty:.6f} {symbol.split('USDT')[0]} at {price:.2f}."
            )
            order = place_market_order(symbol, "BUY", qty)
            if order is not None:
                state["in_position"] = True
                state["entry_price"] = price
                # NOTE: we don't know the exact filled qty from here; for now we assume requested qty
                state["position_size"] = qty
                logs.append("[ENTRY] BUY order filled.")
            else:
                logs.append("[ENTRY FAILED] Staying flat (no position opened).")

    return state, logs, completed_trades

def live_loop_rsi_v1(
    symbol: str = "BTCUSDT",
    interval: str = "15m",
    history_candles: int = 200,
    position_size_usdt: float = 100.0,
    entry_rsi: float = 25.0,
    exit_rsi: float = 80.0,
    take_profit_pct: float = 0.04,
    poll_seconds: int = 60,
):
    """
    Live trading loop for RSI Strategy V1 on TESTNET.

    Logic:
      - Use rsi_v1: entry when RSI < entry_rsi, exit when RSI > exit_rsi
      - No stop-loss
      - Take-profit at entry_price * (1 + take_profit_pct)
      - Single position per symbol, all-in with 'position_size_usdt' each trade
    """

    if TRADING_ENV != "testnet":
        raise RuntimeError("TRADING_ENV must be 'testnet' for live_loop_rsi_v1. Refusing to trade live.")
    
    client = get_binance_client()

    state = {
        "in_position": False,
        "entry_position": None,
        "position_size": 0.0, # in base asset
    }

    print(f"=== Starting RSI Strategy V1 live loop on {symbol} ({interval}) in {TRADING_ENV} mode ===")
    print(f"Entry RSI < {entry_rsi} | Exit RSI > {exit_rsi} | TP: {take_profit_pct * 100:.2f}%")
    print(f"Per-trade size: {position_size_usdt} USDT")
    print("Press Ctrl+C to stop.\n")

    while True:
        try:
            # 1) Fetch lastest candles
            df = get_historical_klines(symbol=symbol, interval=interval, limit=history_candles)
            df = add_indicators(df)
            df = generate_signals(
                df,
                strategy="rsi_v1",
                entry_rsi=entry_rsi,
                exit_rsi=exit_rsi,
            )

            latest = df.iloc[-1]
            price = latest["close"]
            rsi = latest["RSI"]
            signal = latest["signal"]

            print(f"[{symbol}] Price: {price:.2f} | RSI: {rsi:.2f} | signal: {signal} | in_position: {state['in_position']}")

            # 2) If in position, check take profit or exit signal
            if state["in_position"]:
                entry_price = state["entry_price"]
                tp_level = entry_price * (1 + take_profit_pct)

                # Take-profit check
                if price >= tp_level:
                    print(f"[TP] Price {price:.2f} >= TP level {tp_level:.2f}, closing position.")
                    place_market_order(symbol, "SELL", state["position_size"])
                    state["in_position"] = False
                    state["entry_price"] = None
                    state["position_size"] = 0.0
                
                # Signal-based exit
                elif signal == -1:
                    print(f"[EXIT] RSI exit signal triggered at price {price:.2f}.")
                    place_market_order(symbol, "SELL", state["position_size"])
                    state["in_position"] = False
                    state["entry_price"] = None
                    state["position_size"] = 0.0
            
            # 3) If NOT in position, check for entry
            else:
                if signal == 1:
                    # Calculate position size in base asset
                    qty = position_size_usdt / price
                    print(f"[ENTRY] Entry signal detected. Buying approx {qty:.6f} {symbol.split('USDT')[0]} at {price:.2f}.")
                    order = place_market_order(symbol, "BUY", qty)

                    if order is not None:
                        # Only mark in-position if order succeeded
                        state["in_position"] = True
                        state["entry_price"] = price
                        state["position_size"] = qty
                    else:
                        print("[ENTRY FAILED] Staying flat (no position opened.)")
                        state["in_position"] = False
                        state["entry_price"] = None
                        state["position_size"] = 0.0
                
            # 4) Sleep until next poll
            time.sleep(poll_seconds)

        except KeyboardInterrupt:
            print("\n[STOP] KeyboardInterrupt received. Exiting live loop.")
            break
        except Exception as e:
            print(f"[ERROR] Unexpected error in live loop: {e}")
            time.sleep(poll_seconds)