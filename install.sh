#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Installing Crypto MCP Server..."

# Check Python
PYTHON=$(command -v python3 || command -v python)
if [ -z "$PYTHON" ]; then
    echo "❌ Python 3 required. Install: sudo apt install python3 python3-pip python3-venv"
    exit 1
fi

# Create venv
if [ ! -d "venv" ]; then
    $PYTHON -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate and install
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Setup config
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
    echo "⚠️  Created .env from example — edit it with your API keys"
fi

echo ""
echo "✅ Crypto MCP Server installed!"
echo ""
echo "📋 Quick start:"
echo "  1. Edit .env with your Mistral API key"
echo "  2. Run: python main.py"
echo "  3. Connect from Claude/Cursor:"
echo "     claude mcp add crypto -e \"python $(pwd)/main.py\""
echo ""
echo "🔧 16 tools available: price, yields, signals, whales, gas, AI analysis + smart contract"
