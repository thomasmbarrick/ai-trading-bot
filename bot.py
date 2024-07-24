from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader
from datetime import datetime 
from alpaca_trade_api import REST 
from timedelta import Timedelta 
from ai import estimate_sentiment
import numpy as np
import yfinance as yf


API_KEY = "PKE2VBNLWVIB2MEPHAMI"
API_SECRET = "yBbvQY9rar69pQjeamfFiJtikPbgyk1A0lKytL6K"
BASE_URL = "https://paper-api.alpaca.markets/v2"

ALPACA_CREDS = {
    "API_KEY":API_KEY, 
    "API_SECRET": API_SECRET, 
    "PAPER": True 
}


class MLTrader(Strategy):
    
    """Initialises the class with the given parameters"""
    def initialize(self, symbol:str="NVDA", cash_at_risk:float=.5): 
        self.symbol = symbol
        self.sleeptime = "12H" 
        self.last_trade = None 
        self.cash_at_risk = cash_at_risk
        self.api = REST(base_url=BASE_URL, key_id=API_KEY, secret_key=API_SECRET)

    
    """Basic position sizing algoirthm"""
    def position_sizing(self):
        cash = self.get_cash()
        last_price = self.get_last_price(self.symbol)
        quantity = round(cash * self.cash_at_risk / last_price)
        return cash, last_price, quantity
    
    """position sizing algoirthm that allocates a fixed percentage of their trading account to each trade. """
    def fixed_fractional_sizing(self, risk_percentage=0.02):
        cash = self.get_cash()
        last_price = self.get_last_price(self.symbol)
        stop_loss_price = last_price * 0.95
        risk_per_share = last_price - stop_loss_price
        risk_amount = cash * risk_percentage
        quantity = round(risk_amount / risk_per_share)
        return cash, last_price, quantity

    """position sizing algoirthm that allocates a fixed percentage of their trading account to each trade. """
    def equal_dollar_sizing(self, dollar_amount=10000):
        last_price = self.get_last_price(self.symbol)
        quantity = round(dollar_amount / last_price)
        return self.get_cash(), last_price, quantity

    """Uses datetime library to recieve the time of which the sentiment of stocks is measured"""
    def get_sentiment_window_dates(self): 
        today = self.get_datetime()
        three_days_prior = today - Timedelta(days=5)
        return today.strftime('%Y-%m-%d'), three_days_prior.strftime('%Y-%m-%d')

    """Uses the estimate_sentiment method to """
    def get_sentiment(self): 
        today, sentiment_window_start = self.get_sentiment_window_dates()
        news = self.api.get_news(symbol=self.symbol, 
                                 start=sentiment_window_start, 
                                 end=today) 
        news = [ev.__dict__["_raw"]["headline"] for ev in news]
        probability, sentiment = estimate_sentiment(news)
        return probability, sentiment 

    """The trading logic which is executed on each change"""
    def on_trading_iteration(self):
        cash, last_price, quantity = self.position_sizing() 
        probability, sentiment = self.get_sentiment()
        if cash > last_price: # Ensures that you have more available cash than the last price of the stock 
            if sentiment == "positive" and probability > .999: 
                if self.last_trade == "sell": 
                    self.sell_all() 
                order = self.create_order(
                    self.symbol, 
                    quantity, 
                    "buy", 
                    type="bracket", 
                    take_profit_price=last_price*1.20, 
                    stop_loss_price=last_price*.95
                )
                self.submit_order(order) 
                self.last_trade = "buy"
            elif sentiment == "negative" and probability > .999: 
                if self.last_trade == "buy": 
                    self.sell_all() 
                order = self.create_order(
                    self.symbol, 
                    quantity, 
                    "sell", 
                    type="bracket", 
                    take_profit_price=last_price*.8, 
                    stop_loss_price=last_price*1.05
                )
                self.submit_order(order) 
                self.last_trade = "sell"

start_date = datetime(2020,1,1)
end_date = datetime(2023,12,31) 
broker = Alpaca(ALPACA_CREDS) 
strategy = MLTrader(name='mlstrat', broker=broker, 
                    parameters={"symbol":"NVDA", 
                                "cash_at_risk":.5})
strategy.backtest(
    YahooDataBacktesting, 
    start_date, 
    end_date, 
    parameters={"symbol":"NVDA", "cash_at_risk":.5}
)
