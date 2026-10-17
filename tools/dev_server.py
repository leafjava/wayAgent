"""harness 模式启动器。"""

from __future__ import annotations

import os
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.harness_support import load_harness_app  # noqa: E402


def _available_port(preferred: int = 4000) -> int:
    for c in (preferred, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", c))
            except OSError:
                continue
            return int(s.getsockname()[1])
    raise RuntimeError("no port")


def main() -> None:
    runtime_dir = ROOT / ".pose_runtime" / "harness"
    web_app = load_harness_app(runtime_dir)
    web_app.app.config.update(TESTING=False, TEMPLATES_AUTO_RELOAD=True)
    web_app.app.jinja_env.auto_reload = True
    port = int(os.getenv("PORT", "0")) or _available_port()
    print(f"[HARNESS] TokenTruth · http://127.0.0.1:{port}")
    web_app.app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
