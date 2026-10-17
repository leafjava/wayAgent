"""harness 替身：在没有真实 web3 依赖时仍能加载 web_app。"""

from __future__ import annotations

import os
import sys
import types
from pathlib import Path


# 替身 web3.eth_account
fake_web3 = types.ModuleType("web3")
fake_web3_exceptions = types.ModuleType("web3.exceptions")


class _Web3Exception(Exception):
    pass


fake_web3_exceptions.Web3Exception = _Web3Exception


class _FakeWeb3:
    @staticmethod
    def to_checksum_address(a): return a
    @staticmethod
    def to_bytes(hexstr=None, primitive=None): return bytes.fromhex((hexstr or "0x00")[2:].rjust(2, "0") or "00")
    class eth:
        @staticmethod
        def contract(**k): return None
        @staticmethod
        def block_number(): return 0
        @staticmethod
        def get_transaction_count(a): return 0
        @staticmethod
        def get_balance(a): return 0
        @staticmethod
        def wait_for_transaction_receipt(tx, timeout=60): return None
        @staticmethod
        def send_raw_transaction(raw): return b""
        @staticmethod
        def from_wei(v, u): return 0
        @staticmethod
        def to_wei(v, u): return 1
    class HTTPProvider:
        def __init__(self, *a, **k): pass
    class _ProviderProps:
        endpoint_uri = ""
    provider = _ProviderProps()
    def is_connected(self): return False


fake_web3.Web3 = _FakeWeb3
fake_account = types.ModuleType("eth_account")
fake_account.Account = types.SimpleNamespace(from_key=lambda pk: None)
sys.modules.setdefault("eth_account", fake_account)
sys.modules["web3"] = fake_web3
sys.modules["web3.exceptions"] = fake_web3_exceptions


def load_harness_app(runtime_dir: Path):
    runtime_dir = Path(runtime_dir).resolve()
    runtime_dir.mkdir(parents=True, exist_ok=True)
    os.environ["TOKENTRUTH_CHAIN_MODE"] = os.environ.get("TOKENTRUTH_CHAIN_MODE", "mock")
    sys.modules.pop("web_app", None)
    import web_app  # type: ignore  # noqa: E402
    web_app.app.config.update(TESTING=True)
    return web_app
