"""风险状态管理引擎。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..projects.store import ProjectStore


STATUSES = ["HEALTHY", "NEEDS_REVIEW", "HIGH_RISK"]

STATUS_LABEL = {
    "HEALTHY": "健康",
    "NEEDS_REVIEW": "待复核",
    "HIGH_RISK": "高风险",
}

STATUS_COLOR = {
    "HEALTHY": "#10b981",
    "NEEDS_REVIEW": "#f59e0b",
    "HIGH_RISK": "#ef4444",
}


@dataclass
class RiskFactors:
    disclosureRecency: float = 0.0   # 0~1，1 表示最近 30 天有更新
    unlockPressure: float = 0.0       # 0~1，1 表示 90 天内大额解锁
    productProgress: float = 0.5      # 0~1，1 表示路线图按计划
    marketVolatility: float = 0.3     # 0~1，1 表示市场异常
    communitySentiment: float = 0.5   # 0~1，1 表示社区正面
    dataConsistency: float = 1.0      # 0~1，1 表示资料一致
    completeness: float = 1.0         # 0~1，1 表示资料完整


class StatusEngine:
    """根据项目资料综合计算风险状态。"""

    def __init__(self, store: ProjectStore) -> None:
        self.store = store

    def evaluate(self, project_id: str) -> Dict[str, Any]:
        docs = self.store.list_documents(project_id)
        if not docs:
            factors = RiskFactors()
            factors.completeness = 0.0
            return self._format(project_id, factors, "资料缺失，建议补充后重新评估")

        # 1. 披露及时性
        from time import time
        now = int(time())
        latest_doc = max(docs, key=lambda d: d["createdAt"])
        recency_days = (now - latest_doc["createdAt"]) / 86400
        disclosure_recency = max(0.0, 1.0 - recency_days / 90)

        # 2. 资料完整度
        expected = {"whitepaper", "tokenomics", "unlock", "announcement"}
        actual = {d["docType"] for d in docs}
        completeness = len(expected & actual) / len(expected)

        # 3. 解锁压力（mock：基于 unlock 资料数量）
        unlock_docs = [d for d in docs if d["docType"] == "unlock"]
        unlock_pressure = min(1.0, len(unlock_docs) * 0.5)

        # 4. 社区情绪（基于 community 类型文档数量）
        community_docs = [d for d in docs if d["docType"] in ("community", "news")]
        community_sentiment = max(0.0, 1.0 - len(community_docs) * 0.1)  # 文档越多越负面（mock）

        # 5. 产品进展（基于 announcement）
        announcements = [d for d in docs if d["docType"] == "announcement"]
        product_progress = min(1.0, len(announcements) * 0.3 + 0.4)

        # 6. 一致性（版本变化是否剧烈）
        latest_tokenomics = self.store.latest_version(project_id, "tokenomics")
        data_consistency = 1.0
        if latest_tokenomics and latest_tokenomics.get("changes"):
            if len(latest_tokenomics["changes"]) > 3:
                data_consistency = 0.5

        factors = RiskFactors(
            disclosureRecency=disclosure_recency,
            unlockPressure=unlock_pressure,
            productProgress=product_progress,
            marketVolatility=0.3,
            communitySentiment=community_sentiment,
            dataConsistency=data_consistency,
            completeness=completeness,
        )

        # 综合评分（0~100，数值越低越健康）
        # HEALTHY ≥ 70，NEEDS_REVIEW 50~70，HIGH_RISK < 50
        score = (
            disclosure_recency * 30
            + (1 - unlock_pressure) * 15
            + product_progress * 15
            + (1 - community_sentiment) * 10
            + data_consistency * 15
            + completeness * 15
        )
        if score >= 70:
            status = "HEALTHY"
        elif score >= 50:
            status = "NEEDS_REVIEW"
        else:
            status = "HIGH_RISK"

        # 检测状态变更
        prev = self.store.get_risk(project_id)
        changed = (prev is None) or (prev["status"] != status)
        from_status = prev["status"] if prev else "INIT"
        self.store.upsert_risk(project_id, status, score, factors.__dict__)

        return self._format(
            project_id, factors, f"综合评分 {score:.1f}，状态 {STATUS_LABEL[status]}",
            score=score, status=status, fromStatus=from_status, changed=changed,
        )

    def _format(self, project_id: str, factors: RiskFactors, note: str, **extra) -> Dict[str, Any]:
        result = {
            "projectId": project_id,
            "factors": factors.__dict__,
            "note": note,
        }
        result.update(extra)
        return result
