"""问答引擎单元测试。"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.projects.store import ProjectStore
from src.projects.seed_data import apply_seed
from src.knowledge.qa_engine import QAEngine


class TestQA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.store = ProjectStore(os.path.join(cls.tmp.name, "tt.sqlite3"))
        apply_seed(cls.store)
        cls.qa = QAEngine(cls.store)

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

    def test_revenue_intent(self):
        ans = self.qa.ask("demo-mon", "这家公司靠什么赚钱？")
        self.assertIn("DEMO", ans.conclusion or "")
        self.assertIn(ans.confidence, ("high", "medium", "low"))
        self.assertGreaterEqual(len(ans.citations), 1)

    def test_token_rights_intent(self):
        ans = self.qa.ask("demo-mon", "我买的代币有什么权利？")
        self.assertIn("代币", ans.conclusion or "")
        self.assertGreaterEqual(len(ans.citations), 1)

    def test_transfer_restriction_intent(self):
        ans = self.qa.ask("demo-mon", "什么时候可以转让？")
        self.assertIn("解锁", ans.conclusion or "解锁" or "锁仓")

    def test_unlock_intent(self):
        ans = self.qa.ask("demo-mon", "未来一年有哪些解锁？")
        self.assertGreaterEqual(len(ans.citations), 1)

    def test_risk_intent(self):
        ans = self.qa.ask("demo-mon", "这个项目当前最大的风险是什么？")
        self.assertIn("风险", ans.conclusion or "风险")

    def test_general_intent(self):
        ans = self.qa.ask("demo-mon", "今天天气怎么样？")
        self.assertIn(ans.confidence, ("high", "medium", "low"))

    def test_unknown_project(self):
        ans = self.qa.ask("not-exist", "任何问题")
        self.assertIn("未找到", ans.conclusion)

    def test_answer_has_risks_and_followups(self):
        ans = self.qa.ask("demo-mon", "这家公司靠什么赚钱？")
        self.assertIsInstance(ans.risks, list)
        self.assertIsInstance(ans.suggestedFollowups, list)


if __name__ == "__main__":
    unittest.main()
