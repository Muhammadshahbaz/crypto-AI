#!/bin/bash
set -e

echo "=== APEX v5.2 Admin Trading Mode Upgrade ==="

cd "$(dirname "$0")"

mkdir -p app/admin

cat > app/admin/__init__.py <<'EOF'
# APEX admin module
EOF

cat > app/admin/service.py <<'EOF'
from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.database.session import AsyncSessionLocal
from app.database.models import BotState
from app.config import settings


SAFE_ENV_KEYS = {
    "APP_NAME",
    "EXCHANGE",
    "TRADING_MODE",
    "DRY_RUN",
    "BINANCE_TESTNET",
    "BINANCE_API_KEY",
    "BINANCE_API_SECRET",
    "BINANCE_MARKET_TYPE",
    "BITGET_API_KEY",
    "BITGET_API_SECRET",
    "BITGET_API_PASSWORD",
    "BITGET_MARKET_TYPE",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "AI_OPENAI_ENABLED",
    "AI_CLAUDE_ENABLED",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "MAX_RISK_PER_TRADE",
    "MAX_DAILY_LOSS",
    "MAX_WEEKLY_LOSS",
    "DEFAULT_LEVERAGE",
    "MAX_LEVERAGE",
    "CONSENSUS_THRESHOLD",
    "MIN_CONFIDENCE_SCORE",
    "SIGNAL_CONFLUENCE_REQUIRED",
    "PREFERRED_PAIRS",
}


def mask_secret(value: str | None) -> str:
    if not value:
        return ""
    value = str(value)
    if len(value) <= 8:
        return "****"
    return value[:4] + "..." + value[-4:]


def mode_flags(trading_mode: str) -> dict[str, Any]:
    mode = (trading_mode or "paper").lower().strip()
    return {
        "trading_mode": mode,
        "is_paper": mode == "paper",
        "is_exchange_demo": mode in {"demo", "testnet"},
        "is_live": mode == "live",
        "live_warning": mode == "live",
    }


def normalize_payload(payload: dict[str, Any]) -> dict[str, str]:
    clean: dict[str, str] = {}
    for key, value in payload.items():
        key = str(key).upper().strip()
        if key not in SAFE_ENV_KEYS:
            continue
        if value is None:
            value = ""
        clean[key] = str(value).strip()
    return clean


async def set_bot_state(key: str, value: str) -> None:
    async with AsyncSessionLocal() as db:
        row = (await db.execute(select(BotState).where(BotState.key == key))).scalars().first()
        if row:
            row.value = value
        else:
            db.add(BotState(key=key, value=value))
        await db.commit()


async def get_bot_state(key: str, default: str = "") -> str:
    async with AsyncSessionLocal() as db:
        row = (await db.execute(select(BotState).where(BotState.key == key))).scalars().first()
        return row.value if row else default


async def save_admin_settings(payload: dict[str, Any]) -> dict[str, Any]:
    clean = normalize_payload(payload)

    for key, value in clean.items():
        await set_bot_state(key, value)

    update_env_file(clean)

    return {
        "ok": True,
        "saved_keys": sorted(clean.keys()),
        "restart_required": True,
        "message": "Settings saved. Restart Docker container for exchange/API config changes to fully apply.",
    }


