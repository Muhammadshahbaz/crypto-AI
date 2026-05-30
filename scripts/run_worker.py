import asyncio
from app.config import settings
from app.database.session import init_db
from app.market.scanner import scan_all
from app.trading.executor import TradeExecutor

async def main():
    await init_db()
    executor = TradeExecutor()
    while True:
        signals = await scan_all(settings.pairs)
        for signal in signals:
            if signal.get('direction') != 'SKIP':
                print(await executor.evaluate_and_execute(signal))
            else:
                print({'pair': signal.get('pair'), 'skip': signal.get('reasons', signal.get('error'))})
        await asyncio.sleep(settings.scan_interval_seconds)

if __name__ == '__main__':
    asyncio.run(main())
