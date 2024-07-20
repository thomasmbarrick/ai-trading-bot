from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader
from datetime import datetime 
from alpaca_trade_api import REST 
from timedelta import Timedelta 
from finbert_utils import estimate_sentiment

API_KEY = "PKE2VBNLWVIB2MEPHAMI"
API_SECRET = "yBbvQY9rar69pQjeamfFiJtikPbgyk1A0lKytL6K"
BASE_URL = "https://paper-api.alpaca.markets/v2"

ALPACA_CREDS = {
    "API_KEY":API_KEY, 
    "API_SECRET": API_SECRET, 
    "PAPER": True
}


class MLTrader(Strategy):
    def initialize(self, symbol:str="NVDA", cash_at_risk:float=.5): 
        self.symbol = symbol
        self.sleeptime = "12H" 
        self.last_trade = None 
        self.cash_at_risk = cash_at_risk
        self.api = REST(base_url=BASE_URL, key_id=API_KEY, secret_key=API_SECRET)
    
    def fixed_fractional_position_sizing(self):
        cash = self.get_cash()
        risk_per_trade = cash * self.cash_at_risk
        last_price = self.get_last_price(self.symbol)
        quantity = round(risk_per_trade / last_price, 0)
        return cash, last_price, quantity
    
    def fixed_dollar_position_sizing(self):
        fixed_amount = 1000  
        last_price = self.get_last_price(self.symbol)
        quantity = round(fixed_amount / last_price, 0)
        cash = self.get_cash()
        return cash, last_price, quantity

    
    def volatility_based_position_sizing(self):
        cash = self.get_cash()
        atr = self.get_atr(self.symbol) 
        risk_per_trade = cash * self.cash_at_risk
        last_price = self.get_last_price(self.symbol)
        quantity = round(risk_per_trade / atr, 0)
        return cash, last_price, quantity

    def volatility_based_position_sizing(self):
        cash = self.get_cash()
        atr = self.get_atr(self.symbol)  
        risk_per_trade = cash * self.cash_at_risk
        last_price = self.get_last_price(self.symbol)
        quantity = round(risk_per_trade / atr, 0)
        return cash, last_price, quantity
    
    def kelly_criterion_position_sizing(self):
        win_probability = self.get_win_probability(self.symbol)
        win_loss_ratio = self.get_win_loss_ratio(self.symbol) 
        kelly_fraction = win_probability - (1 - win_probability) / win_loss_ratio
        cash = self.get_cash()
        risk_per_trade = cash * kelly_fraction
        last_price = self.get_last_price(self.symbol)
        quantity = round(risk_per_trade / last_price, 0)
        return cash, last_price, quantity
    
    def equal_allocation_position_sizing(self, num_positions=10):
        cash = self.get_cash()
        allocation_per_position = cash / num_positions
        last_price = self.get_last_price(self.symbol)
        quantity = round(allocation_per_position / last_price, 0)
        return cash, last_price, quantity

    def maximum_quantity_position_sizing(self):
        cash = self.get_cash()
        last_price = self.get_last_price(self.symbol)
        quantity = round(cash / last_price, 0)
        return cash, last_price, quantity

    def risk_parity_position_sizing(self):
        portfolio_volatility = self.get_portfolio_volatility()  # Assume we have a method to get portfolio volatility
        asset_volatility = self.get_asset_volatility(self.symbol)  # Assume we have a method to get asset volatility
        cash = self.get_cash()
        risk_per_trade = (cash * self.cash_at_risk) * (portfolio_volatility / asset_volatility)
        last_price = self.get_last_price(self.symbol)
        quantity = round(risk_per_trade / last_price, 0)
        return cash, last_price, quantity



    def get_dates(self): 
        today = self.get_datetime()
        three_days_prior = today - Timedelta(days=3)
        return today.strftime('%Y-%m-%d'), three_days_prior.strftime('%Y-%m-%d')

    def get_sentiment(self): 
        today, three_days_prior = self.get_dates()
        news = self.api.get_news(symbol=self.symbol, 
                                 start=three_days_prior, 
                                 end=today) 
        news = [ev.__dict__["_raw"]["headline"] for ev in news]
        probability, sentiment = estimate_sentiment(news)
        return probability, sentiment 

    def on_trading_iteration(self):
        cash, last_price, quantity = self.fixed_fractional_position_sizing() 
        probability, sentiment = self.get_sentiment()

        if cash > last_price: 
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
