#!/usr/bin/env python3
"""Crypto MCP Server — REST API wrapper with Swagger UI."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from ai.analyst import CryptoAnalyst
from config import settings
from tools.analysis import analyze_token, portfolio_health
from tools.gas import estimate_tx_cost, gas_tracker
from tools.price import compare_prices, get_price, get_top_crypto
from tools.signal import technical_indicators
from tools.whales import track_whale, whale_alerts
from tools.yield_tools import get_yields

analyst = CryptoAnalyst(api_key=settings.github_token)
analyst.fallback_key = settings.mistral_api_key

app = FastAPI(
    title="💰 Crypto & DeFi Intelligence Server",
    description=(
        "**14 инструментов для крипто-аналитики**\n\n"
        "**Возможности:**\n"
        "• 💰 Real-time цены с бирж (Binance, Coinbase, Kraken, Bybit)\n"
        "• ⚖️ Сравнение цен между биржами (арбитраж)\n"
        "• 📊 Технический анализ (RSI, MACD, скользящие средние)\n"
        "• 📈 DeFi Yields (Aave, Compound, Lido, Curve, и др.)\n"
        "• ⛽ Gas tracker (Ethereum, BSC, Polygon, Arbitrum, Optimism, Base)\n"
        "• 🐋 Whale alerts (крупные транзакции)\n"
        "• 🧠 AI сентимент и торговые сигналы через Mistral AI\n"
        "• 🔍 Глубокий анализ токенов\n\n"
        "🔌 REST API + MCP Protocol + Swagger UI"
    ),
    version="1.4.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Crypto & DeFi Intelligence Server</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:#03080e; color:#e6edf3; overflow-x:hidden; }
  .hero { text-align:center; padding:70px 24px 50px; background:radial-gradient(ellipse at 50% 0%, rgba(56,139,253,0.15) 0%, transparent 60%); }
  .hero h1 { font-size:2.8rem; font-weight:700; background:linear-gradient(135deg,#f0f6fc,#58a6ff,#a371f7); -webkit-background-clip:text; -webkit-text-fill-color:transparent; letter-spacing:-1px; }
  .hero p { color:#8b949e; margin-top:10px; font-size:1.1rem; max-width:500px; margin-left:auto; margin-right:auto; }
  .hero .badge { display:inline-block; background:rgba(56,139,253,0.1); color:#58a6ff; padding:4px 16px; border-radius:100px; font-size:0.8rem; border:1px solid rgba(56,139,253,0.15); margin-top:14px; }
  .section-title { max-width:1200px; margin:40px auto 16px; padding:0 24px; font-size:1.2rem; font-weight:600; color:#f0f6fc; }
  .section-sub { max-width:1200px; margin:0 auto 24px; padding:0 24px; color:#8b949e; font-size:0.9rem; }

  .grid { max-width:1200px; margin:0 auto; padding:0 24px 40px; display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:16px; }
  .tool-card { background:linear-gradient(135deg,#0d1117,#161b22); border:1px solid #21262d; border-radius:16px; padding:20px; cursor:pointer; transition:all 0.25s; }
  .tool-card:hover { border-color:#58a6ff; transform:translateY(-3px); box-shadow:0 12px 40px rgba(0,0,0,0.4); }
  .card-header { display:flex; align-items:center; gap:10px; margin-bottom:8px; }
  .card-icon { font-size:1.5rem; }
  .tool-card h3 { font-size:1rem; font-weight:600; }
  .tool-card p { color:#8b949e; font-size:0.85rem; line-height:1.5; }
  .card-result { background:#0d1117; border:1px solid #21262d; border-radius:8px; padding:10px; margin-top:10px; font-family:monospace; font-size:0.72rem; line-height:1.5; color:#8b949e; max-height:220px; overflow-y:auto; white-space:pre-wrap; word-break:break-all; transition:all 0.2s; }
  .card-result td { padding:3px 8px; font-family:monospace; font-size:0.75rem; }
  .card-result table { width:100%; border-collapse:collapse; }
  .card-result tr { border-bottom:1px solid #21262d; }
  .card-result tr:last-child { border:none; }
  .g { color:#3fb950; } .r { color:#f85149; } .y { color:#d29922; } .b { color:#58a6ff; } .v { color:#a371f7; }
  .card-action { display:inline-block; margin-top:12px; color:#58a6ff; font-size:0.8rem; font-weight:600; }
  .loading { opacity:0.4; pointer-events:none; }
  .error { color:#f85149; }

  .features { max-width:1200px; margin:0 auto; padding:40px 24px; display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:20px; background:#0a0e14; border-radius:20px; }
  .feature-item { text-align:center; padding:24px; }
  .feature-icon { font-size:2rem; margin-bottom:8px; }
  .feature-item h4 { font-size:0.95rem; margin-bottom:6px; color:#f0f6fc; }
  .feature-item p { font-size:0.8rem; color:#8b949e; line-height:1.5; }

  .includes { max-width:1200px; margin:40px auto; padding:40px 24px; }
  .includes-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:16px; margin-top:24px; }
  .include-item { background:#0d1117; border:1px solid #21262d; border-radius:12px; padding:20px; }
  .include-item h4 { font-size:0.95rem; margin-bottom:6px; color:#f0f6fc; }
  .include-item h4 span { margin-right:8px; }
  .include-item p { font-size:0.8rem; color:#8b949e; line-height:1.5; }

  .cta { text-align:center; padding:60px 24px; background:radial-gradient(ellipse at center, rgba(56,139,253,0.08) 0%, transparent 70%); }
  .cta h2 { font-size:1.8rem; margin-bottom:8px; }
  .cta p { color:#8b949e; margin-bottom:20px; }
  .btn { display:inline-block; padding:12px 28px; background:linear-gradient(135deg,#238636,#2ea043); color:#fff; border-radius:12px; text-decoration:none; font-weight:600; transition:all 0.25s; }
  .btn:hover { transform:translateY(-2px); box-shadow:0 8px 30px rgba(46,160,67,0.3); }
  footer { text-align:center; padding:30px; color:#484f58; font-size:0.8rem; }
  a { color:#58a6ff; text-decoration:none; }
  a:hover { text-decoration:underline; }
</style>
</head>
<body>
<div class="hero">
  <h1>Crypto & DeFi Intelligence</h1>
  <p>14 real-time tools for prices, yields, technical analysis, whales, gas, and AI market insights.</p>
  <div class="badge">v1.3.0 · REST API + MCP Server</div>
</div>

<div class="section-title">📦 What You Get</div>
<div class="section-sub">Everything you need to plug crypto intelligence into any AI agent, dashboard, or trading bot.</div>
<div class="includes-grid" style="max-width:1200px;margin:0 auto 40px;padding:0 24px;display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;">
  <div class="include-item"><h4><span>🔌</span>MCP Protocol</h4><p>Drop-in integration with Claude, Cursor, Windsurf, and any MCP-compatible AI assistant. One config line.</p></div>
  <div class="include-item"><h4><span>🌐</span>REST API</h4><p>Full HTTP API with Swagger docs. Use from Python, JS, curl — any language. CORS enabled.</p></div>
  <div class="include-item"><h4><span>📊</span>14 Tools</h4><p>Prices, technical analysis, DeFi yields, gas tracker, whale alerts, token analysis, AI sentiment, portfolio health, and more.</p></div>
  <div class="include-item"><h4><span>🤖</span>AI Analysis</h4><p>Mistral AI-powered market sentiment, trading signals, and yield assessments. Natural language insights.</p></div>
  <div class="include-item"><h4><span>⛓️</span>Multi-Chain</h4><p>Ethereum, BSC, Polygon, Arbitrum, Optimism, Base — gas prices and DeFi data across all major EVM chains.</p></div>
  <div class="include-item"><h4><span>🐋</span>Real-Time Data</h4><p>Live prices from exchanges, whale transaction monitoring, gas fees, and DeFi yield rates.</p></div>
  <div class="include-item"><h4><span>📁</span>Source Code</h4><p>Full Python source. MIT license. Modify, extend, deploy on your infrastructure.</p></div>
  <div class="include-item"><h4><span>🐳</span>Docker</h4><p>One-command deployment with Docker Compose. Includes health checks and monitoring.</p></div>
</div>

<div class="section-title">🛠️ Tools</div>
<div class="section-sub">Click any card to fetch live data from the API.</div>
<div class="grid" id="toolGrid"></div>

<div class="cta">
  <h2>Need a custom version?</h2>
  <p>Extended data sources, custom integrations, white-label deployment.</p>
  <a href="https://t.me/mrpkk" class="btn">📩 Contact on Telegram</a>
</div>
<footer>Crypto & DeFi Intelligence Server · <a href="/docs">API Docs</a> · <a href="https://t.me/mrpkk">@mrpkk</a></footer>

<script>
const TOOLS = [
  {id:"price",icon:"💰",title:"Price",desc:"Real-time crypto prices from major exchanges",url:"/price/BTC/USDT",render:renderPrice},
  {id:"top",icon:"🏆",title:"Top Crypto",desc:"Top cryptocurrencies by market metrics",url:"/top",render:renderTable},
  {id:"ta",icon:"📊",title:"Technical Analysis",desc:"RSI, MACD, moving averages for any pair",url:"/technical/BTC/USDT",render:renderBlock},
  {id:"yields",icon:"📈",title:"DeFi Yields",desc:"Best yield opportunities across protocols",url:"/yields",render:renderYields},
  {id:"gas",icon:"⛽",title:"Gas Tracker",desc:"EVM gas prices with recommendations",url:"/gas/ethereum",render:renderGas},
  {id:"whales",icon:"🐋",title:"Whale Alerts",desc:"Large transactions and whale movements",url:"/whales",render:renderWhales},
  {id:"analyze",icon:"🔍",title:"Token Analysis",desc:"Deep risk assessment and market positioning",url:"/analyze/BTC",render:renderAnalyze},
  {id:"compare",icon:"⚖️",title:"Compare Prices",desc:"Cross-exchange arbitrage scanner",url:"/price/compare/BTC/USDT",render:renderTable},
  {id:"sentiment",icon:"🧠",title:"AI Sentiment",desc:"AI-powered market sentiment analysis",url:"/sentiment/BTC",render:renderBlock},
  {id:"signal",icon:"📶",title:"Trading Signal",desc:"AI-generated trading signals",url:"/signal/BTC/USDT",render:renderBlock},
  {id:"tx",icon:"💸",title:"TX Cost Estimator",desc:"Transaction cost in USD across speeds",url:"/estimate-tx",render:renderTx},
  {id:"portfolio",icon:"📋",title:"Portfolio Health",desc:"Diversity analysis and allocation suggestions",url:"/portfolio",render:renderBlock},
];

function renderPrice(d) {
  if(!d || d.error) return '<div class="r">Error: '+(d?.error||'no data')+'</div>';
  const ch = d.change_24h||0;
  const cls = ch>=0 ? 'g' : 'r';
  const price = d.price || d.price_usd || 0;
  const vol = d.volume_24h || d.volume_24h_usd || 0;
  const cap = d.market_cap || d.market_cap_usd || 0;
  return `<table>
    <tr><td>Symbol</td><td class="b">${d.symbol||'?'}</td></tr>
    <tr><td>Price</td><td class="b" style="font-size:1.1rem">$${price.toLocaleString()}</td></tr>
    <tr><td>24h Change</td><td class="${cls}">${ch>=0?'+':''}${ch.toFixed(2)}%</td></tr>
    <tr><td>24h Volume</td><td>$${vol.toLocaleString()}</td></tr>
    <tr><td>Market Cap</td><td>$${cap.toLocaleString()}</td></tr>
  </table>`;
}
function renderTable(d) {
  if(!Array.isArray(d)) return '<div class="r">No data</div>';
  return '<table>'+d.slice(0,8).map(r=>{
    const ch = r.change_24h;
    const cls = ch!==null&&ch!==undefined ? (ch>=0?'g':'r') : 'y';
    const chStr = ch!==null&&ch!==undefined ? (ch>=0?'+':'')+ch.toFixed(2)+'%' : 'N/A';
    return `<tr><td>${r.symbol||'?'}</td><td class="b">$${(r.price_usd||0).toLocaleString()}</td><td class="${cls}">${chStr}</td><td>${abbr(r.volume_24h_usd||0)}</td></tr>`;
  }).join('')+'</table>';
}
function renderYields(d) {
  if(!Array.isArray(d)) return '<div class="r">No data</div>';
  return '<table>'+d.slice(0,6).map(r=>
    `<tr><td class="b">${r.protocol}</td><td>${r.pool}</td><td class="g">${r.apy}%</td><td>${r.chain}</td></tr>`
  ).join('')+'</table>';
}
function renderGas(d) {
  if(!d||!d.gas_levels) return '<div class="r">No data</div>';
  const g = d.gas_levels;
  return `<table>
    <tr><td>Slow</td><td class="y">${g.slow.gwei} Gwei</td><td>${g.slow.est_time}</td></tr>
    <tr><td>Standard</td><td class="b">${g.standard.gwei} Gwei</td><td>${g.standard.est_time}</td></tr>
    <tr><td>Fast</td><td class="g">${g.fast.gwei} Gwei</td><td>${g.fast.est_time}</td></tr>
    <tr><td>🚀 Urgent</td><td class="r">${g.urgent.gwei} Gwei</td><td>${g.urgent.est_time}</td></tr>
  </table>`;
}
function renderWhales(d) {
  if(!Array.isArray(d)) return '<div class="r">No data</div>';
  return '<table>'+d.slice(0,4).map(r=>
    `<tr><td class="${r.significance==='high'?'r':'y'}">$${abbr(r.value_usd)}</td><td>${r.token}</td><td style="font-size:0.65rem">${r.type}</td><td style="font-size:0.65rem;color:#8b949e">${r.time}</td></tr>`
  ).join('')+'</table>';
}
function renderAnalyze(d) {
  if(!d||!d.risk_assessment) return '<div class="r">No data</div>';
  const risk = d.risk_assessment;
  const riskCls = risk.score>=80 ? 'g' : (risk.score>=50 ? 'y' : 'r');
  return `<table>
    <tr><td>Price</td><td class="b">$${(d.price_usd||0).toLocaleString()}</td></tr>
    <tr><td>Market Cap</td><td>$${abbr(d.market_cap||0)}</td></tr>
    <tr><td>Dominance</td><td class="b">${d.market_dominance||'?'}%</td></tr>
    <tr><td>Risk Score</td><td class="${riskCls}">${risk.score}/100 (${risk.level})</td></tr>
    <tr><td>ATH</td><td class="y">$${(d.all_time_high||0).toLocaleString()}</td></tr>
    <tr><td>From ATH</td><td class="r">${d.from_ath_pct||0}%</td></tr>
  </table>`;
}
function renderTx(d) {
  if(!d||!d.operation_examples) return '<div class="r">No data</div>';
  return `<table>
    <tr><td>ETH Transfer</td><td class="b">$${d.operation_examples.eth_transfer_21k}</td></tr>
    <tr><td>ERC-20 Transfer</td><td class="b">$${d.operation_examples.erc20_transfer_65k}</td></tr>
    <tr><td>Swap</td><td class="b">$${d.operation_examples.swap_150k}</td></tr>
    <tr><td>Complex TX</td><td class="b">$${d.operation_examples.complex_tx_300k}</td></tr>
  </table>`;
}
function renderBlock(d) {
  if(!d) return '<div class="r">No data</div>';
  if(d.error) return '<div class="r">Error: '+d.error+'</div>';
  const pairs = Object.entries(d).slice(0,8);
  return '<table>'+pairs.map(([k,v])=>{
    let val = typeof v==='object' ? JSON.stringify(v) : v;
    if(typeof val==='number') val = val.toLocaleString();
    return `<tr><td style="color:#8b949e">${k}</td><td class="b">${String(val).slice(0,60)}</td></tr>`;
  }).join('')+'</table>';
}
function abbr(n) {
  if(n>=1e12) return (n/1e12).toFixed(1)+'T';
  if(n>=1e9) return (n/1e9).toFixed(1)+'B';
  if(n>=1e6) return (n/1e6).toFixed(1)+'M';
  if(n>=1e3) return (n/1e3).toFixed(1)+'K';
  return n.toString();
}
function init() {
  const grid = document.getElementById('toolGrid');
  grid.innerHTML = TOOLS.map(t=>`
    <div class="tool-card" onclick="callTool('${t.id}')" id="card-${t.id}">
      <div class="card-header"><span class="card-icon">${t.icon}</span><h3>${t.title}</h3></div>
      <p>${t.desc}</p>
      <div class="card-result" id="result-${t.id}">← Click to load live data</div>
      <span class="card-action">▶ Run</span>
    </div>
  `).join('');
}
async function callTool(id) {
  const t = TOOLS.find(x=>x.id===id); if(!t) return;
  const card = document.getElementById('card-'+id);
  const result = document.getElementById('result-'+id);
  card.classList.add('loading');
  result.innerHTML = '<span style="color:#8b949e">⏳ Loading...</span>';
  try {
    const res = await fetch(t.url);
    const text = await res.text();
    let data;
    try { data = JSON.parse(text); } catch { data = {raw:text}; }
    if(res.status===404||res.status===500) data = {error:'API returned '+res.status};
    result.innerHTML = '<div style="font-family:monospace;font-size:0.72rem;line-height:1.5">'+(t.render(data)||'<span class="r">render error</span>')+'</div>';
  } catch(e) {
    result.innerHTML = '<span class="r">✗ '+e.message+'</span>';
  }
  card.classList.remove('loading');
}
init();
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def root():
    return DASHBOARD_HTML


@app.get("/price/compare/{symbol:path}")
async def api_compare_prices(symbol: str = "BTC/USDT"):
    return await compare_prices(symbol=symbol)


@app.get("/price/{symbol:path}")
async def api_get_price(symbol: str = "BTC/USDT", exchange: str = "binance"):
    result = await get_price(symbol=symbol, exchange=exchange)
    # Добавляем алиасы для совместимости с дашбордом
    if isinstance(result, dict):
        if "price_usd" in result and "price" not in result:
            result["price"] = result["price_usd"]
        if "volume_24h_usd" in result and "volume_24h" not in result:
            result["volume_24h"] = result["volume_24h_usd"]
        if "market_cap" not in result and "market_cap_usd" in result:
            result["market_cap"] = result["market_cap_usd"]
    return result


@app.get("/top")
async def api_top_crypto(limit: int = 10):
    return await get_top_crypto(limit=limit)


@app.get("/yields")
async def api_yields(min_apy: float = 0, chain: str = "all", max_results: int = 20):
    return await get_yields(min_apy=min_apy, chain=chain, max_results=max_results)


@app.get("/technical/{symbol:path}")
async def api_technical(symbol: str = "BTC/USDT", price: float = 0,
                        exchange: str = "binance"):
    return await technical_indicators(symbol=symbol, price=price, exchange=exchange)


@app.get("/analyze/{symbol}")
async def api_analyze(symbol: str = "BTC", price_usd: float = 0, market_cap: float = 0):
    return await analyze_token(symbol=symbol, price_usd=price_usd, market_cap=market_cap)


@app.get("/portfolio")
async def api_portfolio():
    dummy = [
        {"symbol": "BTC", "value_usd": 50000},
        {"symbol": "ETH", "value_usd": 30000},
        {"symbol": "SOL", "value_usd": 10000},
        {"symbol": "USDC", "value_usd": 10000},
    ]
    return await portfolio_health(holdings=dummy)


@app.get("/gas/{chain}")
async def api_gas(chain: str = "ethereum"):
    return await gas_tracker(chain=chain)


@app.get("/estimate-tx")
async def api_estimate_tx(chain: str = "ethereum", gas_units: int = 21000, speed: str = "standard"):
    return await estimate_tx_cost(chain=chain, gas_units=gas_units, speed=speed)


@app.get("/sentiment/{symbol}")
async def api_sentiment(symbol: str = "BTC", price_change_24h: float = 0, volume_usd: float = 0):
    try:
        return await analyst.market_sentiment(symbol=symbol, price_change_24h=price_change_24h, volume_usd=volume_usd)
    except Exception as e:
        return {"symbol": symbol, "sentiment": "neutral", "score": 50, "reason": f"AI unavailable: {e!s}", "fallback": True}


@app.get("/signal/{symbol:path}")
async def api_signal(symbol: str = "BTC/USDT", price: float = 0, rsi: float = 50, macd: str = "neutral", volume_trend: str = "stable"):
    try:
        return await analyst.trading_signal(symbol=symbol, price=price, rsi=rsi, macd=macd, volume_trend=volume_trend)
    except Exception as e:
        return {"symbol": symbol, "signal": "hold", "confidence": 0, "reason": f"AI unavailable: {e!s}", "fallback": True}


@app.get("/whales")
async def api_whales(min_value_usd: float = 1_000_000, timeframe_hours: int = 24):
    return await whale_alerts(min_value_usd=min_value_usd, timeframe_hours=timeframe_hours)


@app.get("/whale/{address}")
async def api_track_whale(address: str):
    return await track_whale(address=address)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8006
    print(f"🚀 Crypto MCP API running on http://127.0.0.1:{port}")
    print(f"📖 Swagger: http://127.0.0.1:{port}/docs")
    uvicorn.run(app, host="127.0.0.1", port=port)
