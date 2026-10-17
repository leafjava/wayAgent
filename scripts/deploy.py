"""部署 DisclosureRegistry 到 Monad Testnet。"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from web3 import Web3
from eth_account import Account


CONTRACT_SOURCE = ROOT / "contracts" / "DisclosureRegistry.sol"
CONTRACT_RUNTIME = ROOT / ".chain_runtime" / "contract.json"


def load_solc_if_available():
    try:
        from solcx import compile_source
        return compile_source
    except Exception:
        return None


def compile_with_solc() -> dict:
    from solcx import compile_source, install_solc, set_solc_version
    try:
        set_solc_version("0.8.20")
    except Exception:
        install_solc("0.8.20")
        set_solc_version("0.8.20")
    out = compile_source(CONTRACT_SOURCE.read_text(encoding="utf-8"),
                          output_values=["abi", "bin"], solc_version="0.8.20")
    cid = next(k for k in out if k.endswith(":DisclosureRegistry"))
    return out[cid]


def main() -> int:
    rpc = os.getenv("MONAD_RPC", "https://testnet-rpc.monad.xyz")
    chain_id = int(os.getenv("MONAD_CHAIN_ID", "10143"))
    pk = os.getenv("PRIVATE_KEY")
    if not pk:
        print("PRIVATE_KEY 未设置。演示可用 mock 模式：TOKENTRUTH_CHAIN_MODE=mock npm run dev")
        return 1
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 20}))
    if not w3.is_connected():
        return 2
    account = Account.from_key(pk)
    print(f"部署者 {account.address}, balance {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} MON")
    compile_source = load_solc_if_available()
    if compile_source is None:
        print("未安装 solcx。请先 pip install py-solc-x")
        return 3
    info = compile_with_solc()
    fallback = ROOT / ".chain_runtime" / "build.json"
    fallback.parent.mkdir(parents=True, exist_ok=True)
    fallback.write_text(json.dumps({"abi": info["abi"], "bin": info["bin"]}, ensure_ascii=False, indent=2), encoding="utf-8")
    contract = w3.eth.contract(abi=info["abi"], bytecode=info["bin"])
    tx = contract.constructor().build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "chainId": chain_id,
        "gas": 2_000_000,
        "gasPrice": w3.to_wei("1", "gwei"),
    })
    signed = w3.eth.account.sign_transaction(tx, pk)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction).hex()
    print(f"部署 tx: {tx_hash}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    if receipt.status != 1:
        return 4
    address = receipt.contractAddress
    print(f"DisclosureRegistry deployed: {address} (block {receipt.blockNumber})")
    payload = {
        "address": address, "deployer": account.address, "txHash": tx_hash,
        "blockNumber": int(receipt.blockNumber), "chainId": chain_id,
        "rpc": rpc, "explorer": f"https://testnet.monadexplorer.com/address/{address}",
        "abi": info["abi"],
    }
    CONTRACT_RUNTIME.parent.mkdir(parents=True, exist_ok=True)
    CONTRACT_RUNTIME.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已写入 {CONTRACT_RUNTIME}")
    print(f"提示：设置环境变量 DISCLOSURE_REGISTRY_ADDRESS={address} 后启动 web_app。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