async def load_admin_settings() -> dict[str, Any]:
    exchange = await get_bot_state("EXCHANGE", getattr(settings, "exchange", "bitget"))
    trading_mode = await get_bot_state("TRADING_MODE", getattr(settings, "trading_mode", "paper"))

    data = {
        "APP_NAME": getattr(settings, "app_name", "APEX AI Trading Platform"),
        "EXCHANGE": exchange,
        "TRADING_MODE": trading_mode,
        "DRY_RUN": str(getattr(settings, "dry_run", True)).lower(),
        "BINANCE_TESTNET": str(getattr(settings, "binance_testnet", True)).lower(),
        "BINANCE_MARKET_TYPE": getattr(settings, "binance_market_type", "spot"),
        "BITGET_MARKET_TYPE": getattr(settings, "bitget_market_type", "spot"),
        "AI_OPENAI_ENABLED": str(getattr(settings, "ai_openai_enabled", False)).lower(),
        "AI_CLAUDE_ENABLED": str(getattr(settings, "ai_claude_enabled", False)).lower(),
        "MAX_RISK_PER_TRADE": str(getattr(settings, "max_risk_per_trade", 0.005)),
        "MAX_DAILY_LOSS": str(getattr(settings, "max_daily_loss", 0.03)),
        "MAX_WEEKLY_LOSS": str(getattr(settings, "max_weekly_loss", 0.08)),
        "DEFAULT_LEVERAGE": str(getattr(settings, "default_leverage", 1)),
        "MAX_LEVERAGE": str(getattr(settings, "max_leverage", 3)),
        "CONSENSUS_THRESHOLD": str(getattr(settings, "consensus_threshold", 0.65)),
        "MIN_CONFIDENCE_SCORE": str(getattr(settings, "min_confidence_score", 0.70)),
        "SIGNAL_CONFLUENCE_REQUIRED": str(getattr(settings, "signal_confluence_required", 4)),
        "PREFERRED_PAIRS": getattr(settings, "preferred_pairs", "BTC/USDT,ETH/USDT,SOL/USDT,BNB/USDT,AVAX/USDT"),
        "BINANCE_API_KEY_MASKED": mask_secret(getattr(settings, "binance_api_key", "")),
        "BITGET_API_KEY_MASKED": mask_secret(getattr(settings, "bitget_api_key", "")),
        "OPENAI_API_KEY_MASKED": mask_secret(getattr(settings, "openai_api_key", "")),
        "ANTHROPIC_API_KEY_MASKED": mask_secret(getattr(settings, "anthropic_api_key", "")),
        "TELEGRAM_BOT_TOKEN_MASKED": mask_secret(getattr(settings, "telegram_bot_token", "")),
    }
    data.update(mode_flags(trading_mode))
    return data


def update_env_file(values: dict[str, str]) -> None:
    env_path = Path(".env")
    existing: dict[str, str] = {}

    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if not line.strip() or line.strip().startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            existing[k.strip()] = v.strip()

    existing.update(values)

    mode = existing.get("TRADING_MODE", "paper").lower()
    if mode == "paper":
        existing["DRY_RUN"] = "true"
    elif mode in {"demo", "testnet"}:
        existing["DRY_RUN"] = "false"
        existing["BINANCE_TESTNET"] = "true"
    elif mode == "live":
        existing["DRY_RUN"] = "false"
        existing["BINANCE_TESTNET"] = "false"

    order = [
        "APP_NAME", "ENV", "DRY_RUN", "EXCHANGE", "TRADING_MODE",
        "BINANCE_TESTNET", "BINANCE_API_KEY", "BINANCE_API_SECRET", "BINANCE_MARKET_TYPE",
        "BITGET_API_KEY", "BITGET_API_SECRET", "BITGET_API_PASSWORD", "BITGET_MARKET_TYPE",
        "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "AI_OPENAI_ENABLED", "AI_CLAUDE_ENABLED",
        "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
        "DATABASE_URL", "SCAN_INTERVAL_SECONDS",
        "MAX_RISK_PER_TRADE", "MAX_DAILY_LOSS", "MAX_WEEKLY_LOSS",
        "MAX_CONCURRENT_TRADES", "DEFAULT_LEVERAGE", "MAX_LEVERAGE",
        "CONSENSUS_THRESHOLD", "MIN_CONFIDENCE_SCORE", "SIGNAL_CONFLUENCE_REQUIRED", "PREFERRED_PAIRS",
    ]

    lines = []
    for key in order:
        if key in existing:
            lines.append(f"{key}={existing[key]}")

    for key in sorted(existing.keys()):
        if key not in order:
            lines.append(f"{key}={existing[key]}")

    env_path.write_text("\n".join(lines) + "\n")
EOF

cat > app/admin/web.py <<'EOF'
from fastapi.responses import HTMLResponse

