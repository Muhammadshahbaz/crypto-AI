from fastapi import FastAPI
from sqlalchemy import select
from app.config import settings
from app.database.session import init_db, AsyncSessionLocal
from app.database.models import TradeLog
from app.market.scanner import scan_all
from app.trading.executor import TradeExecutor
from app.paper.engine import dashboard_summary, list_paper_trades, update_open_paper_trades
from app.dashboard.web import dashboard_page
from app.admin.web import admin_page
from app.admin.routes import router as admin_router

app = FastAPI(title=settings.app_name)
app.include_router(admin_router)

@app.on_event('startup')
async def startup():
    await init_db()

@app.get('/')
async def root():
    return {'status': 'ok', 'app': settings.app_name, 'dashboard': '/dashboard', 'admin': '/admin', 'docs': '/docs'}

@app.get('/dashboard')
async def dashboard():
    return dashboard_page()

@app.get('/admin')
async def admin():
    return admin_page()

@app.get('/health')
async def health():
    return {'status': 'ok', 'app': settings.app_name, 'exchange': settings.exchange, 'dry_run': settings.dry_run, 'testnet': settings.binance_testnet}

@app.get('/api/config')
async def config():
    return {'app': settings.app_name, 'exchange': settings.exchange, 'pairs': settings.pairs, 'dry_run': settings.dry_run, 'testnet': settings.binance_testnet, 'risk_per_trade': settings.max_risk_per_trade, 'max_leverage': settings.max_leverage}

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
        return [{'created_at': r.created_at.isoformat(), 'pair': r.pair, 'direction': r.direction, 'strategy': r.strategy, 'entry': r.entry, 'stop_loss': r.stop_loss, 'tp1': r.tp1, 'risk_usd': r.risk_usd, 'status': r.status} for r in rows]
