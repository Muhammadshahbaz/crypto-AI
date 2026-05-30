from fastapi.responses import HTMLResponse

ADMIN_HTML = """
<!doctype html>
<html>
<head>
  <title>APEX Admin Panel</title>
  <style>
    body{margin:0;background:#0b1020;color:#e5e7eb;font-family:Arial}
    .wrap{padding:24px;max-width:1300px;margin:auto}
    .top{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}
    .grid{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}
    .card{background:#111827;border:1px solid #1f2937;border-radius:16px;padding:18px;margin-bottom:16px}
    label{font-size:13px;color:#9ca3af}
    input,select{width:100%;box-sizing:border-box;padding:10px;border-radius:10px;border:1px solid #374151;background:#020617;color:#fff;margin:6px 0 12px}
    button{background:#2563eb;color:white;border:0;border-radius:10px;padding:11px 16px;cursor:pointer;font-weight:700}
    button.red{background:#dc2626} button.green{background:#16a34a}
    table{width:100%;border-collapse:collapse;margin-top:12px}
    th,td{border-bottom:1px solid #1f2937;padding:10px;text-align:left;font-size:13px}
    .muted{color:#9ca3af}.good{color:#22c55e}.bad{color:#ef4444}
    a{color:#60a5fa;text-decoration:none}
    pre{background:#020617;border-radius:12px;padding:12px;overflow:auto}
  </style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <div>
      <h1>APEX v5.1 Admin Panel</h1>
      <div class="muted">Exchange APIs • AI APIs • Risk Settings • Bot Controls</div>
    </div>
    <div>
      <a href="/dashboard">Dashboard</a> &nbsp; | &nbsp; <a href="/docs">API Docs</a>
    </div>
  </div>

  <div class="grid">
    <div class="card">
      <h2>Bot Status</h2>
      <p>Status: <b id="botStatus">Loading...</b></p>
      <p>Exchange: <b id="botExchange">-</b></p>
      <p>Dry Run: <b id="dryRun">-</b></p>
      <button class="green" onclick="botStart()">Start Bot</button>
      <button class="red" onclick="botStop()">Stop Bot</button>
    </div>

    <div class="card">
      <h2>Risk Settings</h2>
      <label>Max risk per trade</label><input id="max_risk_per_trade" value="0.005">
      <label>Max daily loss</label><input id="max_daily_loss" value="0.03">
      <label>Max weekly loss</label><input id="max_weekly_loss" value="0.08">
      <label>Max concurrent trades</label><input id="max_concurrent_trades" value="3">
      <label>Max leverage</label><input id="max_leverage" value="3">
      <label>Preferred pairs</label><input id="preferred_pairs" value="BTC/USDT,ETH/USDT,SOL/USDT,BNB/USDT,AVAX/USDT">
      <button onclick="saveRisk()">Save Risk Settings</button>
    </div>
  </div>

  <div class="card">
    <h2>Exchange API Settings</h2>
    <div class="grid">
      <div>
        <label>Exchange</label>
        <select id="exchange">
          <option value="bitget">Bitget</option>
          <option value="binance">Binance</option>
          <option value="bybit">Bybit</option>
          <option value="okx">OKX</option>
          <option value="kucoin">KuCoin</option>
        </select>
        <label>Label</label><input id="exchange_label" value="Default">
        <label>Market Type</label>
        <select id="market_type"><option value="spot">Spot</option><option value="swap">Futures/Swap</option></select>
        <label>Mode</label>
        <select id="mode"><option value="paper">Paper</option><option value="testnet">Testnet</option><option value="live">Live</option></select>
      </div>
      <div>
        <label>API Key</label><input id="api_key" placeholder="Paste API key">
        <label>API Secret</label><input id="api_secret" placeholder="Paste API secret">
        <label>Password / Passphrase</label><input id="api_password" placeholder="Bitget/OKX passphrase">
        <button onclick="saveExchange()">Save Exchange</button>
      </div>
    </div>
    <h3>Saved Exchanges</h3>
    <table>
      <thead><tr><th>ID</th><th>Exchange</th><th>Label</th><th>Market</th><th>Mode</th><th>Enabled</th><th>API Key</th></tr></thead>
      <tbody id="exchanges"></tbody>
    </table>
  </div>

  <div class="card">
    <h2>AI Provider Settings</h2>
    <div class="grid">
      <div>
        <label>Enable OpenAI</label>
        <select id="openai_enabled"><option value="false">Disabled</option><option value="true">Enabled</option></select>
        <label>OpenAI API Key</label><input id="openai_api_key" placeholder="sk-...">
      </div>
      <div>
        <label>Enable Claude</label>
        <select id="claude_enabled"><option value="false">Disabled</option><option value="true">Enabled</option></select>
        <label>Anthropic API Key</label><input id="anthropic_api_key" placeholder="sk-ant-...">
      </div>
    </div>
    <button onclick="saveAI()">Save AI Settings</button>
  </div>

  <div class="card">
    <h2>System Response</h2>
    <pre id="response">Ready.</pre>
  </div>
</div>

<script>
async function j(url, opts={}){ const r = await fetch(url, opts); return await r.json(); }
function show(x){ document.getElementById("response").innerText = JSON.stringify(x,null,2); }

async function load(){
  const status = await j("/api/admin/status");
  document.getElementById("botStatus").innerText = status.running ? "RUNNING" : "STOPPED";
  document.getElementById("botStatus").className = status.running ? "good" : "bad";
  document.getElementById("botExchange").innerText = status.env_exchange;
  document.getElementById("dryRun").innerText = status.dry_run;

  const exchanges = await j("/api/admin/exchanges");
  document.getElementById("exchanges").innerHTML = exchanges.map(e => `
    <tr><td>${e.id}</td><td>${e.exchange}</td><td>${e.label}</td><td>${e.market_type}</td><td>${e.mode}</td><td>${e.enabled}</td><td>${e.api_key || ""}</td></tr>
  `).join("");

  const ai = await j("/api/admin/ai");
  document.getElementById("openai_enabled").value = ai.openai_enabled || "false";
  document.getElementById("claude_enabled").value = ai.claude_enabled || "false";
}

async function botStart(){ show(await j("/api/admin/bot/start", {method:"POST"})); await load(); }
async function botStop(){ show(await j("/api/admin/bot/stop", {method:"POST"})); await load(); }

async function saveRisk(){
  const payload = {
    max_risk_per_trade: document.getElementById("max_risk_per_trade").value,
    max_daily_loss: document.getElementById("max_daily_loss").value,
    max_weekly_loss: document.getElementById("max_weekly_loss").value,
    max_concurrent_trades: document.getElementById("max_concurrent_trades").value,
    max_leverage: document.getElementById("max_leverage").value,
    preferred_pairs: document.getElementById("preferred_pairs").value
  };
  show(await j("/api/admin/risk", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)}));
}

async function saveExchange(){
  const payload = {
    exchange: document.getElementById("exchange").value,
    label: document.getElementById("exchange_label").value,
    market_type: document.getElementById("market_type").value,
    mode: document.getElementById("mode").value,
    enabled: true,
    api_key: document.getElementById("api_key").value,
    api_secret: document.getElementById("api_secret").value,
    api_password: document.getElementById("api_password").value
  };
  show(await j("/api/admin/exchanges", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)}));
  document.getElementById("api_key").value="";
  document.getElementById("api_secret").value="";
  document.getElementById("api_password").value="";
  await load();
}

async function saveAI(){
  const payload = {
    openai_enabled: document.getElementById("openai_enabled").value,
    claude_enabled: document.getElementById("claude_enabled").value,
    openai_api_key: document.getElementById("openai_api_key").value,
    anthropic_api_key: document.getElementById("anthropic_api_key").value
  };
  show(await j("/api/admin/ai", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)}));
  document.getElementById("openai_api_key").value="";
  document.getElementById("anthropic_api_key").value="";
  await load();
}
load();
</script>
</body>
</html>
"""

def admin_page():
    return HTMLResponse(ADMIN_HTML)
