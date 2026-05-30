from abc import ABC, abstractmethod

class ExchangeClient(ABC):
    name: str

    @abstractmethod
    async def close(self): ...

    @abstractmethod
    async def fetch_ohlcv(self, symbol: str, timeframe: str = "15m", limit: int = 250): ...

    @abstractmethod
    async def fetch_balance(self): ...

    @abstractmethod
    async def create_order(self, symbol: str, side: str, amount: float, price: float | None = None): ...