ADMIN_HTML = """
<!doctype html>
<html>
<head>
  <title>APEX v5.2 Admin</title>
  <style>
    body{margin:0;background:#0b1020;color:#e5e7eb;font-family:Arial}
    .wrap{padding:24px;max-width:1300px;margin:auto}
    .top{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px}
    .grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
    .card{background:#111827;border:1px solid #1f2937;border-radius:16px;padding:18px;margin-bottom:16px}
    label{font-size:13px;color:#9ca3af;display:block;margin-top:10px}
    input,select{width:100%;box-sizing:border-box;padding:10px;border-radius:10px;border:1px solid #374151;background:#020617;color:#fff;margin-top:5px}
    button{background:#2563eb;color:white;border:0;border-radius:10px;padding:11px 16px;cursor:pointer;font-weight:700;margin-right:8px}
    .danger{background:#dc2626}.ok{background:#16a34a}.warn{background:#f59e0b;color:#111}
    .pill{display:inline-block;padding:6px 10px;border-radius:999px;background:#1f2937;margin-right:8px;font-size:12px}
    .paper{background:#2563eb}.demo{background:#f59e0b;color:#111}.live{background:#dc2626}
    .muted{color:#9ca3af;font-size:13px}
    pre{background:#020617;border-radius:12px;padding:12px;overflow:auto;max-height:280px}
    a{color:#93c5fd}
  </style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <div>
      <h1>APEX v5.2 Admin Panel</h1>
      <div class="muted">Exchange APIs • Trading Mode • AI Keys • Risk Settings</div>
    </div>
    <div>
      <a href="/dashboard">Dashboard</a> · <a href="/docs">API Docs</a>
    </div>
  </div>

  <div class="card">
    <h2>Current Safety Mode</h2>
    <div id="modePill" class="pill">Loading...</div>
    <div class="muted" id="modeHelp"></div>
  </div>

  <div class="grid">
    <div class="card">
      <h2>Trading Mode</h2>
      <label>Mode</label>
      <select id="TRADING_MODE">
        <option value="paper">Paper Trading — No real exchange orders</option>
        <option value="demo">Exchange Demo/Testnet — Fake exchange/demo funds</option>
        <option value="live">Live Real Money — Dangerous</option>
      </select>

      <label>Active Exchange</label>
      <select id="EXCHANGE">
        <option value="bitget">Bitget</option>
        <option value="binance">Binance</option>
        <option value="bybit" disabled>Bybit — coming soon</option>
        <option value="okx" disabled>OKX — coming soon</option>
        <option value="kucoin" disabled>KuCoin — coming soon</option>
      </select>

      <label>Preferred Pairs</label>
      <input id="PREFERRED_PAIRS" placeholder="BTC/USDT,ETH/USDT,SOL/USDT">
    </div>

    <div class="card">
      <h2>Bitget API</h2>
      <div class="muted">Use demo/testnet credentials first. Do not use live funds until risk controls are verified.</div>
      <label>Bitget Market Type</label>
      <select id="BITGET_MARKET_TYPE">
        <option value="spot">Spot</option>
        <option value="swap">Futures/Swap</option>
      </select>
      <label>API Key</label>
      <input id="BITGET_API_KEY" placeholder="Leave blank to keep existing">
      <label>API Secret</label>
      <input id="BITGET_API_SECRET" type="password" placeholder="Leave blank to keep existing">
      <label>API Password / Passphrase</label>
      <input id="BITGET_API_PASSWORD" type="password" placeholder="Leave blank to keep existing">
      <div class="muted" id="bitgetMasked"></div>
    </div>

    <div class="card">
      <h2>Binance API</h2>
      <label>Binance Testnet</label>
      <select id="BINANCE_TESTNET">
        <option value="true">true</option>
        <option value="false">false</option>
      </select>
      <label>Binance Market Type</label>
      <select id="BINANCE_MARKET_TYPE">
        <option value="spot">Spot</option>
        <option value="future">Futures</option>
      </select>
      <label>API Key</label>
      <input id="BINANCE_API_KEY" placeholder="Leave blank to keep existing">
      <label>API Secret</label>
      <input id="BINANCE_API_SECRET" type="password" placeholder="Leave blank to keep existing">
      <div class="muted" id="binanceMasked"></div>
    </div>

    <div class="card">
      <h2>AI Providers</h2>
      <label>OpenAI Enabled</label>
      <select id="AI_OPENAI_ENABLED"><option value="false">false</option><option value="true">true</option></select>
      <label>OpenAI API Key</label>
      <input id="OPENAI_API_KEY" type="password" placeholder="Leave blank to keep existing">

      <label>Claude Enabled</label>
      <select id="AI_CLAUDE_ENABLED"><option value="false">false</option><option value="true">true</option></select>
      <label>Claude API Key</label>
      <input id="ANTHROPIC_API_KEY" type="password" placeholder="Leave blank to keep existing">
      <div class="muted" id="aiMasked"></div>
    </div>

    <div class="card">
      <h2>Risk Settings</h2>
      <label>Max Risk Per Trade</label>
      <input id="MAX_RISK_PER_TRADE" placeholder="0.005">
      <label>Max Daily Loss</label>
      <input id="MAX_DAILY_LOSS" placeholder="0.03">
      <label>Max Weekly Loss</label>
      <input id="MAX_WEEKLY_LOSS" placeholder="0.08">
      <label>Default Leverage</label>
      <input id="DEFAULT_LEVERAGE" placeholder="1">
      <label>Max Leverage</label>
      <input id="MAX_LEVERAGE" placeholder="3">
    </div>

    <div class="card">
      <h2>Actions</h2>
      <button onclick="save()">Save Settings</button>
      <button onclick="testExchange()">Test Exchange Account</button>
      <button class="ok" onclick="testPaperTrade()">Create Test Paper Trade</button>
      <button class="warn" onclick="scanOnce()">Run Scan</button>
      <p class="muted">After saving exchange/API settings, rebuild/restart Docker so .env settings fully reload.</p>
    </div>
  </div>

  <div class="card">
    <h2>Output</h2>
    <pre id="out">Ready.</pre>
  </div>
</div>

<script>
const ids = [
 "TRADING_MODE","EXCHANGE","PREFERRED_PAIRS","BITGET_MARKET_TYPE","BITGET_API_KEY","BITGET_API_SECRET","BITGET_API_PASSWORD",
 "BINANCE_TESTNET","BINANCE_MARKET_TYPE","BINANCE_API_KEY","BINANCE_API_SECRET",
 "AI_OPENAI_ENABLED","OPENAI_API_KEY","AI_CLAUDE_ENABLED","ANTHROPIC_API_KEY",
 "MAX_RISK_PER_TRADE","MAX_DAILY_LOSS","MAX_WEEKLY_LOSS","DEFAULT_LEVERAGE","MAX_LEVERAGE"
];

function val(id){ return document.getElementById(id).value; }
function set(id,v){ const el=document.getElementById(id); if(el && v !== undefined && v !== null) el.value = v; }
function out(x){ document.getElementById("out").innerText = typeof x === "string" ? x : JSON.stringify(x,null,2); }

function updateModeUI(mode){
  const pill = document.getElementById("modePill");
  pill.className = "pill " + (mode === "live" ? "live" : mode === "demo" ? "demo" : "paper");
  pill.innerText = "MODE: " + String(mode || "paper").toUpperCase();
  document.getElementById("modeHelp").innerText =
    mode === "live" ? "LIVE REAL MONEY MODE. Only use after demo/paper results are proven." :
    mode === "demo" ? "Exchange demo/testnet mode. Uses exchange demo funds where supported." :
    "Paper mode. No real exchange orders. Safest mode for testing.";
}

async function load(){
  const s = await fetch("/api/admin/settings").then(r=>r.json());
  ["TRADING_MODE","EXCHANGE","PREFERRED_PAIRS","BITGET_MARKET_TYPE","BINANCE_TESTNET","BINANCE_MARKET_TYPE",
   "AI_OPENAI_ENABLED","AI_CLAUDE_ENABLED","MAX_RISK_PER_TRADE","MAX_DAILY_LOSS","MAX_WEEKLY_LOSS","DEFAULT_LEVERAGE","MAX_LEVERAGE"]
   .forEach(k => set(k, s[k]));
  updateModeUI(s.TRADING_MODE);
  document.getElementById("bitgetMasked").innerText = "Saved key: " + (s.BITGET_API_KEY_MASKED || "not set");
  document.getElementById("binanceMasked").innerText = "Saved key: " + (s.BINANCE_API_KEY_MASKED || "not set");
  document.getElementById("aiMasked").innerText = "OpenAI: " + (s.OPENAI_API_KEY_MASKED || "not set") + " | Claude: " + (s.ANTHROPIC_API_KEY_MASKED || "not set");
}

async function save(){
  const payload = {};
  ids.forEach(id => {
    const v = val(id);
    if(["BITGET_API_KEY","BITGET_API_SECRET","BITGET_API_PASSWORD","BINANCE_API_KEY","BINANCE_API_SECRET","OPENAI_API_KEY","ANTHROPIC_API_KEY"].includes(id) && !v) return;
    payload[id] = v;
  });
  if(payload.TRADING_MODE === "live"){
    if(!confirm("LIVE mode can place real-money trades after live execution is enabled. Continue?")) return;
  }
  const res = await fetch("/api/admin/settings", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)}).then(r=>r.json());
  out(res);
  await load();
}

async function testExchange(){
  const res = await fetch("/api/exchange/account").then(r=>r.json());
  out(res);
}

async function testPaperTrade(){
  const res = await fetch("/api/paper/test-trade?pair=BTC/USDT&direction=LONG", {method:"POST"}).then(r=>r.json());
  out(res);
}

async function scanOnce(){
  const res = await fetch("/api/scan-once", {method:"POST"}).then(r=>r.json());
  out(res);
}

load();
</script>
</body>
</html>
"""

