"""端到端 smoke：项目目录 + 3 个核心问题 + 风险评估 + 资料更新 + 存证查询。"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.harness_support import load_harness_app  # noqa: E402


QUESTIONS = [
    "这家公司靠什么赚钱？",
    "我买的代币有什么权利？",
    "什么时候可以转让？",
    "未来一年有哪些解锁？",
    "这个项目当前最大的风险是什么？",
]


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def run_smoke() -> dict:
    steps: list = []
    with tempfile.TemporaryDirectory(prefix="tt-smoke-") as temp_dir:
        web_app = load_harness_app(Path(temp_dir))
        client = web_app.app.test_client()

        # 1. 8 个页面
        routes = ["/", "/chat", "/analyze", "/track", "/company", "/edit_doc", "/proof"]
        # /project/<id> 需要先有项目
        r = client.post("/api/seed")
        _require(r.status_code == 200, f"seed failed: {r.status_code} {r.get_data(as_text=True)[:200]}")
        steps.append({"step": "seed", "status": "ok"})

        projects = client.get("/api/analyze?projectId=demo-mon").get_json()
        _require("summary" in projects, "analyze should work after seed")
        routes.append("/project/demo-mon")

        for route in routes:
            r = client.get(route)
            _require(r.status_code == 200, f"{route} returned {r.status_code}")
            steps.append({"step": f"GET {route}", "status": r.status_code})

        # 2. 5 个核心问题都能拿到答案
        for q in QUESTIONS:
            r = client.post("/api/qa", json={"projectId": "demo-mon", "question": q})
            _require(r.status_code == 200, f"qa '{q}' failed")
            d = r.get_json()
            _require(d.get("conclusion"), f"qa '{q}' no conclusion")
            _require(d.get("citations") is not None, f"qa '{q}' no citations field")
            steps.append({"step": f"qa: {q[:20]}", "conclusion": d["conclusion"][:50]})

        # 3. 1 个上链版问题
        r = client.post("/api/qa", json={"projectId": "demo-mon", "question": QUESTIONS[0], "anchorOnChain": True})
        d = r.get_json()
        _require(d.get("onChain") and d["onChain"].get("txHash"), "anchored qa missing txHash")
        steps.append({"step": "anchor qa", "tx": d["onChain"]["txHash"][:18]})

        # 4. 风险评估
        r = client.get("/api/risk?projectId=demo-mon")
        _require(r.status_code == 200, "risk failed")
        d = r.get_json()
        _require(d.get("status") in ("HEALTHY", "NEEDS_REVIEW", "HIGH_RISK"), "risk status invalid")
        steps.append({"step": "risk eval", "status": d["status"], "score": d.get("score")})

        # 5. 资料更新 + diff + 上链
        new_content = "## DemoChain 白皮书 v2.0\n\n新增：并行执行细节、并行 TPS 数据、Layer3 路线图。"
        r = client.post("/api/version", json={
            "projectId": "demo-mon",
            "docType": "whitepaper",
            "content": new_content,
            "changes": {"team": "Alex, Maya, Wei", "tier": "Top 50", "revenue": "Gas + RPC + Bridge + MEV"},
        })
        _require(r.status_code == 200, "version create failed")
        d = r.get_json()
        _require(d.get("onChain") and d["onChain"].get("txHash"), "version missing txHash")
        _require(d.get("diff") is not None, "version missing diff")
        steps.append({"step": "new version", "version": d["version"], "tx": d["onChain"]["txHash"][:18]})

        # 6. 链上存证查询
        r = client.get(f"/api/proof/{d['contentHash']}")
        proof = r.get_json()
        _require(proof["onChain"]["exists"], "proof not on chain")
        steps.append({"step": "verify proof", "hash": d["contentHash"][:18]})

        # 7. 关注列表
        r = client.post("/api/watchlist", json={"projectId": "demo-mon", "note": "test", "budget": 100})
        _require(r.status_code == 200, "watchlist add failed")
        items = client.get("/api/watchlist").get_json()["items"]
        _require(len(items) >= 1, "watchlist should have items")
        steps.append({"step": "watchlist", "items": len(items)})

        # 8. 授权执行
        r = client.post("/api/consent", json={
            "projectId": "demo-mon", "platform": "uniswap",
            "actionType": "swap", "userLabel": "smoke-test"
        })
        _require(r.status_code == 200, "consent failed")
        d = r.get_json()
        _require(d.get("onChain") and d["onChain"].get("txHash"), "consent missing txHash")
        steps.append({"step": "consent", "tx": d["onChain"]["txHash"][:18]})

        # 9. 内容生成
        r = client.post("/api/content", json={"projectId": "demo-mon", "template": "intro", "audience": "investor"})
        _require(r.status_code == 200, "content failed")
        d = r.get_json()
        _require(d.get("sections") and len(d["sections"]) >= 1, "content no sections")
        _require(d.get("onChain") and d["onChain"].get("txHash"), "content missing txHash")
        steps.append({"step": "content gen", "template": "intro", "sections": len(d["sections"])})

        # 10. 链状态
        r = client.get("/api/chain/status").get_json()
        _require(r.get("contractAddress"), "chain status missing contract address")
        steps.append({"step": "chain status", "mode": r.get("mode")})

    return {
        "status": "passed",
        "scenario": "tokentruth-investor-issuer",
        "mode": "deterministic-harness-no-gpu",
        "steps": steps,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    result = run_smoke()
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
