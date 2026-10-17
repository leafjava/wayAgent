"""内容辅助生成（确定性格式 + 模板填充）。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..projects.store import ProjectStore


TEMPLATES = {
    "intro": {
        "title": "项目介绍",
        "structure": ["一句话定位", "目标用户", "核心价值", "差异化"],
    },
    "video_script": {
        "title": "60 秒视频脚本",
        "structure": ["开场 5 秒", "痛点 10 秒", "解决方案 25 秒", "CTA 20 秒"],
    },
    "press_release": {
        "title": "新闻稿模板",
        "structure": ["标题", "副标题", "导语", "主体 3 段", "项目方 quote", "联系信息"],
    },
    "social_x": {
        "title": "X 推文（280 字内）",
        "structure": ["Hook", "核心信息", "标签"],
    },
    "social_tg": {
        "title": "Telegram 频道帖",
        "structure": ["标题", "正文", "CTA"],
    },
    "faq": {
        "title": "投资者 FAQ",
        "structure": ["Q1: 这家公司靠什么赚钱？", "Q2: 代币有什么权利？", "Q3: 什么时候可以转让？", "Q4: 未来一年有哪些解锁？", "Q5: 当前主要风险？"],
    },
}


class ContentGenerator:
    """基于项目知识库 + 模板生成内容。"""

    def __init__(self, store: ProjectStore) -> None:
        self.store = store

    def list_templates(self) -> List[Dict[str, str]]:
        return [{"key": k, "title": v["title"], "structure": v["structure"]} for k, v in TEMPLATES.items()]

    def generate(self, project_id: str, template_key: str, audience: str = "investor") -> Dict[str, Any]:
        if template_key not in TEMPLATES:
            return {"error": f"未知模板：{template_key}", "availableTemplates": list(TEMPLATES.keys())}
        project = self.store.get_project(project_id)
        if not project:
            return {"error": "项目不存在"}
        template = TEMPLATES[template_key]
        sections: List[Dict[str, str]] = []
        for heading in template["structure"]:
            body = self._fill_section(heading, project, template_key, audience)
            sections.append({"heading": heading, "body": body})
        return {
            "template": template_key,
            "title": template["title"],
            "audience": audience,
            "projectId": project_id,
            "projectName": project["name"],
            "sections": sections,
            "disclaimer": "本内容为模板生成，请项目方审校后发布。",
        }

    def _fill_section(self, heading: str, project: Dict[str, Any], template_key: str, audience: str) -> str:
        """简单模板填充：把项目名/符号/行业拼到骨架中。"""
        name = project["name"]
        symbol = project["symbol"]
        sector = project.get("sector", "加密项目")
        description = project.get("description", "")
        if "一句话定位" in heading or "Hook" in heading or "标题" == heading:
            return f"{name}（{symbol}）：{description[:80] or sector + '领域的项目'}。"
        if "目标用户" in heading:
            return f"面向 {sector} 生态的用户与开发者。"
        if "核心价值" in heading or "解决方案" in heading:
            return f"{description[:200] or '提供差异化能力与可持续的代币经济。'}"
        if "差异化" in heading:
            return f"{sector} 领域差异化定位；具体见白皮书与代币经济模型。"
        if "开场" in heading or "痛点" in heading:
            return f"{sector} 行业当前痛点：效率、信任与可持续性。"
        if "CTA" in heading:
            return f"访问 {project.get('website') or '官网'} 获取更多信息。"
        if "副标题" in heading:
            return f"{name} 在 {sector} 持续迭代，本期更新亮点：…"
        if "导语" in heading:
            return f"{name} 今日宣布…（请补充具体事件）"
        if "主体" in heading or "项目方 quote" in heading or "联系信息" in heading:
            return "（请项目方补充具体内容）"
        if "核心信息" in heading:
            return f"{name}（{symbol}）— {description[:100] or sector}"
        if "标签" in heading:
            return f"#{symbol} #{sector} #TokenTruth"
        if "正文" in heading:
            return f"{name} 最新动态：……（请补充）"
        if heading.startswith("Q") and ":" in heading:
            return f"（请项目方按知识库回答：{heading.split(':',1)[1].strip()}）"
        return "（请项目方补充）"
