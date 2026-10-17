"""版本对比工具（line-level diff + 关键字段 diff）。"""

from __future__ import annotations

import difflib
from typing import Any, Dict, List


def diff_versions(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """对比两个版本：行级 diff + 字段级 diff。

    Args:
        old: 旧版本（含 content / version / changes）
        new: 新版本
    Returns:
        diff 摘要：行级 unified diff、变更统计、关键字段变更
    """
    old_content = old.get("content", "")
    new_content = new.get("content", "")

    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()

    diff = list(difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"v{old.get('version', '?')}",
        tofile=f"v{new.get('version', '?')}",
        lineterm="",
        n=2,
    ))

    added = sum(1 for ln in diff if ln.startswith("+") and not ln.startswith("+++"))
    removed = sum(1 for ln in diff if ln.startswith("-") and not ln.startswith("---"))

    # 关键字段
    key_fields = ["unlockSchedule", "tokenRights", "revenue", "vesting", "supply", "circulating", "team"]
    old_changes = old.get("changes") or {}
    new_changes = new.get("changes") or {}
    all_fields = set(old_changes.keys()) | set(new_changes.keys())
    field_changes: List[Dict[str, Any]] = []
    for f in sorted(all_fields):
        old_v = old_changes.get(f)
        new_v = new_changes.get(f)
        if old_v != new_v:
            field_changes.append({"field": f, "old": old_v, "new": new_v})
    # 兼容：当 changes 字段为空时仍按 key_fields 报告
    if not field_changes:
        for f in key_fields:
            old_v = old_changes.get(f)
            new_v = new_changes.get(f)
            if old_v != new_v and (old_v is not None or new_v is not None):
                field_changes.append({"field": f, "old": old_v, "new": new_v})

    return {
        "unifiedDiff": "\n".join(diff[:200]),  # 截断 200 行
        "addedLines": added,
        "removedLines": removed,
        "fieldChanges": field_changes,
        "oldVersion": old.get("version"),
        "newVersion": new.get("version"),
        "oldHash": old.get("contentHash"),
        "newHash": new.get("contentHash"),
    }
