import os
from dotenv import load_dotenv
from binance.client import Client
from datetime import datetime, timezone, timedelta

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
def get_opening_price(symbol):
    try:
        agora = datetime.utcnow()
        inicio_utc = agora.replace(hour=0, minute=0, second=0, microsecond=0)
        start_ts = int(inicio_utc.timestamp() * 1000)

        # Tenta buscar candle de hoje (00:00 UTC)
        klines = client.get_klines(
            symbol=symbol,
            interval=Client.KLINE_INTERVAL_1HOUR,
            startTime=start_ts,
            limit=1
        )
        if klines:
            return float(klines[0][1])

        # Fallback: último candle disponível antes das 00:00
        klines_fallback = client.get_klines(
            symbol=symbol,
            interval=Client.KLINE_INTERVAL_1HOUR,
            limit=1
        )
        if klines_fallback:
            return float(klines_fallback[0][1])

        return None
    except Exception as e:
        print(f"[Erro] get_opening_price({symbol}):", e)
        return None

def get_real_balance(token):
    """
    Retorna o saldo total (free + locked) exato do token, igual à interface da Binance.
    """
    try:
        info = client.get_account()
        for b in info["balances"]:
            if b["asset"] == token:
                return float(b["free"]) + float(b["locked"])
        return 0.0
    except Exception as e:
        print(f"[Erro] get_real_balance({token}):", e)
        return 0.0
