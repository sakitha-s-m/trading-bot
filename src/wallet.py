from __future__ import annotations

import os
from typing import Iterable

from .config import TRADING_ENV, get_binance_client
from .data import get_historical_klines

def get_testnet_balances(assets: Iterable[str] = ("USDT", "BTC", "ETH")) -> dict[str, float]:
    """
    Return free balances for the given assets on TESTNET (or live, if TRADING_ENV is changed.)
    """
    client = get_binance_client()
    account = client.get_account()

    balances = {asset: 0.0 for asset in assets}
    for bal in account["balances"]:
        asset = bal["asset"]
        if asset in balances:
            balances[asset] = float(bal["free"])
    return balances

def get_latest_price(symbol: str) -> float:
    """
    Get the latest close price for a symbol from klines.
    """
    df = get_historical_klines(symbol=symbol, interval="15m", limit=1)
    return float(df["close"].iloc[-1])

def get_equity_snapshot(
    symbols: Iterable[str] = ("BTCUSDT", "ETHUSDT"),
    base_asset: str = "USDT",
    default_start_equity: float = 10_000.0,
) -> dict:
    """
    Compute a simple equity snapshot:
        - balances (USDT, BTC, ETH)
        - current  prices for BTCUSDT / ETHUSDT
        - total equity in USDT
        - PnL % vs a notional starting equity (default 10,000 USDT)
    """
    balances = get_testnet_balances(assets=(base_asset, "BTC", "ETH"))

    prices = {}
    for sym in symbols:
        prices[sym] = get_latest_price(sym)

    # Covert holding to USDT
    usdt = balances.get(base_asset, 0.0)
    btc = balances.get("BTC", 0.0)
    eth = balances.get("ETH", 0.0)

    btc_price = prices.get("BTCUSDT", 0.0)
    eth_price = prices.get("ETHUSDT", 0.0)

    equity_usdt = usdt + btc * btc_price + eth * eth_price

    # For V1 we just compare vs a fixed starting equity
    start_equity = default_start_equity
    pnl_pct = (equity_usdt - start_equity) / start_equity * 100 if start_equity > 0 else 0.0

    return {
        "balances": balances,
        "prices": prices,
        "equity_usdt": equity_usdt,
        "pnl_pct": pnl_pct,
        "base_asset": base_asset,
        "start_equity": start_equity,
    }


