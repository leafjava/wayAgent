"""项目存储单元测试。"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.projects.store import ProjectStore, Project, Document, Version, hash_project_payload


class TestProjectStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(os.path.join(self.tmp.name, "p.sqlite3"))

    def tearDown(self):
        import gc, shutil
        gc.collect()
        try:
            self.store._conn().close()
        except Exception:
            pass
        try:
            shutil.rmtree(self.tmp.name, ignore_errors=True)
        except Exception:
            pass

    def test_project_crud(self):
        self.store.upsert_project(Project("p1", "Test", "TST", "sector", "desc"))
        ps = self.store.list_projects()
        self.assertEqual(len(ps), 1)
        self.assertEqual(ps[0]["projectId"], "p1")
        self.assertEqual(ps[0]["name"], "Test")
        self.assertEqual(self.store.get_project("p1")["symbol"], "TST")

    def test_document_crud(self):
        self.store.upsert_project(Project("p1", "Test", "TST", "x", "d"))
        self.store.add_document(Document("", "p1", "whitepaper", "T1", "content", "internal", "", "official"))
        docs = self.store.list_documents("p1")
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["docType"], "whitepaper")

    def test_version_crud(self):
        self.store.upsert_project(Project("p1", "Test", "TST", "x", "d"))
        self.store.add_version(Version("", "p1", "whitepaper", "v1.0", "0x1", "content", None, {}))
        v = self.store.latest_version("p1", "whitepaper")
        self.assertIsNotNone(v)
        self.assertEqual(v["version"], "v1.0")

    def test_risk_state(self):
        self.store.upsert_risk("p1", "HEALTHY", 80.0, {"x": 1})
        rs = self.store.get_risk("p1")
        self.assertEqual(rs["status"], "HEALTHY")
        self.assertEqual(rs["score"], 80.0)

    def test_watchlist(self):
        wid = self.store.add_watch("p1", "note", 100.0)
        items = self.store.list_watch()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["project_id"], "p1")
        self.assertTrue(self.store.remove_watch(wid))

    def test_consent(self):
        c = self.store.add_consent("p1", "uniswap", "buy", "user1", "0xabc")
        self.assertIn("consentId", c)
        self.store.update_consent_chain(c["consentId"], "0xtx", "confirmed")
        items = self.store.list_consents("p1")
        self.assertEqual(items[0]["chain_status"], "confirmed")

    def test_hash_deterministic(self):
        p = {"a": 1, "b": [1, 2]}
        self.assertEqual(hash_project_payload(p), hash_project_payload({"b": [1, 2], "a": 1}))


if __name__ == "__main__":
    unittest.main()
