from src.config import get_binance_client, TRADING_ENV

def main():
    client = get_binance_client()
    print("TRADING_ENV:", TRADING_ENV)

    # Fetch basic account info (no trading)
    info = client.get_account()
    print("Can access account. First 3 balances:")
    for bal in info['balances'][:3]:
        print(bal)

    # Fetch a live price to be sure we can connect
    ticker = client.get_symbol_ticker(symbol="ETHUSDT")
    print("ETHUSDT price:", ticker)

if __name__ == "__main__":
    main()