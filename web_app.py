"""TokenTruth · Flask 主入口。

页面：/ · /project/<id> · /chat · /analyze · /track · /company · /edit_doc · /proof
API：/api/qa · /api/analyze · /api/watchlist · /api/consent · /api/content
     /api/version · /api/risk · /api/proof · /api/chain · /api/seed
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# 自动加载 .env（如果存在）
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from flask import Flask, jsonify, render_template, request, redirect, url_for

from src.config_loader import load_config, default_config_path
from src.projects.store import ProjectStore, Project, Document, Version, hash_project_payload
from src.projects.seed_data import apply_seed, load_seed_projects
from src.knowledge.qa_engine import QAEngine
from src.knowledge.analyzer import Analyzer
from src.knowledge.llm_client import DeepSeekClient
from src.tracking.watchlist import WatchlistService, PLATFORMS, RWA_ACTIONS, find_platform, InvestmentPlan
from src.company.content_gen import ContentGenerator
from src.company.version_diff import diff_versions
from src.risk.status_engine import StatusEngine
from src.chain.registry import build_registry, evidence_type_to_int, status_to_bytes32
from src.i18n import get_dict


logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("tokentruth")

CONFIG = load_config(default_config_path())
DB_PATH = ROOT / "data" / "runtime" / "tokentruth.sqlite3"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

STORE = ProjectStore(str(DB_PATH))
LLM = DeepSeekClient()  # 自动读取 DEEPSEEK_API_KEY / BASE_URL / MODEL
QA = QAEngine(STORE, llm_client=LLM)
ANALYZER = Analyzer(STORE)
WATCH = WatchlistService(STORE)
GEN = ContentGenerator(STORE)
RISK = StatusEngine(STORE)
CHAIN, CONTRACT_ADDRESS = build_registry()
CHAIN_MODE = type(CHAIN).__name__
LLM_ENABLED = LLM.enabled
LLM_MODEL = LLM.model


# 首次启动时灌入 seed
if not STORE.list_projects():
    apply_seed(STORE)
    log.info("已灌入 demo seed 项目")
log.info("LLM 状态：%s (model=%s)", "启用" if LLM_ENABLED else "降级到本地引擎", LLM_MODEL)


# --------------------------------------------------------------------------- #
# Flask App
# --------------------------------------------------------------------------- #

app = Flask(
    __name__,
    template_folder=str(ROOT / "templates"),
    static_folder=str(ROOT / "static"),
)


def _now_ts() -> int:
    return int(time.time())


def _lang() -> str:
    return request.args.get("lang") or request.cookies.get("tt_lang") or CONFIG["app"].get("default_language", "zh-CN")


# ─────────── 页面 ───────────


@app.route("/")
def home():
    projects = STORE.list_projects()
    return render_template(
        "home.html",
        projects=projects,
        mode=CHAIN_MODE,
        contract_address=CONTRACT_ADDRESS,
        lang=_lang(),
        t=get_dict(_lang()),
    )


@app.route("/project/<project_id>")
def project_detail(project_id: str):
    project = STORE.get_project(project_id)
    if not project:
        return redirect(url_for("home"))
    docs = STORE.list_documents(project_id)
    versions: Dict[str, List[Dict[str, Any]]] = {}
    for d in docs:
        versions[d["docType"]] = STORE.list_versions(project_id, d["docType"])
    risk = STORE.get_risk(project_id)
    return render_template(
        "project.html",
        project=project,
        docs=docs,
        versions=versions,
        risk=risk,
        mode=CHAIN_MODE,
        contract_address=CONTRACT_ADDRESS,
        lang=_lang(),
        t=get_dict(_lang()),
    )


@app.route("/chat")
def chat():
    projects = STORE.list_projects()
    default_id = projects[0]["projectId"] if projects else "demo-mon"
    project_id = request.args.get("projectId", default_id)
    return render_template(
        "chat.html",
        project_id=project_id,
        projects=projects,
        mode=CHAIN_MODE,
        contract_address=CONTRACT_ADDRESS,
        lang=_lang(),
        t=get_dict(_lang()),
    )


@app.route("/analyze")
def analyze():
    projects = STORE.list_projects()
    default_id = projects[0]["projectId"] if projects else "demo-mon"
    project_id = request.args.get("projectId", default_id)
    return render_template(
        "analyze.html",
        project_id=project_id,
        projects=projects,
        mode=CHAIN_MODE,
        contract_address=CONTRACT_ADDRESS,
        lang=_lang(),
        t=get_dict(_lang()),
    )


@app.route("/track")
def track():
    return render_template(
        "track.html",
        mode=CHAIN_MODE,
        contract_address=CONTRACT_ADDRESS,
        lang=_lang(),
        t=get_dict(_lang()),
        platforms=PLATFORMS,
    )


@app.route("/company")
def company():
    projects = STORE.list_projects()
    default_id = projects[0]["projectId"] if projects else "demo-mon"
    project_id = request.args.get("projectId", default_id)
    return render_template(
        "company.html",
        project_id=project_id,
        projects=projects,
        templates=GEN.list_templates(),
        mode=CHAIN_MODE,
        contract_address=CONTRACT_ADDRESS,
        lang=_lang(),
        t=get_dict(_lang()),
    )


@app.route("/edit_doc")
def edit_doc():
    projects = STORE.list_projects()
    default_id = projects[0]["projectId"] if projects else "demo-mon"
    project_id = request.args.get("projectId", default_id)
    doc_type = request.args.get("docType", "whitepaper")
    return render_template(
        "edit_doc.html",
        project_id=project_id,
        doc_type=doc_type,
        mode=CHAIN_MODE,
        contract_address=CONTRACT_ADDRESS,
        lang=_lang(),
        t=get_dict(_lang()),
    )


@app.route("/proof")
def proof_page():
    evidence_hash = request.args.get("hash", "")
    return render_template(
        "proof.html",
        evidence_hash=evidence_hash,
        mode=CHAIN_MODE,
        contract_address=CONTRACT_ADDRESS,
        lang=_lang(),
        t=get_dict(_lang()),
    )


# ─────────── API：问答 ───────────


@app.route("/api/qa", methods=["POST"])
def api_qa():
    payload = request.get_json(silent=True) or {}
    project_id = str(payload.get("projectId", "")).strip()
    question = str(payload.get("question", "")).strip()
    prefer_llm = bool(payload.get("preferLlm", True))
    if not project_id or not question:
        return jsonify({"error": "缺少 projectId 或 question"}), 400
    ans = QA.ask(project_id, question, prefer_llm=prefer_llm)
    # 触发链上存证（可选：研究问答作为 INVESTOR_QA 类型）
    if payload.get("anchorOnChain", False):
        evidence_id = uuid.uuid4().hex
        evidence_payload = {
            "projectId": project_id,
            "question": question,
            "conclusion": ans.conclusion,
            "citations": [c.docId + "@" + c.version for c in ans.citations],
        }
        evidence_hash = hash_project_payload(evidence_payload)
        tx = CHAIN.record_evidence(
            evidence_hash=evidence_hash,
            evidence_id=evidence_id,
            evidence_type=evidence_type_to_int("INVESTOR_QA"),
            timestamp=_now_ts(),
            project_id=project_id,
            doc_version="",
            from_status=status_to_bytes32(""),
            to_status=status_to_bytes32(""),
        )
        result = {
            "question": ans.question,
            "conclusion": ans.conclusion,
            "confidence": ans.confidence,
            "risks": ans.risks,
            "reasoning": ans.reasoning,
            "suggestedFollowups": ans.suggestedFollowups,
            "citations": [
                {
                    "docId": c.docId,
                    "docType": c.docType,
                    "title": c.title,
                    "trustLevel": c.trustLevel,
                    "source": c.source,
                    "sourceUrl": c.sourceUrl,
                    "excerpt": c.excerpt,
                    "version": c.version,
                }
                for c in ans.citations
            ],
            "onChain": {
                "evidenceHash": evidence_hash,
                "evidenceId": evidence_id,
                "txHash": tx.tx_hash,
                "blockNumber": tx.block_number,
                "status": tx.status,
            },
        }
        return jsonify(result)
    return jsonify({
        "question": ans.question,
        "conclusion": ans.conclusion,
        "confidence": ans.confidence,
        "risks": ans.risks,
        "reasoning": ans.reasoning,
        "suggestedFollowups": ans.suggestedFollowups,
        "llmUsed": LLM_ENABLED and prefer_llm,
        "llmModel": LLM_MODEL if LLM_ENABLED else None,
        "citations": [
            {
                "docId": c.docId, "docType": c.docType, "title": c.title,
                "trustLevel": c.trustLevel, "source": c.source,
                "sourceUrl": c.sourceUrl, "excerpt": c.excerpt, "version": c.version,
            } for c in ans.citations
        ],
    })


# ─────────── API：LLM 状态 ───────────


@app.route("/api/llm/status", methods=["GET"])
def api_llm_status():
    return jsonify({
        "enabled": LLM_ENABLED,
        "model": LLM_MODEL,
        "baseUrl": LLM.base_url,
    })


# ─────────── API：分析 ───────────


@app.route("/api/analyze", methods=["GET"])
def api_analyze():
    project_id = request.args.get("projectId", "")
    if not project_id:
        return jsonify({"error": "缺少 projectId"}), 400
    result = ANALYZER.analyze(project_id)
    return jsonify({
        "projectId": result.projectId,
        "fundamentals": result.fundamentals,
        "market": result.market,
        "community": result.community,
        "riskFactors": result.riskFactors,
        "summary": result.summary,
    })


@app.route("/api/risk", methods=["GET"])
def api_risk():
    project_id = request.args.get("projectId", "")
    if not project_id:
        return jsonify({"error": "缺少 projectId"}), 400
    result = RISK.evaluate(project_id)
    # 如果状态变更，触发链上存证
    if result.get("changed"):
        evidence_id = uuid.uuid4().hex
        payload = {
            "projectId": project_id,
            "status": result.get("status"),
            "score": result.get("score"),
            "fromStatus": result.get("fromStatus"),
        }
        evidence_hash = hash_project_payload(payload)
        tx = CHAIN.record_evidence(
            evidence_hash=evidence_hash,
            evidence_id=evidence_id,
            evidence_type=evidence_type_to_int("RISK_STATUS_CHANGE"),
            timestamp=_now_ts(),
            project_id=project_id,
            doc_version="",
            from_status=status_to_bytes32(result.get("fromStatus", "")),
            to_status=status_to_bytes32(result.get("status", "")),
        )
        result["onChain"] = {
            "evidenceHash": evidence_hash,
            "evidenceId": evidence_id,
            "txHash": tx.tx_hash,
            "blockNumber": tx.block_number,
            "status": tx.status,
        }
    return jsonify(result)


# ─────────── API：跟踪 ───────────


@app.route("/api/watchlist", methods=["GET"])
def api_watchlist_list():
    return jsonify({"items": WATCH.list()})


@app.route("/api/watchlist", methods=["POST"])
def api_watchlist_add():
    payload = request.get_json(silent=True) or {}
    project_id = str(payload.get("projectId", "")).strip()
    note = str(payload.get("note", "")).strip()
    budget = float(payload.get("budget", 0) or 0)
    if not project_id:
        return jsonify({"error": "缺少 projectId"}), 400
    return jsonify(WATCH.add(project_id, note, budget))


@app.route("/api/watchlist/<watch_id>", methods=["DELETE"])
def api_watchlist_remove(watch_id: str):
    return jsonify({"removed": WATCH.remove(watch_id)})


@app.route("/api/plan", methods=["POST"])
def api_plan():
    payload = request.get_json(silent=True) or {}
    project_id = str(payload.get("projectId", "")).strip()
    if not project_id:
        return jsonify({"error": "缺少 projectId"}), 400
    plan = InvestmentPlan(
        projectId=project_id,
        budget=float(payload.get("budget", 0) or 0),
        riskPreference=str(payload.get("riskPreference", "balanced")),
        trackingFrequency=str(payload.get("trackingFrequency", "daily")),
        notes=str(payload.get("notes", "")),
    )
    return jsonify(WATCH.save_plan(project_id, plan))


@app.route("/api/consent", methods=["POST"])
def api_consent():
    payload = request.get_json(silent=True) or {}
    project_id = str(payload.get("projectId", "")).strip()
    platform = str(payload.get("platform", "")).strip()
    action_type = str(payload.get("actionType", "")).strip()
    user_label = str(payload.get("userLabel", "")).strip()
    amount = str(payload.get("amount", "")).strip()
    if not (project_id and platform and action_type):
        return jsonify({"error": "缺少必要字段"}), 400
    consent = WATCH.request_execution(project_id, platform, action_type, user_label, amount)
    # 链上存证
    evidence_id = consent["consentId"]
    evidence_hash = consent["evidenceHash"]
    tx = CHAIN.record_evidence(
        evidence_hash=evidence_hash,
        evidence_id=evidence_id,
        evidence_type=evidence_type_to_int("EXECUTION_CONSENT"),
        timestamp=_now_ts(),
        project_id=project_id,
        doc_version="",
        from_status=status_to_bytes32(""),
        to_status=status_to_bytes32(""),
    )
    WATCH.update_consent_chain(consent["consentId"], tx.tx_hash, tx.status)
    consent["onChain"] = {
        "evidenceHash": evidence_hash,
        "txHash": tx.tx_hash,
        "blockNumber": tx.block_number,
        "status": tx.status,
    }
    return jsonify(consent)


# ─────────── API：帮客户买代币（用户授权后执行）───────────


@app.route("/api/buy", methods=["POST"])
def api_buy():
    """帮客户买代币：用户授权后由 TokenTruth 生成执行记录 + 链上存证 + 跳转合规平台。

    仅生成授权记录，不直接执行任何交易；实际买入由第三方合规平台完成。
    """
    payload = request.get_json(silent=True) or {}
    project_id = str(payload.get("projectId", "")).strip()
    platform = str(payload.get("platform", "")).strip()
    amount = str(payload.get("amount", "")).strip()
    user_label = str(payload.get("userLabel", "")).strip()
    if not (project_id and platform):
        return jsonify({"error": "缺少 projectId 或 platform"}), 400
    if not amount:
        return jsonify({"error": "缺少 amount"}), 400

    project = STORE.get_project(project_id)
    if not project:
        return jsonify({"error": "项目不存在"}), 404
    category = project.get("category", "crypto")

    # RWA 必须用合规平台
    plat = find_platform(platform)
    if category.startswith("rwa") and (not plat or plat.get("category") != "rwa"):
        return jsonify({
            "error": "RWA / 股票代币化项目必须使用合规券商平台（如 licensed_broker_us / licensed_broker_eu / rwa_marketplace / securities_platform）",
            "availableRwaPlatforms": [p["id"] for p in PLATFORMS if p["category"] == "rwa"],
        }), 400

    # 生成 consent + 链上存证
    consent = WATCH.request_execution(project_id, platform, "buy_rwa" if category.startswith("rwa") else "buy", user_label, amount)
    evidence_id = consent["consentId"]
    evidence_hash = consent["evidenceHash"]
    tx = CHAIN.record_evidence(
        evidence_hash=evidence_hash,
        evidence_id=evidence_id,
        evidence_type=evidence_type_to_int("EXECUTION_CONSENT"),
        timestamp=_now_ts(),
        project_id=project_id,
        doc_version=amount,
        from_status=status_to_bytes32(""),
        to_status=status_to_bytes32(""),
    )
    WATCH.update_consent_chain(consent["consentId"], tx.tx_hash, tx.status)
    consent["onChain"] = {
        "evidenceHash": evidence_hash,
        "txHash": tx.tx_hash,
        "blockNumber": tx.block_number,
        "status": tx.status,
    }

    # 在第三方平台"完成"后回填执行记录（mock 模式立即成功）
    execution = WATCH.record_execution(
        consent_id=consent["consentId"],
        project_id=project_id,
        platform=platform,
        action_type=consent.get("actionType") or "buy_rwa",
        amount=amount,
        user_label=user_label,
        evidence_hash=evidence_hash,
        status="dispatched",
    )
    WATCH.store.update_execution(
        execution["executionId"],
        tx_hash=tx.tx_hash,
        block_explorer=f"https://testnet.monadexplorer.com/tx/{tx.tx_hash}",
        status="dispatched",
    )

    return jsonify({
        "consent": consent,
        "execution": execution,
        "redirectUrl": consent["redirectUrl"],
        "disclaimer": (
            "TokenTruth 仅生成授权记录与链上存证；"
            "实际买入在第三方合规平台完成，请在该平台完成 KYC 后再继续。"
            if category.startswith("rwa") else
            "TokenTruth 仅生成授权记录与链上存证；实际买入由第三方平台完成。"
        ),
    })


@app.route("/api/executions", methods=["GET"])
def api_executions_list():
    """查询执行记录。"""
    project_id = request.args.get("projectId")
    consent_id = request.args.get("consentId")
    return jsonify({"executions": WATCH.store.list_executions(project_id=project_id, consent_id=consent_id)})


@app.route("/api/platforms", methods=["GET"])
def api_platforms():
    return jsonify({
        "platforms": PLATFORMS,
        "rwaActions": sorted(RWA_ACTIONS),
    })


@app.route("/api/consent", methods=["GET"])
def api_consent_list():
    project_id = request.args.get("projectId")
    return jsonify({"consents": WATCH.list_consents(project_id)})


# ─────────── API：公司侧 ───────────


@app.route("/api/content", methods=["POST"])
def api_content():
    payload = request.get_json(silent=True) or {}
    project_id = str(payload.get("projectId", "")).strip()
    template = str(payload.get("template", "")).strip()
    audience = str(payload.get("audience", "investor"))
    if not project_id or not template:
        return jsonify({"error": "缺少 projectId 或 template"}), 400
    content = GEN.generate(project_id, template, audience)
    # 链上存证
    evidence_id = uuid.uuid4().hex
    payload_hash = hash_project_payload({"projectId": project_id, "template": template, "content": content})
    tx = CHAIN.record_evidence(
        evidence_hash=payload_hash,
        evidence_id=evidence_id,
        evidence_type=evidence_type_to_int("CONTENT_PUBLISH"),
        timestamp=_now_ts(),
        project_id=project_id,
        doc_version=template,
        from_status=status_to_bytes32(""),
        to_status=status_to_bytes32(""),
    )
    content["onChain"] = {
        "evidenceHash": payload_hash,
        "evidenceId": evidence_id,
        "txHash": tx.tx_hash,
        "blockNumber": tx.block_number,
        "status": tx.status,
    }
    return jsonify(content)


@app.route("/api/version", methods=["POST"])
def api_version():
    """项目方提交新版本。"""
    payload = request.get_json(silent=True) or {}
    project_id = str(payload.get("projectId", "")).strip()
    doc_type = str(payload.get("docType", "")).strip()
    content = str(payload.get("content", ""))
    changes = payload.get("changes") or {}
    if not (project_id and doc_type and content):
        return jsonify({"error": "缺少必要字段"}), 400
    # 找最新版本作为 parent
    latest = STORE.latest_version(project_id, doc_type)
    parent_version = latest["version"] if latest else None
    # 计算 hash
    content_hash = hash_project_payload({"content": content, "docType": doc_type})
    # 新版本号
    if latest:
        try:
            v_num = float(latest["version"].replace("v", ""))
            new_version = f"v{v_num + 0.1:.1f}"
        except ValueError:
            new_version = "v1.1"
    else:
        new_version = "v1.0"
    new = Version(
        versionId="",
        projectId=project_id,
        docType=doc_type,
        version=new_version,
        contentHash=content_hash,
        content=content,
        parentVersion=parent_version,
        changes=changes,
    )
    version_id = STORE.add_version(new)
    # 同步更新 documents 表（最新版本作为当前文档）
    STORE.add_document(Document(
        docId="",
        projectId=project_id,
        docType=doc_type,
        title=f"{doc_type} {new_version}",
        content=content,
        source="company",
        sourceUrl="",
        trustLevel="official",
    ))
    # 链上存证
    evidence_id = uuid.uuid4().hex
    tx = CHAIN.record_evidence(
        evidence_hash=content_hash,
        evidence_id=evidence_id,
        evidence_type=evidence_type_to_int("PROJECT_DISCLOSURE"),
        timestamp=_now_ts(),
        project_id=project_id,
        doc_version=new_version,
        from_status=status_to_bytes32(parent_version or ""),
        to_status=status_to_bytes32(new_version),
    )
    # diff
    diff_result = None
    if latest:
        from src.projects.store import ProjectStore as _PS
        diff_result = diff_versions(latest, {"content": content, "version": new_version, "contentHash": content_hash, "changes": changes})
    return jsonify({
        "versionId": version_id,
        "version": new_version,
        "contentHash": content_hash,
        "parentVersion": parent_version,
        "diff": diff_result,
        "onChain": {
            "evidenceHash": content_hash,
            "evidenceId": evidence_id,
            "txHash": tx.tx_hash,
            "blockNumber": tx.block_number,
            "status": tx.status,
        },
    })


@app.route("/api/version/list", methods=["GET"])
def api_version_list():
    project_id = request.args.get("projectId", "")
    doc_type = request.args.get("docType", "")
    return jsonify({"versions": STORE.list_versions(project_id, doc_type)})


# ─────────── API：链 ───────────


@app.route("/api/proof/<evidence_hash>", methods=["GET"])
def api_proof(evidence_hash: str):
    exists, rec = CHAIN.verify(evidence_hash)
    return jsonify({
        "evidenceHash": evidence_hash,
        "onChain": {"exists": exists, "record": rec} if exists else {"exists": False, "record": {}},
        "mode": CHAIN_MODE,
    })


@app.route("/api/chain/status", methods=["GET"])
def api_chain_status():
    status = CHAIN.status() if hasattr(CHAIN, "status") else None
    if status is None:
        return jsonify({"mode": CHAIN_MODE, "contractAddress": CONTRACT_ADDRESS})
    return jsonify({
        "mode": status.mode,
        "contractAddress": status.contract_address,
        "network": status.network,
        "latestBlock": status.latest_block,
        "explorer": status.explorer,
    })


@app.route("/api/evidence", methods=["GET"])
def api_evidence_list():
    return jsonify({
        "total": CHAIN.total_evidence() if hasattr(CHAIN, "total_evidence") else 0,
    })


# ─────────── API：演示 ───────────


@app.route("/api/seed", methods=["POST"])
def api_seed():
    apply_seed(STORE)
    return jsonify({"status": "ok", "projects": STORE.list_projects()})


@app.route("/api/i18n", methods=["GET"])
def api_i18n():
    lang = _lang()
    return jsonify({"lang": lang, "dict": get_dict(lang)})


# ─────────── 启动 ───────────


if __name__ == "__main__":
    port = int(os.getenv("PORT", "4000"))
    print(f"[TokenTruth] http://127.0.0.1:{port} | mode={CHAIN_MODE} | contract={CONTRACT_ADDRESS}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
