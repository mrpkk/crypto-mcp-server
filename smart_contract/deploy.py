#!/usr/bin/env python3
"""Deploy YieldOptimizer smart contract to any EVM chain."""

import json
import os
from pathlib import Path

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

CONTRACT_PATH = Path(__file__).parent / "YieldOptimizer.sol"
DEPLOYED_PATH = Path(__file__).parent / "deployed.json"

CHAINS = {
    "ethereum": {"rpc": "https://eth.llamarpc.com", "scan": "https://etherscan.io", "explorer_api": "https://api.etherscan.io"},
    "bsc": {"rpc": "https://bsc-dataseed1.binance.org", "scan": "https://bscscan.com", "explorer_api": "https://api.bscscan.com"},
    "polygon": {"rpc": "https://polygon-rpc.com", "scan": "https://polygonscan.com", "explorer_api": "https://api.polygonscan.com"},
    "arbitrum": {"rpc": "https://arb1.arbitrum.io/rpc", "scan": "https://arbiscan.io", "explorer_api": "https://api.arbiscan.io"},
    "base": {"rpc": "https://mainnet.base.org", "scan": "https://basescan.org", "explorer_api": "https://api.basescan.org"},
    "sepolia": {"rpc": "https://rpc.sepolia.org", "scan": "https://sepolia.etherscan.io", "explorer_api": "https://api-sepolia.etherscan.io"},
}


def compile_contract() -> tuple:
    try:
        from solcx import compile_files, install_solc
    except ImportError:
        print("Install solcx: pip install py-solc-x")
        raise

    install_solc("0.8.28", show_progress=False)
    compiled = compile_files(
        [str(CONTRACT_PATH)],
        solc_version="0.8.28",
        output_values=["abi", "bin"],
    )
    contract = compiled[f"{CONTRACT_PATH}:YieldOptimizer"]
    return contract["abi"], contract["bin"]


def deploy(chain: str = "sepolia", private_key: str = "") -> dict:
    if chain not in CHAINS:
        print(f"Unsupported chain: {chain}. Options: {', '.join(CHAINS.keys())}")
        return {}

    pk = private_key or os.getenv("DEPLOYER_PRIVATE_KEY", "")
    if not pk:
        print("Set DEPLOYER_PRIVATE_KEY env var or pass --private-key")
        return {}

    abi, bytecode = compile_contract()
    chain_info = CHAINS[chain]
    w3 = Web3(Web3.HTTPProvider(chain_info["rpc"], request_kwargs={"timeout": 60}))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    account = w3.eth.account.from_key(pk)
    print(f"Deploying from: {account.address} (balance: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} ETH)")

    YieldOptimizer = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx = YieldOptimizer.constructor(account.address).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 2_000_000,
        "gasPrice": w3.eth.gas_price,
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    result = {
        "chain": chain,
        "address": receipt["contractAddress"],
        "tx_hash": receipt["transactionHash"].hex(),
        "block": receipt["blockNumber"],
        "deployer": account.address,
        "scan_url": f"{chain_info['scan']}/address/{receipt['contractAddress']}",
    }

    deployments = []
    if DEPLOYED_PATH.exists():
        deployments = json.loads(DEPLOYED_PATH.read_text())
    deployments.append(result)
    DEPLOYED_PATH.write_text(json.dumps(deployments, indent=2))

    print(f"Deployed: {result['scan_url']}")
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Deploy YieldOptimizer")
    parser.add_argument("--chain", default="sepolia", help="Chain to deploy to")
    parser.add_argument("--private-key", help="Deployer private key")
    args = parser.parse_args()
    deploy(args.chain, args.private_key)
