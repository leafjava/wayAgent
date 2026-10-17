"""Demo 种子项目数据：1 个完整的虚构加密项目，6 类资料、3 个版本。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .store import Project, Document, Version, ProjectStore


SEED_FILE = Path(__file__).resolve().parents[2] / "data" / "demo" / "seed_projects.json"


def load_seed_projects() -> Dict[str, Any]:
    if not SEED_FILE.exists():
        return {}
    return json.loads(SEED_FILE.read_text(encoding="utf-8"))


def apply_seed(store: ProjectStore) -> None:
    """把 seed 数据导入到 store。"""
    seed = load_seed_projects()
    if not seed:
        return
    for p in seed.get("projects", []):
        store.upsert_project(Project(
            projectId=p["projectId"],
            name=p["name"],
            symbol=p["symbol"],
            sector=p.get("sector", ""),
            description=p.get("description", ""),
            website=p.get("website", ""),
            whitepaper=p.get("whitepaper", ""),
        ))
    for d in seed.get("documents", []):
        store.add_document(Document(
            docId=d.get("docId", ""),
            projectId=d["projectId"],
            docType=d["docType"],
            title=d["title"],
            content=d["content"],
            source=d.get("source", "internal"),
            sourceUrl=d.get("sourceUrl", ""),
            trustLevel=d.get("trustLevel", "official"),
        ))
        # 为每个文档自动创建初始版本 v1.0（QA 引擎基于 versions 表检索）
        store.add_version(Version(
            versionId="",
            projectId=d["projectId"],
            docType=d["docType"],
            version="v1.0",
            contentHash="0x" + d["content"][:32].encode("utf-8").hex().ljust(64, "0")[:64],
            content=d["content"],
            parentVersion=None,
            changes={},
        ))
    for v in seed.get("versions", []):
        store.add_version(Version(
            versionId=v.get("versionId", ""),
            projectId=v["projectId"],
            docType=v["docType"],
            version=v["version"],
            contentHash=v["contentHash"],
            content=v["content"],
            parentVersion=v.get("parentVersion"),
            changes=v.get("changes", {}),
        ))
