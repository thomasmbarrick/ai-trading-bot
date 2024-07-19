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
    
    def initialize(self, symbol: str = "NVDA"):
        self.symbol = symbol
        self.sleeptime = "24H"
        self.last_trade = None

    def on_trading_iteration(self):
        if self.last_trade is None:
            order = self.create_order(
                self.symbol,
                10,
                "buy",
                type="market"
            )
            self.submit_order(order)
            self.last_trade = "buy"

broker = Alpaca(ALPACA_CREDS)
strat = MLStrategy(name="mlstrat", broker=broker, parameters={"symbol": "NVDA"})
start_date = dt(2020, 12, 15)
end_date = dt(2022, 12, 15)

strat.backtest(
    YahooDataBacktesting,
    start_date,
    end_date,
    parameters={}
)
