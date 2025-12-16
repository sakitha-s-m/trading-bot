import json 
import os
import threading

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_PATH = os.path.join(BASE_DIR, "config", "runtime_state.json")

_lock = threading.Lock()

DEFAULT_STATE = {
    "bot_enabled": False,
    "symbol": "ETHUSDT",
    "interval": "15m",
    "history_candles": 200,
    "position_size_usdt": 100.0,
    "entry_rsi": 25.0,
    "exit_rsi": 80.0,
    "take_profit_pct": 0.04,  # 4%
    "initial_equity_usdt": 10_000.0,
}

def load_state() -> dict:
    """Load runtime state from file, creating if needed."""
    with _lock:
        if not os.path.exists(STATE_PATH):
            return DEFAULT_STATE.copy()
        try:
            with open(STATE_PATH, "r") as f:
                data = json.load(f)
            merged = DEFAULT_STATE.copy()
            merged.update(data)
            return merged
        except Exception:
            return DEFAULT_STATE.copy()

def save_state(state: dict):
    """Save runtime state to file."""
    with _lock:
        os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
        with open(STATE_PATH, "w") as f:
            json.dump(state, f, indent=2)

def set_bot_enabled(enabled: bool):
    state = load_state()
    state["bot_enabled"] = enabled
    save_state(state)

def update_config_from_dashboard(
    symbol: str,
    interval: str,
    history_candles: int,
    position_size_usdt: float,
    entry_rsi: float,
    exit_rsi: float,
    take_profit_pct: float,
    initial_equity_usdt: float,
    bot_enabled: bool | None = None,
):
    state = load_state()
    state["symbol"] = symbol
    state["interval"] = interval
    state["history_candles"] = int(history_candles)
    state["position_size_usdt"] = float(position_size_usdt)
    state["entry_rsi"] = float(entry_rsi)
    state["exit_rsi"] = float(exit_rsi)
    state["take_profit_pct"] = float(take_profit_pct)
    state["initial_equity_usdt"] = float(initial_equity_usdt)
    if bot_enabled is not None:
        state["bot_enabled"] = bool(bot_enabled)
    save_state(state)
