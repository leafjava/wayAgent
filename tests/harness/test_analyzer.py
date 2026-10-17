"""分析器单元测试。"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.projects.store import ProjectStore
from src.projects.seed_data import apply_seed
from src.knowledge.analyzer import Analyzer
from src.risk.status_engine import StatusEngine


class TestAnalyzer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.store = ProjectStore(os.path.join(cls.tmp.name, "tt.sqlite3"))
        apply_seed(cls.store)
        cls.analyzer = Analyzer(cls.store)

    @classmethod
    def tearDownClass(cls):
        import gc, shutil
        gc.collect()
        try:
            cls.store._conn().close()
        except Exception:
            pass
        try:
            shutil.rmtree(cls.tmp.name, ignore_errors=True)
        except Exception:
            pass

    def test_analyze_returns_full_structure(self):
        r = self.analyzer.analyze("demo-mon")
        self.assertIn("fundamentals", r.__dict__)
        self.assertIn("market", r.__dict__)
        self.assertIn("community", r.__dict__)
        self.assertIn("riskFactors", r.__dict__)
        self.assertGreater(r.fundamentals.get("dataCompleteness", 0), 0.0)

    def test_unknown_project(self):
        r = self.analyzer.analyze("not-exist")
        self.assertIn("不存在", r.summary)


class TestRisk(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.store = ProjectStore(os.path.join(cls.tmp.name, "tt.sqlite3"))
        apply_seed(cls.store)
        cls.engine = StatusEngine(cls.store)

    @classmethod
    def tearDownClass(cls):
        import gc, shutil
        gc.collect()
        try:
            cls.store._conn().close()
        except Exception:
            pass
        try:
            shutil.rmtree(cls.tmp.name, ignore_errors=True)
        except Exception:
            pass

    def test_evaluate_returns_status(self):
        r = self.engine.evaluate("demo-mon")
        self.assertIn(r["status"], ("HEALTHY", "NEEDS_REVIEW", "HIGH_RISK"))
        self.assertIn("factors", r)
        self.assertIn("score", r)

    def test_status_persisted(self):
        self.engine.evaluate("demo-mon")
        rs = self.store.get_risk("demo-mon")
        self.assertIsNotNone(rs)
        self.assertIn(rs["status"], ("HEALTHY", "NEEDS_REVIEW", "HIGH_RISK"))


if __name__ == "__main__":
    unittest.main()
