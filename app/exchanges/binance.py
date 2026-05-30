import ccxt.async_support as ccxt
from app.config import settings
from app.exchanges.base import ExchangeClient

class BinanceClient(ExchangeClient):
    name = "binance"

    def __init__(self):
        options = {"defaultType": "future" if settings.binance_market_type == "future" else "spot"}
        self.exchange = ccxt.binance({
            "apiKey": settings.binance_api_key,
            "secret": settings.binance_api_secret,
            "enableRateLimit": True,
            "options": options,
        })
        if settings.binance_testnet:
            self.exchange.set_sandbox_mode(True)

    async def close(self):
        await self.exchange.close()

    async def fetch_ohlcv(self, symbol: str, timeframe: str = "15m", limit: int = 250):
        return await self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

    async def fetch_balance(self):
        if settings.dry_run or not settings.binance_api_key:
            return {"USDT": {"free": 1000.0, "total": 1000.0}}
        return await self.exchange.fetch_balance()

    async def create_order(self, symbol: str, side: str, amount: float, price: float | None = None):
        if settings.dry_run:
            return {
                "id": "DRY_RUN",
                "exchange": self.name,
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "price": price,
            }
        if price:
            return await self.exchange.create_limit_order(symbol, side, amount, price)
        return await self.exchange.create_market_order(symbol, side, amount)
