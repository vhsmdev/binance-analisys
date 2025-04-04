import os
from dotenv import load_dotenv
from binance.client import Client

load_dotenv()

API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

client = Client(API_KEY, API_SECRET)

def get_trades(symbol):
    return client.get_my_trades(symbol=symbol)

def get_price(symbol):
    ticker = client.get_symbol_ticker(symbol=symbol)
    return float(ticker["price"])

def get_balance(asset):
    try:
        balance_info = client.get_asset_balance(asset=asset)
        if balance_info:
            free = float(balance_info.get("free", 0))
            locked = float(balance_info.get("locked", 0))
            return free, locked
        return 0.0, 0.0
    except Exception as e:
        print(f"[Erro] get_balance({asset}):", e)
        return 0.0, 0.0
    
def get_open_orders(symbol=None):
    if symbol:
        return client.get_open_orders(symbol=symbol)
    return client.get_open_orders()