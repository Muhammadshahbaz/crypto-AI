import pandas as pd
from app.exchanges.base import ExchangeClient
from app.exchanges.factory import get_exchange_client
from app.market.indicators import add_indicators
from app.market.regime_detector import detect_regime
from app.trading.strategies.selector import build_signal

async def scan_pair(client: ExchangeClient, pair: str) -> dict | None:
    raw = await client.fetch_ohlcv(pair, "15m", 250)
    df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df = add_indicators(df)
    if df.empty:
        return None

    row = df.iloc[-1].to_dict()
    regime = detect_regime(row)
    signal = build_signal(pair, row, regime)
    signal["exchange"] = client.name
    return signal

async def scan_all(pairs: list[str]) -> list[dict]:
    client = get_exchange_client()
    try:
        results = []
        for pair in pairs:
            try:
                signal = await scan_pair(client, pair)
                if signal:
                    results.append(signal)
            except Exception as exc:
                results.append({
                    "exchange": client.name,
                    "pair": pair,
                    "direction": "SKIP",
                    "error": str(exc),
                })
        return results
    finally:
        await client.close()
