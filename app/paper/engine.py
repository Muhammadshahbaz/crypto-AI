from datetime import datetime
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.database.models import PaperTrade
from app.exchanges.factory import get_exchange_client

STARTING_EQUITY = 1000.0

def _paper_pnl(direction: str, entry: float, exit_price: float, amount: float):
    if direction == "LONG":
        pnl = (exit_price - entry) * amount
    else:
        pnl = (entry - exit_price) * amount
    pnl_pct = (pnl / max(entry * amount, 1e-9)) * 100
    return pnl, pnl_pct

async def open_paper_trade(signal: dict, consensus: dict, amount: float, risk_usdt: float):
    async with AsyncSessionLocal() as db:
        exists = await db.execute(
            select(PaperTrade).where(
                PaperTrade.pair == signal["pair"],
                PaperTrade.status == "open"
            )
        )
        if exists.scalars().first():
            return None

        trade = PaperTrade(
            exchange=signal.get("exchange", "unknown"),
            pair=signal["pair"],
            direction=consensus["direction"],
            strategy=signal["strategy"],
            regime=signal["regime"],
            entry=float(signal["entry"]),
            stop_loss=float(signal["stop_loss"]),
            tp1=float(signal["tp1"]),
            tp2=float(signal["tp2"]),
            tp3=float(signal["tp3"]),
            amount=float(amount),
            risk_usd=float(risk_usdt),
            confidence=float(signal.get("confidence", 0)),
            consensus=float(consensus.get("consensus_score", 0)),
            status="open",
            notes="; ".join(signal.get("reasons", [])),
        )
        db.add(trade)
        await db.commit()
        await db.refresh(trade)
        return trade

async def update_open_paper_trades():
    client = get_exchange_client()
    updates = []
    try:
        async with AsyncSessionLocal() as db:
            rows = (await db.execute(select(PaperTrade).where(PaperTrade.status == "open"))).scalars().all()

            for trade in rows:
                try:
                    ohlcv = await client.fetch_ohlcv(trade.pair, "1m", 2)
                    last_price = float(ohlcv[-1][4])
                except Exception:
                    continue

                exit_price = None
                reason = ""

                if trade.direction == "LONG":
                    if last_price <= trade.stop_loss:
                        exit_price, reason = trade.stop_loss, "SL"
                    elif last_price >= trade.tp3:
                        exit_price, reason = trade.tp3, "TP3"
                    elif last_price >= trade.tp2:
                        exit_price, reason = trade.tp2, "TP2"
                    elif last_price >= trade.tp1:
                        exit_price, reason = trade.tp1, "TP1"
                else:
                    if last_price >= trade.stop_loss:
                        exit_price, reason = trade.stop_loss, "SL"
                    elif last_price <= trade.tp3:
                        exit_price, reason = trade.tp3, "TP3"
                    elif last_price <= trade.tp2:
                        exit_price, reason = trade.tp2, "TP2"
                    elif last_price <= trade.tp1:
                        exit_price, reason = trade.tp1, "TP1"

                if exit_price is not None:
                    pnl, pnl_pct = _paper_pnl(trade.direction, trade.entry, exit_price, trade.amount)
                    trade.pnl_usd = float(pnl)
                    trade.pnl_pct = float(pnl_pct)
                    trade.status = "closed"
                    trade.close_reason = reason
                    trade.closed_at = datetime.utcnow()
                    updates.append({"id": trade.id, "pair": trade.pair, "reason": reason, "pnl_usd": pnl})

            await db.commit()
        return updates
    finally:
        await client.close()

async def dashboard_summary():
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(PaperTrade).order_by(PaperTrade.id.asc()))).scalars().all()

    closed = [r for r in rows if r.status == "closed"]
    open_trades = [r for r in rows if r.status == "open"]
    wins = [r for r in closed if r.pnl_usd > 0]
    losses = [r for r in closed if r.pnl_usd <= 0]

    total_pnl = sum(r.pnl_usd for r in closed)
    gross_profit = sum(r.pnl_usd for r in wins)
    gross_loss = abs(sum(r.pnl_usd for r in losses))
    profit_factor = gross_profit / gross_loss if gross_loss else (gross_profit if gross_profit else 0)
    win_rate = (len(wins) / len(closed) * 100) if closed else 0

    equity = STARTING_EQUITY
    curve = [{"trade": 0, "equity": equity}]
    for i, r in enumerate(closed, start=1):
        equity += r.pnl_usd
        curve.append({"trade": i, "equity": round(equity, 2)})

    return {
        "starting_equity": STARTING_EQUITY,
        "equity": round(STARTING_EQUITY + total_pnl, 2),
        "total_pnl": round(total_pnl, 2),
        "open_trades": len(open_trades),
        "closed_trades": len(closed),
        "win_rate": round(win_rate, 2),
        "profit_factor": round(profit_factor, 2),
        "equity_curve": curve,
    }

def serialize_trade(r: PaperTrade):
    return {
        "id": r.id,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "closed_at": r.closed_at.isoformat() if r.closed_at else None,
        "exchange": r.exchange,
        "pair": r.pair,
        "direction": r.direction,
        "strategy": r.strategy,
        "regime": r.regime,
        "entry": r.entry,
        "stop_loss": r.stop_loss,
        "tp1": r.tp1,
        "tp2": r.tp2,
        "tp3": r.tp3,
        "amount": r.amount,
        "risk_usd": r.risk_usd,
        "pnl_usd": r.pnl_usd,
        "pnl_pct": r.pnl_pct,
        "confidence": r.confidence,
        "consensus": r.consensus,
        "status": r.status,
        "close_reason": r.close_reason,
        "notes": r.notes,
    }

async def list_paper_trades(status: str | None = None, limit: int = 100):
    async with AsyncSessionLocal() as db:
        query = select(PaperTrade).order_by(PaperTrade.id.desc()).limit(limit)
        if status:
            query = select(PaperTrade).where(PaperTrade.status == status).order_by(PaperTrade.id.desc()).limit(limit)
        rows = (await db.execute(query)).scalars().all()
    return [serialize_trade(r) for r in rows]
