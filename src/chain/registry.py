"""TokenTruth 链上存证客户端。"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from web3 import Web3
from web3.exceptions import Web3Exception


MONAD_TESTNET = {
    "rpc": os.getenv("MONAD_RPC", "https://testnet-rpc.monad.xyz"),
    "chain_id": int(os.getenv("MONAD_CHAIN_ID", "10143")),
    "explorer": os.getenv("MONAD_EXPLORER", "https://testnet.monadexplorer.com"),
}


DISCLOSURE_REGISTRY_ABI: List[Dict[str, Any]] = json.loads(
    """
[
  {"inputs":[],"name":"totalEvidence","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"bytes32","name":"evidenceHash","type":"bytes32"}],"name":"verify","outputs":[{"internalType":"bool","name":"exists","type":"bool"},{"components":[{"internalType":"bytes32","name":"evidenceHash","type":"bytes32"},{"internalType":"string","name":"evidenceId","type":"string"},{"internalType":"uint8","name":"evidenceType","type":"uint8"},{"internalType":"uint256","name":"timestamp","type":"uint256"},{"internalType":"string","name":"projectId","type":"string"},{"internalType":"string","name":"docVersion","type":"string"},{"internalType":"bytes32","name":"fromStatus","type":"bytes32"},{"internalType":"bytes32","name":"toStatus","type":"bytes32"},{"internalType":"address","name":"recorder","type":"address"},{"internalType":"uint256","name":"blockNumber","type":"uint256"}],"internalType":"struct DisclosureRegistry.Evidence","name":"rec","type":"tuple"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"string","name":"evidenceId","type":"string"}],"name":"getByEvidenceId","outputs":[{"internalType":"bool","name":"exists","type":"bool"},{"components":[{"internalType":"bytes32","name":"evidenceHash","type":"bytes32"},{"internalType":"string","name":"evidenceId","type":"string"},{"internalType":"uint8","name":"evidenceType","type":"uint8"},{"internalType":"uint256","name":"timestamp","type":"uint256"},{"internalType":"string","name":"projectId","type":"string"},{"internalType":"string","name":"docVersion","type":"string"},{"internalType":"bytes32","name":"fromStatus","type":"bytes32"},{"internalType":"bytes32","name":"toStatus","type":"bytes32"},{"internalType":"address","name":"recorder","type":"address"},{"internalType":"uint256","name":"blockNumber","type":"uint256"}],"internalType":"struct DisclosureRegistry.Evidence","name":"rec","type":"tuple"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"bytes32","name":"evidenceHash","type":"bytes32"},{"internalType":"string","name":"evidenceId","type":"string"},{"internalType":"uint8","name":"evidenceType","type":"uint8"},{"internalType":"uint256","name":"timestamp","type":"uint256"},{"internalType":"string","name":"projectId","type":"string"},{"internalType":"string","name":"docVersion","type":"string"},{"internalType":"bytes32","name":"fromStatus","type":"bytes32"},{"internalType":"bytes32","name":"toStatus","type":"bytes32"}],"name":"recordEvidence","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"}
]
"""
)


@dataclass
class ChainStatus:
    network: str
    latest_block: int
    pending_count: int
    contract_address: str
    rpc: str
    explorer: str
    mode: str


@dataclass
class TxResult:
    tx_hash: str
    block_number: int
    status: str
    error: Optional[str] = None


# 证据类型枚举映射
EVIDENCE_TYPE_MAP = {
    "PROJECT_DISCLOSURE": 0,
    "RESEARCH_REPORT": 1,
    "RISK_STATUS_CHANGE": 2,
    "INVESTOR_QA": 3,
    "CONTENT_PUBLISH": 4,
    "EXECUTION_CONSENT": 5,
}


@dataclass
class LocalMockRegistry:
    """harness 用本地模拟合约。"""

    records: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    by_id: Dict[str, str] = field(default_factory=dict)
    block_number: int = 0
    tx_counter: int = 0

    def record_evidence(
        self,
        evidence_hash: str,
        evidence_id: str,
        evidence_type: int,
        timestamp: int,
        project_id: str,
        doc_version: str,
        from_status: str,
        to_status: str,
    ) -> TxResult:
        self.tx_counter += 1
        self.block_number += 1
        # 模拟 tx hash：mock 标识 + 计数
        tx_hash = "0x" + (f"tt{self.tx_counter:06d}" + evidence_hash[6:]).ljust(64, "0")[:64]
        rec = {
            "evidenceHash": evidence_hash,
            "evidenceId": evidence_id,
            "evidenceType": evidence_type,
            "timestamp": timestamp,
            "projectId": project_id,
            "docVersion": doc_version,
            "fromStatus": from_status,
            "toStatus": to_status,
            "recorder": "0x0000000000000000000000000000000000000TTM",
            "blockNumber": self.block_number,
        }
        self.records[evidence_hash] = rec
        self.by_id[evidence_id] = evidence_hash
        return TxResult(tx_hash=tx_hash, block_number=self.block_number, status="confirmed")

    def verify(self, evidence_hash: str) -> Tuple[bool, Dict[str, Any]]:
        rec = self.records.get(evidence_hash)
        if rec is None:
            return False, {}
        return True, rec

    def get_by_evidence_id(self, evidence_id: str) -> Tuple[bool, Dict[str, Any]]:
        h = self.by_id.get(evidence_id)
        if not h:
            return False, {}
        return True, self.records[h]

    def total_evidence(self) -> int:
        return len(self.records)

    def status(self, network: str = "monad-testnet", contract_address: str = "0xMOCK000000000000000000000000000000000000") -> ChainStatus:
        return ChainStatus(
            network=network,
            latest_block=self.block_number,
            pending_count=0,
            contract_address=contract_address,
            rpc="mock://local",
            explorer=MONAD_TESTNET["explorer"],
            mode="mock",
        )


@dataclass
class ChainRegistry:
    """真实链上客户端（Web3.py）。"""

    w3: Web3
    contract_address: str
    account: Optional[Any] = None
    private_key: Optional[str] = None
    chain_id: int = 10143
    explorer: str = MONAD_TESTNET["explorer"]
    network_name: str = "monad-testnet"

    @classmethod
    def from_env(cls) -> "ChainRegistry":
        rpc = os.getenv("MONAD_RPC", MONAD_TESTNET["rpc"])
        address = os.getenv("DISCLOSURE_REGISTRY_ADDRESS", "")
        if not address:
            raise RuntimeError("DISCLOSURE_REGISTRY_ADDRESS 未设置；请先运行 scripts/deploy.py 部署合约。")
        w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 10}))
        if not w3.is_connected():
            raise RuntimeError(f"无法连接 Monad RPC: {rpc}")
        pk = os.getenv("PRIVATE_KEY")
        account = None
        if pk:
            from eth_account import Account
            account = Account.from_key(pk)
        return cls(
            w3=w3,
            contract_address=address,
            account=account,
            private_key=pk,
            chain_id=int(os.getenv("MONAD_CHAIN_ID", str(MONAD_TESTNET["chain_id"]))),
            explorer=os.getenv("MONAD_EXPLORER", MONAD_TESTNET["explorer"]),
        )

    @property
    def contract(self):
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(self.contract_address),
            abi=DISCLOSURE_REGISTRY_ABI,
        )

    def record_evidence(
        self,
        evidence_hash: str,
        evidence_id: str,
        evidence_type: int,
        timestamp: int,
        project_id: str,
        doc_version: str,
        from_status: str,
        to_status: str,
    ) -> TxResult:
        if self.account is None or self.private_key is None:
            return TxResult(tx_hash="", block_number=0, status="failed", error="missing PRIVATE_KEY")
        try:
            tx = self.contract.functions.recordEvidence(
                Web3.to_bytes(hexstr=evidence_hash),
                evidence_id,
                evidence_type,
                timestamp,
                project_id,
                doc_version,
                Web3.to_bytes(hexstr=from_status) if from_status else bytes(32),
                Web3.to_bytes(hexstr=to_status) if to_status else bytes(32),
            ).build_transaction({
                "from": self.account.address,
                "nonce": self.w3.eth.get_transaction_count(self.account.address),
                "chainId": self.chain_id,
                "gas": 400_000,
                "gasPrice": self.w3.to_wei("1", "gwei"),
            })
            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction).hex()
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            status = "confirmed" if receipt.status == 1 else "failed"
            return TxResult(tx_hash=tx_hash, block_number=int(receipt.blockNumber), status=status,
                            error=None if status == "confirmed" else "tx reverted")
        except Web3Exception as exc:
            return TxResult(tx_hash="", block_number=0, status="failed", error=str(exc))
        except Exception as exc:  # noqa: BLE001
            return TxResult(tx_hash="", block_number=0, status="failed", error=str(exc))

    def verify(self, evidence_hash: str) -> Tuple[bool, Dict[str, Any]]:
        h = evidence_hash if evidence_hash.startswith("0x") else "0x" + evidence_hash
        h_bytes = Web3.to_bytes(hexstr=h)
        exists, rec = self.contract.functions.verify(h_bytes).call()
        if not exists:
            return False, {}
        return True, {
            "evidenceHash": "0x" + rec[0].hex(),
            "evidenceId": rec[1],
            "evidenceType": int(rec[2]),
            "timestamp": int(rec[3]),
            "projectId": rec[4],
            "docVersion": rec[5],
            "fromStatus": "0x" + rec[6].hex(),
            "toStatus": "0x" + rec[7].hex(),
            "recorder": rec[8],
            "blockNumber": int(rec[9]),
        }

    def get_by_evidence_id(self, evidence_id: str) -> Tuple[bool, Dict[str, Any]]:
        exists, rec = self.contract.functions.getByEvidenceId(evidence_id).call()
        if not exists:
            return False, {}
        return True, {
            "evidenceHash": "0x" + rec[0].hex(),
            "evidenceId": rec[1],
            "evidenceType": int(rec[2]),
            "timestamp": int(rec[3]),
            "projectId": rec[4],
            "docVersion": rec[5],
            "fromStatus": "0x" + rec[6].hex(),
            "toStatus": "0x" + rec[7].hex(),
            "recorder": rec[8],
            "blockNumber": int(rec[9]),
        }

    def total_evidence(self) -> int:
        return int(self.contract.functions.totalEvidence().call())

    def status(self) -> ChainStatus:
        try:
            latest = self.w3.eth.block_number
        except Exception:  # noqa: BLE001
            latest = 0
        return ChainStatus(
            network=self.network_name,
            latest_block=latest,
            pending_count=0,
            contract_address=self.contract_address,
            rpc=self.w3.provider.endpoint_uri if hasattr(self.w3.provider, "endpoint_uri") else "",
            explorer=self.explorer,
            mode="live",
        )


def build_registry(mode: Optional[str] = None) -> Tuple[Any, str]:
    mode = mode or os.getenv("TOKENTRUTH_CHAIN_MODE", "mock")
    address = os.getenv("DISCLOSURE_REGISTRY_ADDRESS", "0xMOCK000000000000000000000000000000000000")
    if mode == "live":
        try:
            reg = ChainRegistry.from_env()
            return reg, reg.contract_address
        except Exception as exc:  # noqa: BLE001
            print(f"[chain] 切到 live 失败，降级为 mock：{exc}")
            return LocalMockRegistry(), address
    return LocalMockRegistry(), address


def evidence_type_to_int(name: str) -> int:
    return EVIDENCE_TYPE_MAP.get(name, 0)


def status_to_bytes32(status: str) -> str:
    if not status:
        return "0x" + "00" * 32
    import hashlib
    return "0x" + hashlib.sha256(status.encode("utf-8")).hexdigest()
