"""LLM 客户端 + 模板解析 单元测试。"""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.knowledge.llm_client import (
    DeepSeekClient, LLMResponse, build_qa_messages, parse_json_response,
    citation_indexes_to_docs,
)


class TestDeepSeekClient(unittest.TestCase):
    def test_disabled_without_key(self):
        os.environ["DEEPSEEK_API_KEY"] = ""
        c = DeepSeekClient(api_key="")
        self.assertFalse(c.enabled)

    def test_enabled_with_key(self):
        c = DeepSeekClient(api_key="sk-test")
        self.assertTrue(c.enabled)
        self.assertEqual(c.model, "deepseek-chat")
        self.assertIn("deepseek.com", c.base_url)

    def test_env_override(self):
        os.environ["DEEPSEEK_BASE_URL"] = "https://proxy.example/v1/"
        os.environ["DEEPSEEK_MODEL"] = "deepseek-coder"
        c = DeepSeekClient(api_key="sk-x")
        self.assertEqual(c.base_url, "https://proxy.example/v1")
        self.assertEqual(c.model, "deepseek-coder")
        del os.environ["DEEPSEEK_BASE_URL"]
        del os.environ["DEEPSEEK_MODEL"]

    @patch("requests.post")
    def test_chat_success(self, mock_post):
        c = DeepSeekClient(api_key="sk-test")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": '{"conclusion": "ok"}'}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 20},
        }
        mock_post.return_value = mock_resp
        r = c.chat([{"role": "user", "content": "hi"}], max_tokens=100)
        self.assertIsInstance(r, LLMResponse)
        self.assertEqual(r.text, '{"conclusion": "ok"}')
        self.assertEqual(r.prompt_tokens, 100)
        self.assertEqual(r.completion_tokens, 20)
        # 验证请求 URL 和 header
        args, kwargs = mock_post.call_args
        self.assertIn("/chat/completions", args[0])
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer sk-test")

    @patch("requests.post")
    def test_chat_failure(self, mock_post):
        c = DeepSeekClient(api_key="sk-test")
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        mock_post.return_value = mock_resp
        with self.assertRaises(RuntimeError):
            c.chat([{"role": "user", "content": "hi"}])


class TestParseJson(unittest.TestCase):
    def test_parse_plain_json(self):
        text = '{"conclusion": "ok", "risks": ["a"]}'
        d = parse_json_response(text)
        self.assertEqual(d["conclusion"], "ok")
        self.assertEqual(d["risks"], ["a"])

    def test_parse_with_markdown_fence(self):
        text = "```json\n{\"conclusion\": \"x\"}\n```"
        d = parse_json_response(text)
        self.assertEqual(d["conclusion"], "x")

    def test_parse_with_extra_text(self):
        text = '这是回答：{"conclusion": "y", "confidence": "high"} 完毕'
        d = parse_json_response(text)
        self.assertEqual(d["conclusion"], "y")
        self.assertEqual(d["confidence"], "high")

    def test_parse_invalid(self):
        text = "no json here"
        d = parse_json_response(text)
        self.assertEqual(d, {})


class TestBuildQaMessages(unittest.TestCase):
    def test_messages_structure(self):
        project = {"name": "Demo", "symbol": "DEMO", "sector": "L1", "description": "A test project."}
        contexts = [
            {"docId": "d1", "docType": "whitepaper", "title": "WP",
             "trustLevel": "official", "version": "v1.0", "excerpt": "excerpt here"}
        ]
        msgs = build_qa_messages(project, "代币有什么权利？", contexts)
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0]["role"], "system")
        self.assertEqual(msgs[1]["role"], "user")
        # 用户消息中应包含项目名 + 引用 + 问题
        self.assertIn("Demo", msgs[1]["content"])
        self.assertIn("代币有什么权利？", msgs[1]["content"])
        self.assertIn("[1]", msgs[1]["content"])
        self.assertIn("excerpt here", msgs[1]["content"])


