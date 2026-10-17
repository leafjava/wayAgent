"""公司侧：内容生成 + 版本对比 单元测试。"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.projects.store import ProjectStore, Version
from src.projects.seed_data import apply_seed
from src.company.content_gen import ContentGenerator
from src.company.version_diff import diff_versions


class TestContentGen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.store = ProjectStore(os.path.join(cls.tmp.name, "tt.sqlite3"))
        apply_seed(cls.store)
        cls.gen = ContentGenerator(cls.store)

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

    def test_list_templates(self):
        ts = self.gen.list_templates()
        self.assertGreater(len(ts), 3)

    def test_generate_intro(self):
        d = self.gen.generate("demo-mon", "intro")
        self.assertIn("sections", d)
        self.assertGreaterEqual(len(d["sections"]), 1)
        self.assertIn("disclaimer", d)

    def test_generate_unknown_template(self):
        d = self.gen.generate("demo-mon", "not-a-template")
        self.assertIn("error", d)

    def test_generate_unknown_project(self):
        d = self.gen.generate("not-exist", "intro")
        self.assertIn("error", d)


class TestVersionDiff(unittest.TestCase):
    def test_diff_detects_changes(self):
        old = {"content": "line1\nline2\nline3", "version": "v1.0", "contentHash": "0x1", "changes": {"a": 1, "b": 2}}
        new = {"content": "line1\nline2-modified\nline3\nline4", "version": "v1.1", "contentHash": "0x2", "changes": {"a": 1, "b": 3, "c": 4}}
        diff = diff_versions(old, new)
        self.assertGreater(diff["addedLines"], 0)
        self.assertGreater(diff["removedLines"], 0)
        # changes 中 a 没变，b 变了，新增 c
        fields = {fc["field"] for fc in diff["fieldChanges"]}
        self.assertIn("b", fields)
        self.assertIn("c", fields)


if __name__ == "__main__":
    unittest.main()
