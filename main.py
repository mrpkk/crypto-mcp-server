#!/usr/bin/env python3
"""Crypto MCP Server — AI-powered crypto/DeFi intelligence for any AI agent.

Usage:
  # Install: pip install -r requirements.txt
  # Run:    python main.py
  # Claude: claude mcp add crypto -e "python /path/to/main.py"
  # Cursor: Add as MCP server in Cursor settings
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp_server import main

if __name__ == "__main__":
    asyncio.run(main())
