#!/bin/bash
set -e

mkdir -p app/paper app/dashboard

cat >> app/database/models.py <<'EOF'

class PaperTrade(Base):
    __tablename__ = 'paper_trades'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    exchange: Mapped[str] = mapped_column(String(32), default='bitget')
    pair: Mapped[str] = mapped_column(String(32))
    direction: Mapped[str] = mapped_column(String(8))
    strategy: Mapped[str] = mapped_column(String(64))
    regime: Mapped[str] = mapped_column(String(64))

    entry: Mapped[float] = mapped_column(Float)
    stop_loss: Mapped[float] = mapped_column(Float)
    tp1: Mapped[float] = mapped_column(Float)
    tp2: Mapped[float] = mapped_column(Float)
    tp3: Mapped[float] = mapped_column(Float)

    amount: Mapped[float] = mapped_column(Float)
    risk_usd: Mapped[float] = mapped_column(Float)
    pnl_usd: Mapped[float] = mapped_column(Float, default=0.0)
    pnl_pct: Mapped[float] = mapped_column(Float, default=0.0)

    confidence: Mapped[float] = mapped_column(Float)
    consensus: Mapped[float] = mapped_column(Float)

    status: Mapped[str] = mapped_column(String(32), default='open')
    close_reason: Mapped[str] = mapped_column(String(32), default='')
    notes: Mapped[str] = mapped_column(Text, default='')
EOF

cat > app/paper/engine.py <<'EOF'
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
EOF

cat > app/dashboard/web.py <<'EOF'
from fastapi.responses import HTMLResponse

DASHBOARD_HTML = """
<!doctype html>
<html>
<head>
  <title>APEX v5 Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body{margin:0;background:#0b1020;color:#e5e7eb;font-family:Arial}
    .wrap{padding:24px;max-width:1400px;margin:auto}
    .grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}
    .card{background:#111827;border:1px solid #1f2937;border-radius:16px;padding:18px;box-shadow:0 10px 30px rgba(0,0,0,.2)}
    .big{font-size:28px;font-weight:700;margin-top:8px}
    .muted{color:#9ca3af;font-size:13px}
    button{background:#2563eb;color:white;border:0;border-radius:10px;padding:11px 16px;cursor:pointer;font-weight:700}
    table{width:100%;border-collapse:collapse;margin-top:12px}
    th,td{border-bottom:1px solid #1f2937;padding:10px;text-align:left;font-size:13px}
    .good{color:#22c55e}.bad{color:#ef4444}.warn{color:#f59e0b}
    .top{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}
  </style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <div>
      <h1>APEX v5 AI Trading Platform</h1>
      <div class="muted">Paper trading dashboard • Exchange-ready architecture • Dry-run first</div>
    </div>
    <button onclick="scan()">Run Scan</button>
  </div>

  <div class="grid">
    <div class="card"><div class="muted">Equity</div><div class="big" id="equity">$0</div></div>
    <div class="card"><div class="muted">Total PnL</div><div class="big" id="pnl">$0</div></div>
    <div class="card"><div class="muted">Win Rate</div><div class="big" id="winrate">0%</div></div>
    <div class="card"><div class="muted">Open Trades</div><div class="big" id="open">0</div></div>
  </div>

  <div class="card" style="margin-top:16px">
    <h2>Equity Curve</h2>
    <canvas id="curve" height="90"></canvas>
  </div>

  <div class="card" style="margin-top:16px">
    <h2>Paper Trades</h2>
    <table>
      <thead>
        <tr><th>ID</th><th>Exchange</th><th>Pair</th><th>Side</th><th>Status</th><th>Entry</th><th>SL</th><th>TP1</th><th>PnL</th><th>Reason</th></tr>
      </thead>
      <tbody id="trades"></tbody>
    </table>
  </div>

  <div class="card" style="margin-top:16px">
    <h2>Last Scan</h2>
    <pre id="lastscan" class="muted">No scan yet.</pre>
  </div>
</div>

<script>
let chart;
const api = "";

async function load(){
  const s = await fetch(api + "/api/dashboard/summary").then(r=>r.json());
  document.getElementById("equity").innerText = "$" + s.equity;
  document.getElementById("pnl").innerText = "$" + s.total_pnl;
  document.getElementById("pnl").className = "big " + (s.total_pnl >= 0 ? "good" : "bad");
  document.getElementById("winrate").innerText = s.win_rate + "%";
  document.getElementById("open").innerText = s.open_trades;

  const labels = s.equity_curve.map(x=>x.trade);
  const data = s.equity_curve.map(x=>x.equity);
  if(chart) chart.destroy();
  chart = new Chart(document.getElementById("curve"), {
    type: "line",
    data: {labels, datasets:[{label:"Equity", data, tension:.35}]},
    options: {plugins:{legend:{labels:{color:"#e5e7eb"}}}, scales:{x:{ticks:{color:"#9ca3af"}}, y:{ticks:{color:"#9ca3af"}}}}
  });

  const trades = await fetch(api + "/api/paper-trades").then(r=>r.json());
  document.getElementById("trades").innerHTML = trades.map(t => `
    <tr>
      <td>${t.id}</td><td>${t.exchange}</td><td>${t.pair}</td><td>${t.direction}</td>
      <td>${t.status}</td><td>${Number(t.entry).toFixed(4)}</td><td>${Number(t.stop_loss).toFixed(4)}</td>
      <td>${Number(t.tp1).toFixed(4)}</td>
      <td class="${t.pnl_usd >= 0 ? "good" : "bad"}">$${Number(t.pnl_usd).toFixed(2)}</td>
      <td>${t.close_reason || ""}</td>
    </tr>`).join("");
}

async function scan(){
  document.getElementById("lastscan").innerText = "Scanning...";
  const res = await fetch(api + "/api/scan-once", {method:"POST"}).then(r=>r.json());
  document.getElementById("lastscan").innerText = JSON.stringify(res, null, 2);
  await load();
}

load();
setInterval(load, 10000);
</script>
</body>
</html>
"""

