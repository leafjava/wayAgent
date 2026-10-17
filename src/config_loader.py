"""TokenTruth · 配置文件加载。"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict


def load_config(path: str | Path) -> Dict[str, Any]:
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(p)
    return deepcopy(json.loads(p.read_text(encoding="utf-8")))


def default_config_path() -> Path:
    return Path(__file__).resolve().parent.parent / "config" / "default.json"
