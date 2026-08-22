import json
from datetime import datetime, timezone
from typing import Any

from web3 import Web3

CHAIN_RPCS = {
    "ethereum": "https://eth.llamarpc.com",
    "bsc": "https://bsc-dataseed1.binance.org",
    "polygon": "https://polygon-rpc.com",
    "arbitrum": "https://arb1.arbitrum.io/rpc",
    "optimism": "https://mainnet.optimism.io",
    "base": "https://mainnet.base.org",
}

ERC20_ABI = json.loads('[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]')


class Web3Client:
    def __init__(self, chain: str = "ethereum"):
        self.chain = chain
        rpc = CHAIN_RPCS.get(chain, CHAIN_RPCS["ethereum"])
        self.w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 30}))

    @property
    def is_connected(self) -> bool:
        return self.w3.is_connected()

    def get_block(self, block_identifier: int | str = "latest") -> dict[str, Any]:
        block = self.w3.eth.get_block(block_identifier, full_transactions=False)
        return {
            "number": block["number"],
            "hash": block["hash"].hex(),
            "timestamp": block["timestamp"],
            "datetime": datetime.fromtimestamp(block["timestamp"], tz=timezone.utc).isoformat(),
            "transactions": len(block["transactions"]),
            "gas_used": block["gasUsed"],
            "gas_limit": block["gasLimit"],
            "base_fee": block.get("baseFeePerGas", 0),
        }

    def get_gas_price(self) -> dict[str, Any]:
        gwei = self.w3.eth.gas_price / 1e9
        return {
            "gas_price_gwei": round(gwei, 2),
            "chain": self.chain,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_balance(self, address: str) -> dict[str, Any]:
        checksum = self.w3.to_checksum_address(address)
        balance_wei = self.w3.eth.get_balance(checksum)
        balance_eth = self.w3.from_wei(balance_wei, "ether")
        return {
            "address": address,
            "balance_eth": round(float(balance_eth), 6),
            "balance_wei": balance_wei,
            "chain": self.chain,
        }

    def get_token_balance(self, token_address: str, wallet_address: str) -> dict[str, Any]:
        token = self.w3.eth.contract(address=self.w3.to_checksum_address(token_address), abi=ERC20_ABI)
        wallet = self.w3.to_checksum_address(wallet_address)
        try:
            balance = token.functions.balanceOf(wallet).call()
            decimals = token.functions.decimals().call()
            symbol = token.functions.symbol().call()
            return {
                "token": symbol,
                "token_address": token_address,
                "balance_raw": balance,
                "balance": balance / (10 ** decimals),
                "decimals": decimals,
            }
        except Exception as e:
            return {"error": str(e), "token_address": token_address}

    def estimate_gas(self, from_addr: str, to_addr: str, value_eth: float = 0) -> dict[str, Any]:
        tx = {
            "from": self.w3.to_checksum_address(from_addr),
            "to": self.w3.to_checksum_address(to_addr),
            "value": self.w3.to_wei(value_eth, "ether"),
        }
        try:
            gas = self.w3.eth.estimate_gas(tx)
            gas_price = self.w3.eth.gas_price
            return {
                "gas_units": gas,
                "gas_price_gwei": round(gas_price / 1e9, 2),
                "total_cost_eth": round(float(gas * gas_price / 1e18), 6),
                "chain": self.chain,
            }
        except Exception as e:
            return {"error": str(e)}


def get_client(chain: str = "ethereum") -> Web3Client:
    return Web3Client(chain)
