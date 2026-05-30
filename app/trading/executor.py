from sqlalchemy import select
from app.config import settings
from app.exchanges.factory import get_exchange_client
from app.exchanges.base import ExchangeClient
from app.trading.risk_manager import RiskManager, AccountSnapshot
from app.ai.consensus import get_consensus
from app.database.session import AsyncSessionLocal
from app.database.models import TradeLog
from app.notifications.telegram import notify

class TradeExecutor:
    def __init__(self):
        self.risk = RiskManager()

    async def _equity(self, client: ExchangeClient) -> float:
        bal = await client.fetch_balance()
        usdt = bal.get('USDT') or {}
        return float(usdt.get('total') or usdt.get('free') or 1000.0)

    async def evaluate_and_execute(self, signal: dict) -> dict:
        if signal.get('error'):
            return {'status': 'error', 'signal': signal}
        consensus = await get_consensus(signal)
        client = get_exchange_client()
        try:
            equity = await self._equity(client)
            account = AccountSnapshot(equity_usdt=equity)
            ok, blocks = self.risk.validate(signal, consensus, account)
            amount, risk_usdt = self.risk.position_size(signal['entry'], signal['stop_loss'], equity)

            result = {
                'pair': signal['pair'],
                'direction': consensus['direction'],
                'ok': ok,
                'blocks': blocks,
                'amount': amount,
                'risk_usdt': risk_usdt,
                'signal': signal,
                'consensus': consensus,
                'dry_run': settings.dry_run,
            }
            if not ok:
                return result

            side = 'buy' if consensus['direction'] == 'LONG' else 'sell'
            order = await client.create_order(signal['pair'], side, amount, signal['entry'])
            result['order'] = order
            await self._log_trade(signal, consensus, amount, risk_usdt, 'dry_run' if settings.dry_run else 'submitted')
            await notify(self._format_alert(signal, consensus, amount, risk_usdt))
            return result
        finally:
            await client.close()

    async def _log_trade(self, signal: dict, consensus: dict, amount: float, risk_usdt: float, status: str) -> None:
        async with AsyncSessionLocal() as db:
            db.add(TradeLog(
                pair=signal['pair'], direction=consensus['direction'], strategy=signal['strategy'], regime=signal['regime'],
                entry=signal['entry'], stop_loss=signal['stop_loss'], tp1=signal['tp1'], tp2=signal['tp2'], tp3=signal['tp3'],
                risk_usd=risk_usdt, position_size=amount, leverage=settings.default_leverage,
                confidence=signal['confidence'], consensus=consensus['consensus_score'], dry_run=settings.dry_run,
                status=status, notes='; '.join(signal.get('reasons', []))
            ))
            await db.commit()

    def _format_alert(self, signal: dict, consensus: dict, amount: float, risk_usdt: float) -> str:
        return (
            f"APEX v4 Trade {'DRY RUN' if settings.dry_run else 'LIVE'}\n"
            f"Pair: {signal['pair']}\nDirection: {consensus['direction']}\nStrategy: {signal['strategy']}\n"
            f"Entry: {signal['entry']:.6f}\nSL: {signal['stop_loss']:.6f}\n"
            f"TP1: {signal['tp1']:.6f} | TP2: {signal['tp2']:.6f} | TP3: {signal['tp3']:.6f}\n"
            f"Size: {amount:.6f}\nRisk: ${risk_usdt:.2f}\nConsensus: {consensus['consensus_score']:.2%}"
        )