def admin_page():
    return HTMLResponse(ADMIN_HTML)
EOF

python3 - <<'PY'
from pathlib import Path
p = Path("app/config.py")
s = p.read_text()
if "trading_mode:" not in s:
    s = s.replace('exchange: str = "bitget"', 'exchange: str = "bitget"\n    trading_mode: str = "paper"  # paper, demo/testnet, live')
p.write_text(s)
PY

python3 - <<'PY'
from pathlib import Path
p = Path("app/main.py")
s = p.read_text()

imports = [
    "from typing import Any",
    "from fastapi import Body",
    "from app.admin.web import admin_page",
    "from app.admin.service import load_admin_settings, save_admin_settings",
    "from app.exchanges.factory import get_exchange_client",
    "from app.paper.engine import open_paper_trade",
]
for imp in imports:
    if imp not in s:
        s = imp + "\n" + s

if "@app.get('/admin')" not in s:
    insert_after = """@app.get('/dashboard')
async def dashboard():
    return dashboard_page()
"""
    admin_route = """
@app.get('/admin')
async def admin():
    return admin_page()
"""
    s = s.replace(insert_after, insert_after + admin_route)

if "@app.get('/api/admin/settings')" not in s:
    extra = """
@app.get('/api/admin/settings')
async def admin_get_settings():
    return await load_admin_settings()

@app.post('/api/admin/settings')
async def admin_save_settings(payload: dict[str, Any] = Body(...)):
    return await save_admin_settings(payload)

@app.get('/api/exchange/account')
async def exchange_account():
    client = get_exchange_client()
    try:
        balance = await client.fetch_balance()
        return {
            'ok': True,
            'exchange': client.name,
            'balance': balance,
            'note': 'In paper mode this may return virtual balance. In demo/live mode restart Docker after saving API keys.'
        }
    except Exception as exc:
        return {'ok': False, 'error': str(exc)}
    finally:
        await client.close()

@app.post('/api/paper/test-trade')
async def paper_test_trade(pair: str = 'BTC/USDT', direction: str = 'LONG'):
    client = get_exchange_client()
    try:
        raw = await client.fetch_ohlcv(pair, '1m', 2)
        entry = float(raw[-1][4])
    finally:
        await client.close()

    direction = direction.upper()
    if direction not in {'LONG', 'SHORT'}:
        direction = 'LONG'

    if direction == 'LONG':
        stop_loss = entry * 0.995
        tp1 = entry * 1.005
        tp2 = entry * 1.010
        tp3 = entry * 1.020
    else:
        stop_loss = entry * 1.005
        tp1 = entry * 0.995
        tp2 = entry * 0.990
        tp3 = entry * 0.980

    signal = {
        'exchange': settings.exchange,
        'pair': pair,
        'direction': direction,
        'strategy': 'manual_test',
        'regime': 'TEST',
        'entry': entry,
        'stop_loss': stop_loss,
        'tp1': tp1,
        'tp2': tp2,
        'tp3': tp3,
        'confidence': 1.0,
        'reasons': ['Manual admin test trade']
    }
    consensus = {'direction': direction, 'consensus_score': 1.0}
    amount = 10 / entry
    trade = await open_paper_trade(signal, consensus, amount, 5.0)
    if trade is None:
        return {'ok': False, 'message': 'An open paper trade for this pair already exists.'}
    return {'ok': True, 'trade_id': trade.id, 'pair': pair, 'direction': direction, 'entry': entry}
"""
    s = s + "\n" + extra

p.write_text(s)
PY

git add .
git commit -m "Add v5.2 trading mode admin controls" || true
git push origin main

docker compose down
docker compose up -d --build

echo ""
echo "=== v5.2 installed ==="
echo "Admin:     http://34.24.22.108:8000/admin"
echo "Dashboard: http://34.24.22.108:8000/dashboard"
echo ""
