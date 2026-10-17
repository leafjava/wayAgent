"""RWA / 股票代币化 单元测试。"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.projects.store import ProjectStore, Project
from src.projects.seed_data import apply_seed
from src.tracking.watchlist import WatchlistService, PLATFORMS, RWA_ACTIONS, find_platform
from src.knowledge.qa_engine import QAEngine


class TestPlatforms(unittest.TestCase):
    def test_rwa_platforms_exist(self):
        rwa = [p for p in PLATFORMS if p["category"] == "rwa"]
        self.assertEqual(len(rwa), 4)
        names = [p["id"] for p in rwa]
        self.assertIn("licensed_broker_us", names)
        self.assertIn("licensed_broker_eu", names)
        self.assertIn("rwa_marketplace", names)
        self.assertIn("securities_platform", names)

    def test_rwa_platforms_require_kyc(self):
        for p in PLATFORMS:
            if p["category"] == "rwa":
                self.assertTrue(p.get("requiresKyc"), f"{p['id']} should require KYC")
                self.assertIn("regulator", p)
                # 必须支持 4 种 RWA 动作
                for action in ("buy_rwa", "sell", "redeem_rwa", "claim_dividend"):
                    self.assertIn(action, p["supportedActions"])

    def test_dex_cex_platforms_distinct(self):
        for p in PLATFORMS:
            if p["category"] in ("dex", "cex"):
                self.assertFalse(p.get("requiresKyc", False), f"{p['id']} should NOT require KYC for demo")

    def test_find_platform(self):
        self.assertIsNotNone(find_platform("uniswap"))
        self.assertIsNotNone(find_platform("licensed_broker_us"))
        self.assertIsNone(find_platform("not-a-platform"))

    def test_rwa_actions_set(self):
        self.assertIn("buy_rwa", RWA_ACTIONS)
        self.assertIn("redeem_rwa", RWA_ACTIONS)
        self.assertIn("claim_dividend", RWA_ACTIONS)
        self.assertEqual(len(RWA_ACTIONS), 4)


class TestRWAStore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.store = ProjectStore(os.path.join(cls.tmp.name, "tt.sqlite3"))

    @classmethod
    def tearDownClass(cls):
        import gc, shutil
        gc.collect()
        try:
            cls.store._conn().close()
        except Exception:
            pass
        shutil.rmtree(cls.tmp.name, ignore_errors=True)

    def test_upsert_and_get_rwa(self):
        self.store.upsert_rwa_record(
            project_id="rwa-1",
            underlying_asset="AAPL",
            custodian="Test Custodian",
            regulator="SEC",
            regulatory_framework="Reg D 506(c)",
            redemption_period_days=30,
            minimum_redemption="100",
            dividend_frequency="季度",
            audit_firm="Test Audit",
            last_audit_date="2026-09-30",
            kyc_required=True,
            accredited_only=True,
        )
        rec = self.store.get_rwa_record("rwa-1")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["underlying_asset"], "AAPL")
        self.assertEqual(rec["redemption_period_days"], 30)
        self.assertTrue(rec["kyc_required"])
        self.assertTrue(rec["accredited_only"])

    def test_project_with_category_and_rwa_info(self):
        self.store.upsert_project(Project(
            projectId="rwa-2", name="Test Stock", symbol="TST",
            sector="RWA", description="test", category="rwa_stock",
            rwaInfo={"underlying_asset": "TSLA", "custodian": "X"}
        ))
        p = self.store.get_project("rwa-2")
        self.assertEqual(p["category"], "rwa_stock")
        self.assertEqual(p["rwaInfo"]["underlying_asset"], "TSLA")


class TestExecutionRecord(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.store = ProjectStore(os.path.join(cls.tmp.name, "tt.sqlite3"))
        cls.watch = WatchlistService(cls.store)

    @classmethod
    def tearDownClass(cls):
        import gc, shutil
        gc.collect()
        try:
            cls.store._conn().close()
        except Exception:
            pass
        shutil.rmtree(cls.tmp.name, ignore_errors=True)

    def test_add_and_list_execution(self):
        rec = self.watch.record_execution(
            consent_id="ct-1", project_id="demo-equityx", platform="licensed_broker_us",
            action_type="buy_rwa", amount="1000 EQX", user_label="user-A",
            evidence_hash="0xabc", status="executed"
        )
        self.assertIn("executionId", rec)
        rows = self.watch.store.list_executions(project_id="demo-equityx")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["actionType"], "buy_rwa")
        self.assertEqual(rows[0]["amount"], "1000 EQX")

    def test_rwa_consent_returns_kyc_warning(self):
        consent = self.watch.request_execution(
            project_id="demo-equityx", platform="licensed_broker_us",
            action_type="buy_rwa", user_label="u", amount="500 EQX"
        )
        self.assertTrue(consent.get("requiresKyc"))
        self.assertIn("regulator", consent)
        self.assertIn("warning", consent)
        self.assertIn("redirectUrl", consent)

    def test_non_rwa_consent_no_kyc(self):
        consent = self.watch.request_execution(
            project_id="demo-mon", platform="uniswap",
            action_type="swap", user_label="u"
        )
        self.assertNotIn("requiresKyc", consent)


class TestRWAQAIntent(unittest.TestCase):
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
        shutil.rmtree(cls.tmp.name, ignore_errors=True)

    def test_rwa_intent_detection(self):
        intents = self.qa._detect_intent("底层资产由谁托管？")
        self.assertIn("underlying_asset", intents)

    def test_kyc_intent(self):
        intents = self.qa._detect_intent("需要 KYC 吗？")
        self.assertIn("kyc_compliance", intents)

    def test_redemption_intent(self):
        intents = self.qa._detect_intent("如何赎回底层资产？")
        self.assertIn("redemption", intents)

    def test_dividend_intent(self):
        intents = self.qa._detect_intent("分红派息是什么？")
        self.assertIn("dividend_rights", intents)

    def test_rwa_answer_uses_rwa_metadata(self):
        ans = self.qa.ask("demo-equityx", "底层资产由谁托管？")
        self.assertIn("First Trust Custody", ans.conclusion or "")
        self.assertIn("SEC", ans.conclusion or "")

    def test_rwa_redemption_answer(self):
        # "如何赎回" 双匹配，按主意图（underlying_asset first）→ 仍展示 RWA 元信息
        ans = self.qa.ask("demo-equityx", "如何赎回底层资产？")
        self.assertIn("TechCorp", ans.conclusion or "")
        self.assertIn("First Trust Custody", ans.conclusion or "")

    def test_rwa_redemption_direct(self):
        # 直接问"赎回"关键词，单意图匹配
        ans = self.qa.ask("demo-equityx", "赎回机制是怎样的？")
        # redemption handler 输出应包含 30 天
        self.assertIn("30", ans.conclusion or "")

    def test_kyc_answer_mentions_compliance(self):
        ans = self.qa.ask("demo-equityx", "需要 KYC 吗？")
        self.assertIn("合格投资者", ans.conclusion or "")
        self.assertIn("KYC", ans.conclusion or "")

    def test_crypto_project_kyc_question_still_answered(self):
        # 即使是 crypto 项目，KYC 意图也应被识别
        ans = self.qa.ask("demo-mon", "需要 KYC 吗？")
        self.assertIsNotNone(ans.conclusion)


if __name__ == "__main__":
    unittest.main()
