from src.config import get_binance_client, TRADING_ENV

client = get_binance_client()

print("TRADING_ENV:", TRADING_ENV)

# 1) Ping (connectivity)
print("ping:", client.ping())

# 2) Latest price
ticker = client.get_symbol_ticker(symbol="ETHUSDT")
print("ETHUSDT price:", ticker)

# 3) Account endpoint (requires USER_DATA permission)
info = client.get_account()
print("Can read account. Balances count:", len(info.get("balances", [])))
