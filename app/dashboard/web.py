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
