"""DeepSeek LLM 客户端（OpenAI 兼容协议）。

使用 requests 直接调用，避免引入 openai SDK 依赖；
如需使用 OpenAI / 智谱 / 通义千问 / DeepSeek 等任意兼容服务，
只需修改 DEEPSEEK_BASE_URL 和 DEEPSEEK_MODEL。
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_TIMEOUT = 20


@dataclass
class LLMResponse:
    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    raw: Optional[Dict[str, Any]] = None


class DeepSeekClient:
    """DeepSeek API 客户端，支持 mock 降级。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> None:
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = (base_url or os.getenv("DEEPSEEK_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.model = model or os.getenv("DEEPSEEK_MODEL") or DEFAULT_MODEL
        self.timeout = int(timeout or os.getenv("DEEPSEEK_TIMEOUT") or DEFAULT_TIMEOUT)

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 800,
        response_format: Optional[Dict[str, str]] = None,
    ) -> LLMResponse:
        """调用 chat completions 接口。"""
        if not self.enabled:
            raise RuntimeError("DeepSeek API key 未配置（DEEPSEEK_API_KEY）")
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if response_format:
            body["response_format"] = response_format

        import requests
        t0 = time.time()
        r = requests.post(url, headers=headers, json=body, timeout=self.timeout)
        latency = int((time.time() - t0) * 1000)
        if r.status_code != 200:
            raise RuntimeError(f"DeepSeek API {r.status_code}: {r.text[:300]}")
        data = r.json()
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return LLMResponse(
            text=text,
            model=self.model,
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            latency_ms=latency,
            raw=data,
        )


# ---------- Prompt 模板 ----------

QA_SYSTEM_PROMPT = """你是 TokenTruth 的 AI 投研助手，专注于"让投资者问得明白、让项目方讲得清楚"。

## 工作原则
1. **只基于下方"项目资料"回答**。资料未提及的内容必须明确说"项目资料中未提及"；
2. **每条结论都要带引用**：必须用 [N] 标注引用了哪条资料，N 是资料前的编号；
3. **优先官方资料**（trustLevel=official），其次市场/新闻，最次社区观点；
4. **不确定时降低置信度**，并在 `risks` 中说明信息缺口或冲突；
5. **不要给投资建议**（"该买/该卖"），只解释信息；
6. **承认不知道**：缺资料就说"项目资料中未提及"，不要编造。

## 回答结构（严格 JSON）
```json
{
  "conclusion": "直接回答问题的结论（1-2 句话）",
  "reasoning": "推理过程（说明如何从资料推导）",
  "citationIndexes": [1, 3],
  "risks": ["该答案的潜在不确定性 1", "..."],
  "confidence": "high | medium | low",
  "followups": ["建议追问 1", "建议追问 2"]
}
```

只输出合法 JSON，不要输出其他文字、Markdown 代码块、解释。"""


def build_qa_messages(
    project: Dict[str, Any],
    question: str,
    context_chunks: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """构造 QA 的 messages 列表。"""
    # 拼装知识库上下文
    context_lines = [
        f"项目：{project.get('name', '?')}（{project.get('symbol', '?')}）",
        f"赛道：{project.get('sector', '?')}",
        f"简介：{project.get('description', '?')[:300]}",
        "",
        "## 项目资料（按可信度排序）",
    ]
    for i, c in enumerate(context_chunks, 1):
        trust = c.get("trustLevel", "official")
        dt = c.get("docType", "")
        title = c.get("title", "")
        ver = c.get("version", "")
        excerpt = (c.get("excerpt") or c.get("content") or "")[:1200]
        context_lines.append(
            f"[{i}] ({dt} · {trust} · {ver}) {title}\n{excerpt}"
        )
    user = (
        f"{chr(10).join(context_lines)}\n\n"
        f"## 用户问题\n{question}\n\n"
        "请按 JSON 格式回答："
    )
    return [
        {"role": "system", "content": QA_SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


_JSON_BLOCK = re.compile(r"\{[\s\S]*\}")


def parse_json_response(text: str) -> Dict[str, Any]:
    """从 LLM 输出提取 JSON（容错：去掉 markdown 围栏）。"""
    s = text.strip()
    # 去 ```json ... ``` 围栏
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
        s = re.sub(r"\n?```$", "", s)
    # 提取首个 JSON object
    m = _JSON_BLOCK.search(s)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        # 尝试更宽松：替换中文逗号
        s2 = m.group(0).replace("，", ",").replace("：", ":")
        try:
            return json.loads(s2)
        except json.JSONDecodeError:
            return {}


def citation_indexes_to_docs(
    indexes: List[int], context_chunks: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """把 LLM 输出的 [1,3] 转换为完整的引用字典列表。"""
    out: List[Dict[str, Any]] = []
    for i in indexes or []:
        if 1 <= i <= len(context_chunks):
            c = context_chunks[i - 1]
            out.append(c)
    return out
