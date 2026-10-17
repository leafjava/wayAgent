"""部署与种子注入脚本（mock 模式不需要真链）。"""

from __future__ import annotations

import os
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config_loader import load_config, default_config_path
from src.projects.store import ProjectStore, Document, Version, hash_project_payload
from src.projects.seed_data import apply_seed
from src.risk.status_engine import StatusEngine
from src.chain.registry import build_registry, evidence_type_to_int, status_to_bytes32


def main() -> int:
    cfg = load_config(default_config_path())
    db_path = ROOT / "data" / "runtime" / "tokentruth.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    store = ProjectStore(str(db_path))
    apply_seed(store)
    print(f"Seed applied: {len(store.list_projects())} projects")

    chain, addr = build_registry()
    print(f"Chain: {type(chain).__name__} @ {addr}")

    risk_engine = StatusEngine(store)
    triggered = 0
    for p in store.list_projects():
        r = risk_engine.evaluate(p["projectId"])
        if r.get("changed"):
            evidence_id = uuid.uuid4().hex
            payload = {"projectId": p["projectId"], "status": r.get("status"), "score": r.get("score")}
            tx = chain.record_evidence(
                evidence_hash=hash_project_payload(payload),
                evidence_id=evidence_id,
                evidence_type=evidence_type_to_int("RISK_STATUS_CHANGE"),
                timestamp=int(time.time()),
                project_id=p["projectId"],
                doc_version="",
                from_status=status_to_bytes32(r.get("fromStatus", "")),
                to_status=status_to_bytes32(r.get("status", "")),
            )
            print(f"  + {p['projectId']} → {r['status']} (score {r.get('score'):.1f})  tx: {tx.tx_hash[:18]}…")
            triggered += 1
    print(f"完成：触发 {triggered} 次链上存证")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
