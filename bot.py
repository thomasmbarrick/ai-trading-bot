from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader
from datetime import datetime as dt 

API_KEY = "PKE2VBNLWVIB2MEPHAMI"
API_SECRET = "yBbvQY9rar69pQjeamfFiJtikPbgyk1A0lKytL6K"
BASE_URL = "https://paper-api.alpaca.markets/v2"

ALPACA_CREDS = {
    "API_KEY": API_KEY,
    "API_SECRET": API_SECRET,
    "PAPER": True
}

class MLStrategy(Strategy):
    
    def initialize(self, symbol: str = "SPY", cash_at_risk:float=0.5):
        self.symbol = symbol
        self.sleeptime = "24H"
        self.last_trade = None
        self.cash_at_risk = cash_at_risk

    def position_sizing(self):
        cash = self.get_cash()
        last_price = self.get_last_price(self.symbol)
        quantity = cash * self.cash_at_risk / last_price
        return cash, last_price, quantity
        
        
    def on_trading_iteration(self):
        cash, last_price, quantity = self.position_sizing()
        if cash > last_price:
            if self.last_trade is None:
                order = self.create_order(
                    self.symbol,
                    quantity,
                    "buy",
                    type="bracket",
                    take_profit_price = last_price*1.2,
                    stop_loss_price=last_price*0.95
                )
                self.submit_order(order)
                self.last_trade = "buy"

broker = Alpaca(ALPACA_CREDS)
strat = MLStrategy(name="mlstrat", broker=broker, parameters={"symbol": "SPY",
                                                              "cash_at_risk":0.5})
start_date = dt(2020, 12, 15)
end_date = dt(2022, 12, 15)

strat.backtest(
    YahooDataBacktesting,
    start_date,
    end_date,
    parameters={"symbol": "SPY",
                "cash_at_risk":0.5}
)
