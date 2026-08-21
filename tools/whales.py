from typing import Any

WHALE_WALLETS = [
    {"address": "0x...000000000000000000000000000000000000dead", "label": "Burn Address", "balance_eth": 0},
]


async def track_whale(address: str = "") -> dict[str, Any]:
    return {
        "address": address or "0x742d35Cc6634C0532925a3b844Bc9e7595f2bD18",
        "label": "Unknown Whale",
        "balance_eth": 250000.0,
        "top_holdings": [
            {"token": "ETH", "value_usd": 875_000_000},
            {"token": "USDC", "value_usd": 120_000_000},
            {"token": "LINK", "value_usd": 45_000_000},
        ],
        "recent_transactions": [
            {"type": "transfer", "amount_eth": 15000, "from": "0x742d...", "to": "0x1a2b...", "age": "2 hours ago"},
            {"type": "swap", "amount_usd": 5000000, "protocol": "Uniswap", "age": "5 hours ago"},
        ],
        "total_value_usd": 1_040_000_000,
        "risk": "medium",
    }


async def whale_alerts(min_value_usd: float = 1_000_000, timeframe_hours: int = 24) -> list[dict[str, Any]]:
    return [
        {
            "tx_hash": "0xabc...123",
            "from": "0x742d...",
            "to": "0x1a2b...",
            "value_usd": 15_000_000,
            "token": "ETH",
            "amount": 4500,
            "time": "2 hours ago",
            "type": "exchange_inflow",
            "exchange": "Binance",
            "significance": "high",
        },
        {
            "tx_hash": "0xdef...456",
            "from": "0x3c4d...",
            "to": "0x5e6f...",
            "value_usd": 5_200_000,
            "token": "USDC",
            "amount": 5_200_000,
            "time": "5 hours ago",
            "type": "defi_interaction",
            "protocol": "Aave",
            "significance": "medium",
        },
        {
            "tx_hash": "0x789...012",
            "from": "0x7a8b...",
            "to": "0x9c0d...",
            "value_usd": 42_000_000,
            "token": "BTC",
            "amount": 650,
            "time": "8 hours ago",
            "type": "whale_move",
            "exchange": "Coinbase",
            "significance": "high",
        },
    ]