def dashboard_page():
    return HTMLResponse(DASHBOARD_HTML)
EOF

python3 - <<'PY'
from pathlib import Path
p = Path("app/trading/executor.py")
s = p.read_text()
if "from app.paper.engine import open_paper_trade" not in s:
    s = s.replace("from app.notifications.telegram import notify", "from app.notifications.telegram import notify\nfrom app.paper.engine import open_paper_trade")
if "await open_paper_trade" not in s:
    s = s.replace(
        "await self._log_trade(signal, consensus, amount, risk_usdt, 'dry_run' if settings.dry_run else 'submitted')",
        "await self._log_trade(signal, consensus, amount, risk_usdt, 'dry_run' if settings.dry_run else 'submitted')\n            if settings.dry_run:\n                await open_paper_trade(signal, consensus, amount, risk_usdt)"
    )
p.write_text(s)
PY

cat > app/main.py <<'EOF'
from fastapi import FastAPI
from sqlalchemy import select
from app.config import settings
from app.database.session import init_db, AsyncSessionLocal
from app.database.models import TradeLog
from app.market.scanner import scan_all
from app.trading.executor import TradeExecutor
from app.paper.engine import dashboard_summary, list_paper_trades, update_open_paper_trades
from app.dashboard.web import dashboard_page

app = FastAPI(title=settings.app_name)

@app.on_event('startup')
async def startup():
    await init_db()

@app.get('/')
async def root():
    return {'status': 'ok', 'app': settings.app_name, 'dashboard': '/dashboard', 'docs': '/docs'}

@app.get('/dashboard')
async def dashboard():
    return dashboard_page()

@app.get('/health')
async def health():
    return {
        'status': 'ok',
        'app': settings.app_name,
        'exchange': settings.exchange,
        'dry_run': settings.dry_run,
        'testnet': settings.binance_testnet,
    }

@app.get('/api/config')
async def config():
    return {
        'app': settings.app_name,
        'exchange': settings.exchange,
        'pairs': settings.pairs,
        'dry_run': settings.dry_run,
        'testnet': settings.binance_testnet,
        'risk_per_trade': settings.max_risk_per_trade,
        'max_leverage': settings.max_leverage,
    }

@app.post('/api/scan-once')
async def scan_once():
    await update_open_paper_trades()
    signals = await scan_all(settings.pairs)
    executor = TradeExecutor()
    results = []
    for signal in signals:
        if signal.get('direction') != 'SKIP':
            results.append(await executor.evaluate_and_execute(signal))
        else:
            results.append({'ok': False, 'blocks': ['strategy skipped'], 'signal': signal})
    updates = await update_open_paper_trades()
    return {'count': len(results), 'closed_updates': updates, 'results': results}

@app.post('/api/paper/update')
async def paper_update():
    updates = await update_open_paper_trades()
    return {'updated': len(updates), 'results': updates}

@app.get('/api/dashboard/summary')
async def dashboard_api_summary():
    return await dashboard_summary()

@app.get('/api/paper-trades')
async def paper_trades(status: str | None = None, limit: int = 100):
    return await list_paper_trades(status=status, limit=limit)

@app.get('/api/trades')
async def trades(limit: int = 50):
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(TradeLog).order_by(TradeLog.id.desc()).limit(limit))).scalars().all()
        return [{
            'created_at': r.created_at.isoformat(), 'pair': r.pair, 'direction': r.direction,
            'strategy': r.strategy, 'entry': r.entry, 'stop_loss': r.stop_loss,
            'tp1': r.tp1, 'risk_usd': r.risk_usd, 'status': r.status
        } for r in rows]
EOF

git add .
git commit -m "Add v5 dashboard and paper trading engine" || true
git push origin main

docker compose down
docker compose up -d --build
docker compose logs --tail=80
