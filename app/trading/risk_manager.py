from dataclasses import dataclass
from app.config import settings

@dataclass
class AccountSnapshot:
    equity_usdt: float
    daily_pnl_pct: float = 0.0
    weekly_pnl_pct: float = 0.0
    open_positions: int = 0

class RiskManager:
    def validate(self, signal: dict, consensus: dict, account: AccountSnapshot) -> tuple[bool, list[str]]:
        blocks: list[str] = []
        if signal['direction'] == 'SKIP' or consensus['direction'] == 'SKIP':
            blocks.append('Decision is SKIP')
        if signal['confluence'] < settings.signal_confluence_required:
            blocks.append('Not enough confluence')
        if signal['confidence'] < settings.min_confidence_score:
            blocks.append('Confidence below minimum')
        if consensus['consensus_score'] < settings.consensus_threshold:
            blocks.append('Consensus below threshold')
        if account.daily_pnl_pct <= -settings.max_daily_loss:
            blocks.append('Daily loss limit reached')
        if account.weekly_pnl_pct <= -settings.max_weekly_loss:
            blocks.append('Weekly loss limit reached')
        if account.open_positions >= settings.max_concurrent_trades:
            blocks.append('Max concurrent trades reached')
        if not signal.get('stop_loss'):
            blocks.append('Stop loss missing')
        return len(blocks) == 0, blocks

    def position_size(self, entry: float, stop_loss: float, equity_usdt: float) -> tuple[float, float]:
        risk_usdt = equity_usdt * settings.max_risk_per_trade
        distance = abs(entry - stop_loss)
        if distance <= 0:
            return 0.0, 0.0
        amount = risk_usdt / distance
        return float(amount), float(risk_usdt)
