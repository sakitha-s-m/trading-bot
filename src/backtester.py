import signal
from tracemalloc import start
from numpy import sign
import pandas as pd
from indicators import calculate_indicators
from strategy import generate_signal

class Backtester:
    def __init__(self, data, starting_balance=1000, leverage=1, fee=0.0004, stop_1oss=0.02, take_profit=0.04):
        self.data = data.copy()
        self.balance = starting_balance
        self.initial_balance = starting_balance

        self.position = None
        self.entry_price = None
        self.leverage = leverage
        self.fee = fee
        self.stop_loss = stop_1oss
        self.take_profit = take_profit

        self.equity_curve = []

    def open_position(self, signal, price):
        self.position = signal
        self.entry_price = price

        self.balance -= self.balance * self.fee

    def close_position(self, price):
        if self.position == "LONG":
            pnl = (price - self.entry_price) / self.entry_price
        elif self.position == "SHORT":
            pnl = (self.entry_price - price) / self.entry_price
        
        pnl *= self.leverage
        profit = self.balance * pnl

        # Apply exit fees
        profit -= abs(profit) * self.fee

        self.balance += profit
        self.position = None
        self.entry_price = None

    def run(self):
        self.data = calculate_indicators(self.data)

        for _, row in self.data.iterrows():
            price = row["close"]
            signal = generate_signal(row)

            # If no open trade, open one
            if self.position is None:
                if signal in ["LONG", "SHORT"]:
                    self.open_position(signal, price)
            
            else:
                # Stop loss / Take profit check
                change = (price - self.entry_price) / self.entry_price
                change *= self.leverage

                if self.position == "SHORT":
                    change *= -1 # Invert for short

                if change <= -self.stop_loss or change >= self.take_profit:
                    self.close_position(price)
                    continue

                # Exit signal
                if signal == "EXIT":
                    self.close_position(price)

            self.equity_curve.append(self.balance)

        
        return {
            "final_balance": round(self.balance, 2),
            "return_pct": round(((self.balance - self.initial_balance) / self.initial_balance) * 100, 2),
            "equity_curve": self.equity_curve
        }