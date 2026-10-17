"""自然语言问答引擎。

MVP 模式（无 LLM key）：关键词检索 + 模板化回答，100% 可复现；
LLM 模式（DeepSeek key 已配置）：检索 top-5 资料作为 context，调 LLM 生成 JSON 答案；
LLM 失败时自动降级到本地模板。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..projects.store import ProjectStore

log = logging.getLogger(__name__)

# 类型前向引用：避免循环 import
try:
    from .llm_client import (
        DeepSeekClient, LLMResponse,
        build_qa_messages, parse_json_response, citation_indexes_to_docs,
    )
except ImportError:  # pragma: no cover
    DeepSeekClient = None  # type: ignore
    LLMResponse = None  # type: ignore
    build_qa_messages = None  # type: ignore
    parse_json_response = None  # type: ignore
    citation_indexes_to_docs = None  # type: ignore


@dataclass
class Citation:
    docId: str
    docType: str
    title: str
    trustLevel: str
    source: str
    sourceUrl: str
    excerpt: str
    version: str = ""


@dataclass
class Answer:
    question: str
    conclusion: str
    citations: List[Citation] = field(default_factory=list)
    confidence: str = "low"  # low / medium / high
    risks: List[str] = field(default_factory=list)
    reasoning: str = ""
    suggestedFollowups: List[str] = field(default_factory=list)


# 关键词 → 检索意图
INTENT_RULES: List[Tuple[str, List[str], str]] = [
    ("revenue", ["赚钱", "收入", "revenue", "商业模式", "business model", "盈利"], "revenue"),
    ("token_rights", ["代币", "权利", "token", "权利", "governance", "投票", "分红", "权益"], "token_rights"),
    ("transfer_restriction", ["转让", "transfer", "解锁", "unlock", "vesting", "锁仓", "限制"], "transfer_restriction"),
    ("unlock_schedule", ["解锁", "vesting", "cliff", "释放", "schedule", "流通", "未来"], "unlock_schedule"),
    ("risk", ["风险", "risk", "危险", "隐患", "问题"], "risk"),
    ("team", ["团队", "team", "创始人", "founder", "CEO"], "team"),
    ("price", ["价格", "price", "上涨", "下跌", "市场", "市值", "流通"], "price"),
    ("use_of_funds", ["资金", "funds", "用", "融资", "raised", "tier"], "use_of_funds"),
    ("competitor", ["竞品", "competitor", "对比", "类似", "compete"], "competitor"),
    ("update", ["更新", "修改", "update", "change", "新增", "删除", "新版本"], "update"),
    ("community", ["社区", "community", "Twitter", "Discord", "Telegram", "推特"], "community"),
]


class QAEngine:
    """根据用户问题检索项目资料并生成结构化答案。

    - LLM 模式（DeepSeek key 已配置）：检索 top-5 资料作为 context，调 LLM 生成 JSON 答案
    - 本地模式（无 key 或 LLM 失败）：按意图模板 + 关键词匹配，100% 可复现
    """

    def __init__(self, store: ProjectStore, llm_client: Optional["DeepSeekClient"] = None) -> None:
        self.store = store
        self.llm = llm_client  # type: ignore[name-defined]

    def _detect_intent(self, question: str) -> List[str]:
        q = question.lower()
        intents: List[str] = []
        for intent, keywords, _ in INTENT_RULES:
            if any(kw.lower() in q for kw in keywords):
                intents.append(intent)
        if not intents:
            intents = ["general"]
        return intents

    def _find_relevant_docs(self, project_id: str, intent: str, question: str) -> List[Dict[str, Any]]:
        """按意图 + 关键词双路匹配。"""
        docs = self.store.list_documents(project_id)
        # 加入所有版本
        all_versions: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        for d in docs:
            vs = self.store.list_versions(project_id, d["docType"])
            for v in vs:
                all_versions.append((d, v))

        # 关键词集合
        question_tokens = set(re.findall(r"[\w一-鿿]+", question.lower()))

        # 意图 → docType 偏好
        intent_pref = {
            "revenue": ["whitepaper", "announcement"],
            "token_rights": ["whitepaper", "tokenomics"],
            "transfer_restriction": ["tokenomics", "unlock"],
            "unlock_schedule": ["unlock", "tokenomics"],
            "risk": ["announcement", "whitepaper", "news"],
            "team": ["whitepaper", "announcement"],
            "price": ["news", "community"],
            "use_of_funds": ["whitepaper", "announcement"],
            "competitor": ["announcement", "whitepaper"],
            "update": ["whitepaper", "tokenomics", "announcement"],
            "community": ["community", "news"],
        }
        pref_types = intent_pref.get(intent, [])

        scored: List[Tuple[float, Dict[str, Any], Dict[str, Any]]] = []
        for d, v in all_versions:
            score = 0.0
            # docType 偏好
            if d["docType"] in pref_types:
                score += 2.0
            # 关键词命中
            content_lower = v["content"].lower()
            matched = sum(1 for tok in question_tokens if len(tok) > 1 and tok in content_lower)
            score += matched * 0.5
            # 信任度加权
            trust_w = {"official": 1.0, "market": 0.7, "news": 0.6, "community": 0.4, "ai": 0.2}.get(d["trustLevel"], 0.5)
            score *= trust_w
            if score > 0:
                scored.append((score, d, v))
        scored.sort(key=lambda x: -x[0])
        return scored[:5]  # top 5

    def _answer_revenue(self, project_id: str, project: Dict[str, Any], citations: List[Citation]) -> Answer:
        conclusion = f"{project['name']}（{project['symbol']}）的收入来源主要在白皮书与公告中披露。详见引用资料。"
        risks = [
            "代币白皮书与公告中可能未列明全部收入来源；建议参考项目最新季度报告。",
            "收入数据若为推测，请以官方披露为准。",
        ]
        reasoning = "在白皮书与项目方公告中检索关键词（收入、商业模式、revenue），按可信度排序引用。"
        return Answer(
            question="", conclusion=conclusion, citations=citations,
            confidence="high" if citations and citations[0].trustLevel == "official" else "medium",
            risks=risks, reasoning=reasoning,
            suggestedFollowups=["代币有什么用途？", "代币持有人有哪些权利？"],
        )

    def _answer_token_rights(self, project_id: str, project: Dict[str, Any], citations: List[Citation]) -> Answer:
        conclusion = f"代币 {project['symbol']} 的持有人权利主要在白皮书与代币经济模型中定义。常见权利包括治理投票、费用折扣、生态激励、销毁分红等；具体以项目方披露为准。"
        risks = [
            "白皮书条款不等于法律权利；具体权利以司法管辖区的链上合约与官方公告为准。",
            "代币权利可能随代币规则变更而调整，请关注最新版本。",
        ]
        return Answer(
            question="", conclusion=conclusion, citations=citations,
            confidence="high" if citations and citations[0].trustLevel == "official" else "medium",
            risks=risks,
            reasoning="在代币经济模型与白皮书中检索（治理、投票、分红、销毁等），按可信度排序。",
            suggestedFollowups=["什么时候可以转让？", "未来一年有哪些解锁？"],
        )

    def _answer_transfer(self, project_id: str, project: Dict[str, Any], citations: List[Citation]) -> Answer:
        conclusion = f"代币 {project['symbol']} 的转让限制主要在代币经济与解锁计划中规定：通常包括 cliff 期、线性释放、锁仓期等。详情以引用资料中的最新版本为准。"
        risks = [
            "链上转账可能受智能合约代码限制（如转账白名单、税率）；请同时检查合约源代码。",
            "二级市场转让限制可能因司法管辖区而异。",
        ]
        return Answer(
            question="", conclusion=conclusion, citations=citations,
            confidence="high" if citations and citations[0].trustLevel == "official" else "medium",
            risks=risks,
            reasoning="在代币经济与解锁计划中检索（lockup、cliff、transfer restriction、锁仓）。",
            suggestedFollowups=["未来一年有哪些解锁？", "团队代币什么时候释放？"],
        )

    def _answer_unlock(self, project_id: str, project: Dict[str, Any], citations: List[Citation]) -> Answer:
        conclusion = f"代币 {project['symbol']} 的解锁计划记录在 unlock 类型资料中。请按时间表对照近期事件。"
        risks = [
            "大规模解锁可能造成短期流通量与价格压力，但仍需结合市场情绪综合判断。",
            "解锁计划可能调整，请参考最新版本与项目方公告。",
        ]
        return Answer(
            question="", conclusion=conclusion, citations=citations,
            confidence="medium",
            risks=risks,
            reasoning="在 unlock 类型资料中检索（vesting、unlock、cliff、释放）。",
            suggestedFollowups=["团队代币什么时候释放？", "项目方最近修改过代币规则吗？"],
        )

    def _answer_risk(self, project_id: str, project: Dict[str, Any], citations: List[Citation]) -> Answer:
        conclusion = f"根据引用资料，{project['name']} 当前主要风险包括：监管合规风险、合约代码风险、市场流动性风险、解锁压力。请结合项目方披露与第三方研究综合判断。"
        risks = [
            "本回答仅基于项目方披露资料；不构成投资建议。",
            "加密资产价格波动剧烈，请量力而行。",
        ]
        # 读取风险状态
        rs = self.store.get_risk(project_id)
        if rs:
            conclusion += f"\n\n当前项目风险状态：{rs['status']}（评分 {rs['score']}）。"
        return Answer(
            question="", conclusion=conclusion, citations=citations,
            confidence="high" if citations else "low",
            risks=risks,
            reasoning="在所有资料中检索风险相关关键词，结合项目风险状态评分。",
            suggestedFollowups=["代币有什么权利？", "未来一年有哪些解锁？"],
        )

    def _answer_general(self, project_id: str, project: Dict[str, Any], citations: List[Citation]) -> Answer:
        conclusion = f"关于 {project['name']}（{project['symbol']}）的这个问题，请参考以下引用资料。"
        return Answer(
            question="", conclusion=conclusion, citations=citations,
            confidence="low" if not citations else "medium",
            risks=["未匹配到明确意图，建议换个问法或参考项目方原始资料。"],
            reasoning="未检测到明确意图，按关键词匹配给出最相关资料。",
            suggestedFollowups=[
                "这家公司靠什么赚钱？",
                "我买的代币有什么权利？",
                "未来一年有哪些解锁？",
                "这个项目当前最大的风险是什么？",
            ],
        )

    def ask(
        self,
        project_id: str,
        question: str,
        prefer_llm: bool = True,
    ) -> Answer:
        project = self.store.get_project(project_id)
        if not project:
            return Answer(
                question=question, conclusion=f"未找到项目 {project_id}",
                confidence="low", risks=["项目不存在或已被删除"],
            )

        # 1) 先按本地检索拿 top 上下文（始终需要，供 LLM 使用 + 失败时直接出）
        contexts, citations = self._retrieve_contexts(project_id, question)

        # 2) 优先尝试 LLM
        if prefer_llm and self.llm and self.llm.enabled and contexts:
            try:
                return self._ask_with_llm(project, question, contexts, citations)
            except Exception as exc:  # noqa: BLE001
                log.warning("LLM 回答失败，降级到本地引擎：%s", exc)

        # 3) 降级到本地模板
        return self._ask_with_template(project_id, question, contexts, citations)

    # ------------------------------------------------------------------ #
    # 检索
    # ------------------------------------------------------------------ #

    def _retrieve_contexts(
        self, project_id: str, question: str
    ) -> Tuple[List[Dict[str, Any]], List[Citation]]:
        """按意图 + 关键词双路匹配，返回 (context_dicts, citations)。"""
        intents = self._detect_intent(question)

        all_scored: List[Tuple[float, Dict[str, Any], Dict[str, Any]]] = []
        seen = set()
        for intent in intents:
            for score, d, v in self._find_relevant_docs(project_id, intent, question):
                key = (d["docId"], v["versionId"])
                if key in seen:
                    continue
                seen.add(key)
                all_scored.append((score, d, v))
        all_scored.sort(key=lambda x: -x[0])

        contexts: List[Dict[str, Any]] = []
        citations: List[Citation] = []
        for score, d, v in all_scored[:5]:
            content = v["content"]
            excerpt = content[:200].replace("\n", " ").strip()
            if len(content) > 200:
                excerpt += "..."
            contexts.append({
                "docId": d["docId"],
                "docType": d["docType"],
                "title": d["title"],
                "trustLevel": d["trustLevel"],
                "source": d["source"],
                "sourceUrl": d["sourceUrl"],
                "version": v["version"],
                "excerpt": excerpt,
                "content": content[:4000],  # 喂给 LLM 的完整内容
            })
            citations.append(Citation(
                docId=d["docId"],
                docType=d["docType"],
                title=d["title"],
                trustLevel=d["trustLevel"],
                source=d["source"],
                sourceUrl=d["sourceUrl"],
                excerpt=excerpt,
                version=v["version"],
            ))
        return contexts, citations

    # ------------------------------------------------------------------ #
    # LLM 回答
    # ------------------------------------------------------------------ #

    def _ask_with_llm(
        self,
        project: Dict[str, Any],
        question: str,
        contexts: List[Dict[str, Any]],
        citations: List[Citation],
    ) -> Answer:
        messages = build_qa_messages(project, question, contexts)
        resp = self.llm.chat(
            messages,
            temperature=0.2,
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        data = parse_json_response(resp.text)
        if not data:
            raise RuntimeError(f"LLM 输出无法解析为 JSON：{resp.text[:200]}")
        # 映射 citation index → 完整引用
        used_indexes = data.get("citationIndexes") or []
        used_citations = citation_indexes_to_docs(used_indexes, contexts)
        if used_citations:
            # 把 used_citations 转 Citation
            used = [
                Citation(
                    docId=c["docId"], docType=c["docType"], title=c["title"],
                    trustLevel=c["trustLevel"], source=c["source"],
                    sourceUrl=c["sourceUrl"], excerpt=c["excerpt"], version=c["version"],
                ) for c in used_citations
            ]
        else:
            used = citations  # LLM 没给索引就用全部
        return Answer(
            question=question,
            conclusion=str(data.get("conclusion", "")).strip(),
            citations=used,
            confidence=str(data.get("confidence", "medium")).lower(),
            risks=list(data.get("risks") or []),
            reasoning=str(data.get("reasoning", "")).strip(),
            suggestedFollowups=list(data.get("followups") or []),
        )

    # ------------------------------------------------------------------ #
    # 本地模板（确定性）
    # ------------------------------------------------------------------ #

    def _ask_with_template(
        self,
        project_id: str,
        question: str,
        contexts: List[Dict[str, Any]],
        citations: List[Citation],
    ) -> Answer:
        intents = self._detect_intent(question)
        primary_intent = intents[0] if intents else "general"
        project = self.store.get_project(project_id) or {}
        handlers = {
            "revenue": self._answer_revenue,
            "token_rights": self._answer_token_rights,
            "transfer_restriction": self._answer_transfer,
            "unlock_schedule": self._answer_unlock,
            "risk": self._answer_risk,
            "general": self._answer_general,
        }
        if primary_intent not in handlers:
            primary_intent = "general"
        ans = handlers[primary_intent](project_id, project, citations)
        ans.question = question
        return ans
