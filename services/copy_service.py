import json
from pathlib import Path
from typing import Any

from services.model_clients.text_client import chat_json


def _load_prompt(filename: str, fallback: str) -> str:
    path = Path("prompts") / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return fallback


def _normalize_copy(data: dict[str, Any], image_count: int) -> dict[str, Any]:
    pages = data.get("pages") or []
    normalized_pages = []
    for index, page in enumerate(pages[:image_count], start=1):
        page_type = page.get("type") or ("cover" if index == 1 else "content")
        if index == image_count:
            page_type = "ending" if image_count > 2 else page_type
        normalized_pages.append(
            {
                "page": int(page.get("page") or index),
                "type": page_type,
                "main_text": str(page.get("main_text") or "").strip(),
                "sub_text": str(page.get("sub_text") or "").strip(),
                "visual_instruction": str(page.get("visual_instruction") or "").strip(),
            }
        )

    while len(normalized_pages) < image_count:
        index = len(normalized_pages) + 1
        normalized_pages.append(
            {
                "page": index,
                "type": "cover" if index == 1 else ("ending" if index == image_count else "content"),
                "main_text": data.get("title", "") if index == 1 else f"第 {index} 页",
                "sub_text": "",
                "visual_instruction": "保持参考图风格，排版简洁清晰。",
            }
        )

    hashtags = data.get("hashtags") or []
    if isinstance(hashtags, str):
        hashtags = [tag.strip("# ") for tag in hashtags.split() if tag.strip()]

    return {
        "title": str(data.get("title") or "").strip(),
        "body": str(data.get("body") or "").strip(),
        "hashtags": [str(tag).strip("# ") for tag in hashtags if str(tag).strip()],
        "pages": normalized_pages,
    }


def generate_note_copy(
    topic: str,
    audience: str | None = None,
    tone: str | None = None,
    image_count: int = 3,
    style_profile: dict | None = None,
) -> dict[str, Any]:
    user_payload = {
        "topic": topic,
        "audience": audience or "小红书普通用户",
        "tone": tone or "真诚、实用、不夸张",
        "image_count": image_count,
        "style_profile": style_profile or {},
        "output_schema": {
            "title": "字符串，20字以内更好",
            "body": "字符串，分段正文，适合小红书发布",
            "hashtags": ["标签1", "标签2"],
            "pages": [
                {
                    "page": 1,
                    "type": "cover/content/ending",
                    "main_text": "图片主标题，尽量短",
                    "sub_text": "图片副标题，尽量短",
                    "visual_instruction": "给图片模型的视觉说明",
                }
            ],
        },
    }

    system_prompt = _load_prompt(
        "copywriting_prompt.txt",
        "你是一个资深小红书图文策划。请输出严格 JSON。",
    )
    data = chat_json(system_prompt, json.dumps(user_payload, ensure_ascii=False))
    note = _normalize_copy(data, image_count)
    if not note["title"] or not note["body"]:
        raise RuntimeError("文案模型返回缺少 title 或 body。")
    return note
