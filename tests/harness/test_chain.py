"""链交互 mock 单元测试。"""

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.chain.registry import LocalMockRegistry, build_registry, evidence_type_to_int, status_to_bytes32


class TestMockRegistry(unittest.TestCase):
    def test_record_and_verify(self):
        reg = LocalMockRegistry()
        tx = reg.record_evidence("0x" + "a"*64, "ev-1", 0, 1000, "p1", "v1", "", "HEALTHY")
        self.assertEqual(tx.status, "confirmed")
        self.assertTrue(tx.tx_hash.startswith("0x"))
        ok, rec = reg.verify("0x" + "a"*64)
        self.assertTrue(ok)
        self.assertEqual(rec["evidenceType"], 0)

    def test_total(self):
        reg = LocalMockRegistry()
        self.assertEqual(reg.total_evidence(), 0)
        for i in range(3):
            reg.record_evidence("0x" + f"{i:064x}", f"ev-{i}", 1, i, "p", "v", "x", "y")
        self.assertEqual(reg.total_evidence(), 3)


class TestEvidenceType(unittest.TestCase):
    def test_mapping(self):
        self.assertEqual(evidence_type_to_int("PROJECT_DISCLOSURE"), 0)
        self.assertEqual(evidence_type_to_int("RESEARCH_REPORT"), 1)
        self.assertEqual(evidence_type_to_int("RISK_STATUS_CHANGE"), 2)
        self.assertEqual(evidence_type_to_int("INVESTOR_QA"), 3)
        self.assertEqual(evidence_type_to_int("CONTENT_PUBLISH"), 4)
        self.assertEqual(evidence_type_to_int("EXECUTION_CONSENT"), 5)
        self.assertEqual(evidence_type_to_int("unknown"), 0)


class TestStatusBytes(unittest.TestCase):
    def test_conversion(self):
        self.assertEqual(len(status_to_bytes32("HEALTHY")), 66)  # 0x + 64 hex
        self.assertEqual(len(status_to_bytes32("")), 66)


class TestBuildRegistry(unittest.TestCase):
    def test_mock_mode(self):
        os.environ["TOKENTRUTH_CHAIN_MODE"] = "mock"
        reg, addr = build_registry("mock")
        self.assertIsInstance(reg, LocalMockRegistry)
        self.assertTrue(addr.startswith("0x"))


if __name__ == "__main__":
    unittest.main()
