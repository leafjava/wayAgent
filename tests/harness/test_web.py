"""Flask 路由契约测试。"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

os.environ["TOKENTRUTH_CHAIN_MODE"] = "mock"

from tools.harness_support import load_harness_app  # noqa: E402


class TestRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.web_app = load_harness_app(Path(cls.tmp.name))
        cls.client = cls.web_app.app.test_client()

    @classmethod
    def tearDownClass(cls):
        import shutil
        try:
            shutil.rmtree(cls.tmp.name, ignore_errors=True)
        except Exception:
            pass

    def test_pages(self):
        for route in ["/", "/chat", "/analyze", "/track", "/company", "/edit_doc", "/proof"]:
            r = self.client.get(route)
            self.assertEqual(r.status_code, 200, f"{route}")

    def test_project_detail(self):
        # 确保种子项目已灌入
        self.client.post("/api/seed")
        r = self.client.get("/project/demo-mon")
        self.assertEqual(r.status_code, 200)

    def test_qa(self):
        r = self.client.post("/api/qa", json={"projectId": "demo-mon", "question": "这家公司靠什么赚钱？"})
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertIn("conclusion", d)
        self.assertIn("citations", d)

    def test_analyze(self):
        r = self.client.get("/api/analyze?projectId=demo-mon")
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertIn("fundamentals", d)

    def test_risk(self):
        r = self.client.get("/api/risk?projectId=demo-mon")
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertIn("status", d)

    def test_chain_status(self):
        r = self.client.get("/api/chain/status")
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertIn("contractAddress", d)


if __name__ == "__main__":
    unittest.main()
