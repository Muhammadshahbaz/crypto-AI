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
