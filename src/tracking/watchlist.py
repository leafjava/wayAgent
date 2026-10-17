"""关注列表 + 授权执行服务。"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..projects.store import ProjectStore


PLATFORMS = [
    {"id": "uniswap", "name": "Uniswap (DEX)", "supportedActions": ["swap", "add_liquidity", "remove_liquidity"]},
    {"id": "okx", "name": "OKX (CEX)", "supportedActions": ["buy", "sell", "subscribe"]},
    {"id": "binance", "name": "Binance (CEX)", "supportedActions": ["buy", "sell", "subscribe"]},
    {"id": "bybit", "name": "Bybit (CEX)", "supportedActions": ["buy", "sell", "subscribe"]},
]


@dataclass
class InvestmentPlan:
    projectId: str
    budget: float
    riskPreference: str  # conservative / balanced / aggressive
    trackingFrequency: str  # daily / weekly / on_event
    notes: str = ""


class WatchlistService:
    """关注列表 + 投资计划 + 授权执行（mock）。"""

    def __init__(self, store: ProjectStore) -> None:
        self.store = store

    # -------- Watchlist --------
    def add(self, project_id: str, note: str = "", budget: float = 0.0) -> Dict[str, Any]:
        return {"watchId": self.store.add_watch(project_id, note, budget), "projectId": project_id}

    def list(self) -> List[Dict[str, Any]]:
        items = self.store.list_watch()
        for it in items:
            project = self.store.get_project(it["project_id"])
            it["project"] = project
        return items

    def remove(self, watch_id: str) -> bool:
        return self.store.remove_watch(watch_id)

    # -------- Investment plan (mock) --------
    def save_plan(self, project_id: str, plan: InvestmentPlan) -> Dict[str, Any]:
        """保存投资计划。MVP 不持久化计划实体，只做摘要展示。"""
        return {
            "planId": uuid.uuid4().hex,
            "projectId": project_id,
            "budget": plan.budget,
            "riskPreference": plan.riskPreference,
            "trackingFrequency": plan.trackingFrequency,
            "notes": plan.notes,
            "createdAt": int(time.time()),
        }

    # -------- Authorized execution (mock) --------
    def request_execution(
        self,
        project_id: str,
        platform: str,
        action_type: str,
        user_label: str = "",
    ) -> Dict[str, Any]:
        """用户授权一次执行：返回 consent 记录 + 跳转 URL + 链上存证。"""
        # 计算 evidence hash
        payload = {
            "projectId": project_id,
            "platform": platform,
            "actionType": action_type,
            "userLabel": user_label,
            "timestamp": int(time.time()),
        }
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        evidence_hash = "0x" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        consent = self.store.add_consent(project_id, platform, action_type, user_label, evidence_hash)
        # 跳转 URL（MVP 演示）
        consent["redirectUrl"] = f"https://example.invalid/{platform}/{action_type}?consent={consent['consentId']}"
        return consent

    def list_consents(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.store.list_consents(project_id)

    def update_consent_chain(self, consent_id: str, tx_hash: str, status: str) -> None:
        self.store.update_consent_chain(consent_id, tx_hash, status)
