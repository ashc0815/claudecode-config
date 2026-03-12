"""Audit module — Claude Sonnet structured analysis with prompt versioning."""

import json
import logging
import random

import httpx

from . import db
from .config import settings

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


def _select_prompt() -> tuple[str, str]:
    """Select a prompt version (supports A/B testing).

    Returns (prompt_text, version_tag).
    """
    try:
        prompts = db.get_active_prompts()
    except Exception:
        prompts = []

    if not prompts:
        # Fallback to hardcoded default
        return _DEFAULT_PROMPT, "v1.0-fallback"

    if len(prompts) == 1:
        return prompts[0]["prompt_text"], prompts[0]["version_tag"]

    # A/B split by traffic_pct
    roll = random.randint(1, 100)
    cumulative = 0
    for p in prompts:
        cumulative += p.get("traffic_pct", 0)
        if roll <= cumulative:
            return p["prompt_text"], p["version_tag"]

    return prompts[0]["prompt_text"], prompts[0]["version_tag"]


async def analyze(ocr_text: str, ocr_structured: dict | None = None) -> dict:
    """Send OCR text to Claude for structured audit analysis.

    Returns:
        {
            "structured": { ... },       # Parsed fields
            "risk_flags": [ ... ],        # AI-identified risks
            "ai_reasoning": "...",        # Explanation
            "prompt_version": "v1.0",
            "raw_response": "..."
        }
    """
    prompt_text, version_tag = _select_prompt()

    user_message = f"请分析以下凭证内容:\n\n{ocr_text}"
    if ocr_structured:
        user_message += f"\n\nOCR 已提取的结构化数据:\n{json.dumps(ocr_structured, ensure_ascii=False, indent=2)}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            ANTHROPIC_API_URL,
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 2000,
                "system": prompt_text,
                "messages": [{"role": "user", "content": user_message}],
            },
        )
        resp.raise_for_status()
        data = resp.json()

    raw_text = data["content"][0]["text"]

    # Parse JSON from Claude's response
    structured = _parse_json_response(raw_text)

    return {
        "structured": structured,
        "risk_flags": structured.get("risk_flags", []),
        "ai_reasoning": structured.get("ai_reasoning", ""),
        "prompt_version": version_tag,
        "raw_response": raw_text,
    }


def _parse_json_response(text: str) -> dict:
    """Extract JSON from Claude's response, handling markdown code blocks."""
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from ```json ... ``` block
    import re
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding first { ... } block
    brace_start = text.find("{")
    if brace_start >= 0:
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[brace_start : i + 1])
                    except json.JSONDecodeError:
                        break

    logger.warning("Failed to parse JSON from Claude response")
    return {
        "vendor_name": "",
        "amount": 0,
        "currency": "CNY",
        "risk_flags": [],
        "ai_reasoning": text[:500],
        "parse_error": True,
    }


_DEFAULT_PROMPT = """你是一个专业的财务审计助手。请分析以下凭证的 OCR 提取结果，识别潜在的财务风险。

输入：OCR 提取的凭证文字内容
输出：严格按照以下 JSON 格式返回

{
  "vendor_name": "供应商名称",
  "amount": 数字金额,
  "currency": "CNY",
  "invoice_number": "发票号",
  "invoice_date": "YYYY-MM-DD",
  "expense_type": "费用类型",
  "items": [{"description": "项目描述", "amount": 金额}],
  "risk_flags": [
    {
      "rule": "规则标识符",
      "severity": "critical/high/medium/low",
      "confidence": 0.0-1.0,
      "detail": "具体发现描述"
    }
  ],
  "ai_reasoning": "综合分析说明",
  "citations": ["引用凭证中的具体文字"]
}

重点关注：
1. 金额是否接近常见审批阈值（如 ¥5,000 / ¥10,000 / ¥50,000）
2. 发票日期是否为周末或节假日
3. 金额是否为整数（无零头可能是虚构）
4. 供应商信息是否完整
5. 是否有明显的费用类型不匹配"""
