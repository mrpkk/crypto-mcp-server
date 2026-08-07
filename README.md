# 🚀 Crypto MCP Server

**AI-powered Crypto & DeFi intelligence — 14 tools for any AI agent.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/Protocol-MCP-8A2BE2.svg)](https://modelcontextprotocol.io)
[![Open Source](https://img.shields.io/badge/Open%20Source-❤️-green.svg)](https://github.com/mrpkk/crypto-mcp-server)
[![Telegram](https://img.shields.io/badge/Author-@mrpkk-26A5E4.svg)](https://t.me/mrpkk)

Give Claude, Cursor, or any MCP-compatible agent real-time crypto superpowers: prices, yields, technical analysis, whale tracking, gas optimization, and AI-generated trading signals.

> 🆓 **Free & Open Source (MIT)** — use it, fork it, build on it. Custom integrations & deployments: [@mrpkk](https://t.me/mrpkk).

## ✨ Why This Product?

| Problem | Solution |
|---------|----------|
| AI agents are blind to crypto markets | Real-time price data from 4+ exchanges |
| DeFi yields change hourly | Live APY scanner across 100+ protocols |
| Manual TA is slow | AI-powered technical + sentiment analysis |
| Whale movements move markets | Whale wallet tracking + alerts |
| Gas fees eat profits | Multi-chain gas optimizer |
| No sellable crypto AI product | Complete MCP server — deploy in 2 minutes |

## 🧠 14 Tools

### Market Data
- **`get_price`** — Real-time price from Binance/Coinbase/Kraken
- **`compare_prices`** — Cross-exchange arbitrage scanner
- **`get_top_crypto`** — Top cryptos by volume

### DeFi Intelligence
- **`get_yields`** — Best yield opportunities across 100+ protocols
- **`yield_assessment`** — AI-powered yield + risk assessment

### Technical Analysis
- **`technical_analysis`** — RSI, MACD, MA, support/resistance
- **`trading_signal`** — AI-generated buy/sell/hold signals

### Portfolio & Risk
- **`analyze_token`** — Deep token analysis with risk score
- **`portfolio_health`** — Portfolio diversity + allocation suggestions

### On-Chain
- **`gas_tracker`** — Gas prices for 6 EVM chains
- **`estimate_tx_cost`** — Transaction cost estimator
- **`track_whale`** — Whale wallet tracking
- **`whale_alerts`** — Large transaction alerts

### AI Analysis
- **`market_sentiment`** — Mistral AI-powered sentiment analysis

## ⚡ Quick Start

```bash
# Install
git clone https://github.com/mrpkk/crypto-mcp-server.git
cd crypto-mcp-server
chmod +x install.sh && ./install.sh

# Or manually
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env — add your Mistral AI key (or it works without for basic tools)

# Run
python main.py
```

## 🔌 Connect to AI Agents

### Claude Code
```bash
claude mcp add crypto -e "python $(pwd)/main.py"
```

### Cursor
```
Settings → MCP → Add Server:
  Name: crypto
  Type: stdio
  Command: python /path/to/crypto-mcp-server/main.py
```

### VS Code (GitHub Copilot)
```
.vscode/mcp.json:
{
  "servers": {
    "crypto": {
      "type": "stdio",
      "command": "python",
      "args": ["/path/to/crypto-mcp-server/main.py"]
    }
  }
}
```

## 📦 Smart Contract

Includes `YieldOptimizer.sol` — an AI-piloted DeFi yield aggregator:

- Auto-rebalance based on AI signals
- Multi-protocol allocation
- Keeper pattern for AI agent control
- Deploy to any EVM chain

```bash
# Deploy to testnet
pip install py-solc-x
python smart_contract/deploy.py --chain sepolia
```

## 🏗 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Protocol** | Model Context Protocol (MCP) |
| **AI** | Mistral AI (OpenAI-compatible) |
| **Market Data** | CCXT (4 exchanges) |
| **DeFi Data** | DeFi Llama API |
| **On-Chain** | Web3.py (6 EVM chains) |
| **Smart Contract** | Solidity 0.8.28 |

## 💰 Monetization

| Model | How |
|-------|-----|
| **MCP Subscription** | Sell access to the MCP server ($10-50/mo) |
| **Custom Integration** | Deploy + integrate for clients ($500-2000) |
| **SaaS API** | Wrapped as REST API ($20-100/mo) |
| **AI Agent Add-on** | Bundle with Claude/Cursor tutorials |
| **Smart Contract** | Deploy YieldOptimizer for protocols |

## 📋 Requirements

- Python 3.10+
- Mistral AI key (free at console.mistral.ai) — optional for basic tools

## 🗺 Roadmap

- [ ] Real-time WebSocket price streaming
- [ ] Solana chain support
- [ ] User auth + API key management
- [ ] Web dashboard
- [ ] Strategy backtesting engine
- [ ] Telegram bot integration

---

## 🤝 Contributing

Found a bug? Want a new tool? Open an [issue](https://github.com/mrpkk/crypto-mcp-server/issues) or PR — contributions welcome.

## 📬 Contact

- Telegram: [@mrpkk](https://t.me/mrpkk)
- Custom MCP servers, deployments, integrations: [@mrpkk](https://t.me/mrpkk)

---

Built with ❤️ for the AI x Crypto future.
