from app.config import settings
from app.exchanges.binance import BinanceClient
from app.exchanges.bitget import BitgetClient

def get_exchange_client():
    exchange = settings.exchange.lower().strip()

    if exchange == "binance":
        return BinanceClient()

    if exchange == "bitget":
        return BitgetClient()

    raise ValueError(f"Unsupported exchange: {settings.exchange}")