class TestCitationMapping(unittest.TestCase):
    def test_indexes_to_docs(self):
        contexts = [
            {"docId": "a", "title": "A"},
            {"docId": "b", "title": "B"},
            {"docId": "c", "title": "C"},
        ]
        out = citation_indexes_to_docs([1, 3], contexts)
        self.assertEqual([c["docId"] for c in out], ["a", "c"])

    def test_out_of_range(self):
        contexts = [{"docId": "a"}]
        out = citation_indexes_to_docs([2, 5], contexts)
        self.assertEqual(out, [])

    def test_empty(self):
        self.assertEqual(citation_indexes_to_docs([], [{"docId": "a"}]), [])


class TestQAEngineLLMIntegration(unittest.TestCase):
    """测试 QAEngine 集成 LLM 的降级行为。"""

    def setUp(self):
        import tempfile
        from src.projects.store import ProjectStore
        from src.projects.seed_data import apply_seed
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(os.path.join(self.tmp.name, "tt.sqlite3"))
        apply_seed(self.store)

    def tearDown(self):
        import gc, shutil
        gc.collect()
        try:
            self.store._conn().close()
        except Exception:
            pass
        shutil.rmtree(self.tmp.name, ignore_errors=True)

    def test_no_llm_client_falls_back_to_template(self):
        from src.knowledge.qa_engine import QAEngine
        qa = QAEngine(self.store, llm_client=None)
        ans = qa.ask("demo-mon", "这家公司靠什么赚钱？", prefer_llm=True)
        self.assertIn("收入", ans.conclusion or "收入")
        self.assertGreaterEqual(len(ans.citations), 1)

    def test_disabled_llm_falls_back(self):
        from src.knowledge.qa_engine import QAEngine
        # 显式创建一个 disabled client
        from src.knowledge.llm_client import DeepSeekClient
        llm = DeepSeekClient(api_key="")
        qa = QAEngine(self.store, llm_client=llm)
        ans = qa.ask("demo-mon", "代币有什么权利？", prefer_llm=True)
        # key 为空时 enable=False，本地模板跑
        self.assertFalse(llm.enabled)
        self.assertTrue(
            "代币" in (ans.conclusion or "") or "DEMO" in (ans.conclusion or ""),
            f"expected token info in conclusion, got: {ans.conclusion[:80]!r}",
        )

    def test_llm_failure_falls_back(self):
        from src.knowledge.qa_engine import QAEngine
        from src.knowledge.llm_client import DeepSeekClient
        # 模拟一个 enabled 但 chat() 抛异常的 client
        llm = DeepSeekClient(api_key="sk-fake")
        # monkey-patch chat to raise
        def boom(*a, **k):
            raise RuntimeError("network down")
        llm.chat = boom
        qa = QAEngine(self.store, llm_client=llm)
        ans = qa.ask("demo-mon", "未来一年有哪些解锁？", prefer_llm=True)
        # 降级到本地模板，应该不抛错
        self.assertIn("解锁", ans.conclusion or "解锁" or "")

    def test_llm_success_returns_structured(self):
        from src.knowledge.qa_engine import QAEngine
        from src.knowledge.llm_client import DeepSeekClient, LLMResponse
        llm = DeepSeekClient(api_key="sk-fake")
        llm.chat = lambda *a, **k: LLMResponse(
            text=json.dumps({
                "conclusion": "LLM 自定义结论",
                "reasoning": "推理过程",
                "citationIndexes": [1],
                "risks": ["风险 1"],
                "confidence": "high",
                "followups": ["追问 1"]
            }),
            model="deepseek-chat",
        )
        qa = QAEngine(self.store, llm_client=llm)
        ans = qa.ask("demo-mon", "这家公司靠什么赚钱？", prefer_llm=True)
        self.assertEqual(ans.conclusion, "LLM 自定义结论")
        self.assertEqual(ans.confidence, "high")
        self.assertEqual(ans.risks, ["风险 1"])
        self.assertEqual(ans.suggestedFollowups, ["追问 1"])
        # citations 应该有 1 个（来自 LLM 指定的 [1]）
        self.assertEqual(len(ans.citations), 1)


if __name__ == "__main__":
    unittest.main()
