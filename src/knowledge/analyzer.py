"""基本面 / 市场 / 社区综合分析。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from ..projects.store import ProjectStore


@dataclass
class AnalysisResult:
    projectId: str
    fundamentals: Dict[str, Any] = field(default_factory=dict)
    market: Dict[str, Any] = field(default_factory=dict)
    community: Dict[str, Any] = field(default_factory=dict)
    riskFactors: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""


class Analyzer:
    """基于项目资料的综合分析（确定性实现）。"""

    def __init__(self, store: ProjectStore) -> None:
        self.store = store

    def analyze(self, project_id: str) -> AnalysisResult:
        project = self.store.get_project(project_id)
        if not project:
            return AnalysisResult(projectId=project_id, summary="项目不存在")

        # 基本面
        docs = self.store.list_documents(project_id)
        docs_by_type: Dict[str, List[Dict[str, Any]]] = {}
        for d in docs:
            docs_by_type.setdefault(d["docType"], []).append(d)

        # 资料完整度
        expected_types = ["whitepaper", "tokenomics", "unlock", "announcement"]
        coverage = {t: (t in docs_by_type) for t in expected_types}
        completeness = sum(1 for v in coverage.values() if v) / len(expected_types)

        # 最新版本
        latest_versions: Dict[str, Dict[str, Any]] = {}
        for t in expected_types:
            v = self.store.latest_version(project_id, t)
            if v:
                latest_versions[t] = v

        # 团队（从白皮书提取）
        team = self._extract_team(docs_by_type.get("whitepaper", [{}])[0].get("content", ""))

        # 融资
        funding = self._extract_funding(docs_by_type.get("whitepaper", [{}])[0].get("content", ""))

        # 市场（mock 数据：MVP 不接入真实行情）
        market = {
            "sector": project.get("sector", ""),
            "tier": "Top 100 (示例)",
            "exchangeListings": ["DEX (Uniswap)"],
            "circulatingSupply": "62% (示例)",
            "note": "MVP 演示数据；真实接入需行情 API",
        }

        # 社区
        community_docs = docs_by_type.get("community", [])
        community = {
            "newsCount": len(docs_by_type.get("news", [])),
            "communityPostCount": len(community_docs),
            "sentiment": "中性" if not community_docs else "偏积极",
            "signals": [
                {
                    "type": "news",
                    "content": d["title"],
                    "source": d["source"],
                    "trustLevel": d["trustLevel"],
                }
                for d in docs_by_type.get("news", [])[:3]
            ],
        }

        # 风险因素
        risk_factors: List[Dict[str, Any]] = []
        if not coverage.get("whitepaper"):
            risk_factors.append({"factor": "白皮书缺失", "severity": "high", "note": "未找到白皮书资料"})
        if not coverage.get("tokenomics"):
            risk_factors.append({"factor": "代币经济缺失", "severity": "high", "note": "未找到代币经济说明"})
        if not coverage.get("unlock"):
            risk_factors.append({"factor": "解锁计划缺失", "severity": "medium", "note": "未找到解锁计划"})
        if completeness < 0.5:
            risk_factors.append({"factor": "资料完整度低", "severity": "medium", "note": f"完整度 {completeness:.0%}"})
        if not team:
            risk_factors.append({"factor": "团队信息缺失", "severity": "medium", "note": "白皮书未提及团队"})

        summary = (
            f"{project['name']}（{project['symbol']}）资料完整度 {completeness:.0%}，"
            f"已收录 {len(docs)} 份资料、{len(latest_versions)} 个版本。"
            f"当前识别 {len(risk_factors)} 项风险因素。"
        )

        return AnalysisResult(
            projectId=project_id,
            fundamentals={
                "team": team,
                "funding": funding,
                "useCases": self._extract_usecases(docs_by_type.get("whitepaper", [{}])[0].get("content", "")),
                "dataCompleteness": completeness,
                "latestVersion": {t: v["version"] for t, v in latest_versions.items()},
            },
            market=market,
            community=community,
            riskFactors=risk_factors,
            summary=summary,
        )

    def _extract_team(self, content: str) -> List[Dict[str, str]]:
        team = []
        for line in content.splitlines():
            if "团队" in line or "Team" in line or "Founder" in line or "CEO" in line:
                team.append({"info": line.strip()[:200]})
        return team[:5]

    def _extract_funding(self, content: str) -> Dict[str, Any]:
        funding = {"rounds": []}
        import re
        for m in re.finditer(r"(种子|天使|Series [A-Z]|Pre-Seed|战略)[^。\n]{0,80}", content):
            funding["rounds"].append(m.group(0)[:120])
        return funding

    def _extract_usecases(self, content: str) -> List[str]:
        cases = []
        for line in content.splitlines():
            if any(kw in line for kw in ["场景", "应用", "用例", "use case", "use-case"]):
                cases.append(line.strip()[:200])
        return cases[:5]
