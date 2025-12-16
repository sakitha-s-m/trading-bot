# check_balance.py
import os
from binance.client import Client
from src.config import get_binance_client, TRADING_ENV

def main():
    client = get_binance_client()

    print("TRADING_ENV:", TRADING_ENV)

    account = client.get_account()
    balances = account["balances"]

    usdt = next(b for b in balances if b["asset"] == "USDT")
    eth = next(b for b in balances if b["asset"] == "ETH")

    usdt_free = float(usdt["free"])
    eth_free = float(eth["free"])

    price = float(client.get_symbol_ticker(symbol="ETHUSDT")["price"])

    equity = usdt_free + eth_free * price

    print(f"USDT balance: {usdt_free:.2f}")
    print(f"ETH balance: {eth_free:.6f}")
    print(f"ETH price: {price:.2f}")
    print(f"Total equity (USDT): {equity:.2f}")

if __name__ == "__main__":
    main()
