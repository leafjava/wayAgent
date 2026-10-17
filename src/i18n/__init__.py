"""i18n 字典。"""
import json
from pathlib import Path
from typing import Any, Dict

DICTS_DIR = Path(__file__).resolve().parent / "dicts"

_cache: Dict[str, Any] = {}


def get_dict(lang: str = "zh-CN") -> Dict[str, Any]:
    if lang in _cache:
        return _cache[lang]
    p = DICTS_DIR / f"{lang}.json"
    if not p.exists():
        p = DICTS_DIR / "zh-CN.json"
    _cache[lang] = json.loads(p.read_text(encoding="utf-8"))
    return _cache[lang]
