from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader
from datetime import datetime 
from alpaca_trade_api import REST 
from timedelta import Timedelta 
from finbert_utils import estimate_sentiment
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
    
    """Runs at the start of the """
    def initialize(self, symbol:str="NVDA", cash_at_risk:float=.5): 
        self.symbol = symbol
        self.sleeptime = "12H" 
        self.last_trade = None 
        self.cash_at_risk = cash_at_risk
        self.api = REST(base_url=BASE_URL, key_id=API_KEY, secret_key=API_SECRET)

    import yfinance as yf

    def get_historical_prices(self, symbol):
        if self.broker is None:  # Backtesting mode
            data = yf.download(symbol, start=self.start_date, end=self.end_date)
            return data['Close'].tolist()
        else:  # Live trading mode
            barset = self.api.get_barset(symbol, 'day', limit=1000)
            bars = barset[symbol]
            return [bar.c for bar in bars]

    def get_portfolio(self):
        return {
            'NVDA': {'weight': 1},
        }

    def get_asset_volatility(self, symbol):
        historical_prices = self.get_historical_prices(symbol)
        returns = np.diff(historical_prices) / historical_prices[:-1]
        volatility = np.std(returns)
        return volatility

    def get_portfolio_volatility(self):
        portfolio = self.get_portfolio()
        symbols = list(portfolio.keys())
        weights = np.array([portfolio[symbol]['weight'] for symbol in symbols])
        volatilities = np.array([self.get_asset_volatility(symbol) for symbol in symbols])
        correlation_matrix = self.get_correlation_matrix(symbols)
        portfolio_variance = np.dot(weights.T, np.dot(correlation_matrix * np.outer(volatilities, volatilities), weights))
        portfolio_volatility = np.sqrt(portfolio_variance)
        return portfolio_volatility

    def get_win_loss_ratio(self, symbol):
        trade_history = self.get_trade_history(symbol)
        wins = [trade['profit'] for trade in trade_history if trade['profit'] > 0]
        losses = [-trade['profit'] for trade in trade_history if trade['profit'] < 0]
        if not losses:
            return float('inf') if wins else 0
        average_win = np.mean(wins) if wins else 0
        average_loss = np.mean(losses) if losses else 0
        return average_win / average_loss if average_loss != 0 else float('inf')

    def get_win_probability(self, symbol):
        trade_history = self.get_trade_history(symbol)
        num_trades = len(trade_history)
        num_wins = len([trade for trade in trade_history if trade['profit'] > 0])
        return num_wins / num_trades if num_trades > 0 else 0

    def fixed_fractional_position_sizing(self):
        cash = self.get_cash()
        risk_per_trade = cash * self.cash_at_risk
        last_price = self.get_last_price(self.symbol)
        quantity = round(risk_per_trade / last_price, 0)
        return cash, last_price, quantity
    
    
    """Uses a specific dollar amount for each trade"""
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
        win_probability = self.get_win_probability(self.symbol)  # Assume we have a method for win probability
        win_loss_ratio = self.get_win_loss_ratio(self.symbol)  # Assume we have a method for win/loss ratio
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
