import json
from pathlib import Path
from typing import Any

from services.model_clients.text_client import chat_json


def _load_prompt(filename: str, fallback: str) -> str:
    path = Path("prompts") / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return fallback


def _normalize_candidates(data: dict[str, Any], count: int) -> list[dict[str, Any]]:
    candidates = data.get("candidates") or []
    normalized: list[dict[str, Any]] = []

    for item in candidates:
        topic = str(item.get("topic") or "").strip()
        if not topic:
            continue
        selling_points = item.get("selling_points") or []
        ingredients_hint = item.get("ingredients_hint") or []
        if isinstance(selling_points, str):
            selling_points = [selling_points]
        if isinstance(ingredients_hint, str):
            ingredients_hint = [ingredients_hint]
        normalized.append(
            {
                "topic": topic,
                "reason": str(item.get("reason") or "").strip(),
                "selling_points": [str(value).strip() for value in selling_points if str(value).strip()],
                "ingredients_hint": [str(value).strip() for value in ingredients_hint if str(value).strip()],
                "difficulty": str(item.get("difficulty") or "简单").strip(),
            }
        )
        if len(normalized) >= count:
            break

    return normalized


def generate_topic_candidates_from_items(
    items: list[dict[str, Any]],
    count: int = 8,
    keyword: str = "减脂餐做法",
) -> list[dict[str, Any]]:
    if not items:
        raise RuntimeError("没有可用于提炼选题的小红书采集数据。")

    prompt = _load_prompt(
        "topic_from_xhs_prompt.txt",
        "请从小红书菜谱趋势中提炼原创选题，输出严格 JSON。",
    )
    payload = {
        "keyword": keyword,
        "count": count,
        "items": items[:50],
    }
    data = chat_json(prompt, json.dumps(payload, ensure_ascii=False), temperature=0.8)
    candidates = _normalize_candidates(data, count)
    if not candidates:
        raise RuntimeError("模型没有返回可用选题。")
    return candidates
