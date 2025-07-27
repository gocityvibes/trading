class RiskManager:
    def __init__(self):
        self.max_open_trades = 3
        self.open_trades = []

    def can_open_new_trade(self):
        return len(self.open_trades) < self.max_open_trades

    def register_trade(self, symbol):
        self.open_trades.append(symbol)

    def close_trade(self, symbol):
        if symbol in self.open_trades:
            self.open_trades.remove(symbol)

    def get_trade_size(self):
        return 500  # Fixed trade size in dollars

    def get_risk_limits(self):
        return {
            'stop_loss_pct': -5,
            'take_profit_pct': 10,
            'trailing_stop': False  # Optional: set to True if needed
        }