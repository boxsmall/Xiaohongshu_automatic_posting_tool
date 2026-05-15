import json
import re
from typing import Any

import requests

from config import settings


class TextGenerationError(RuntimeError):
    pass


def _model_candidates(model_id: str) -> list[str]:
    candidates = [
        model_id,
        "doubao-seed-2-0-lite-260215",
        "doubao-seed-2.0-lite",
        "doubao-seed-2-0-lite",
    ]
    return list(dict.fromkeys([item for item in candidates if item]))


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def chat_json(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    timeout: int = 90,
) -> dict[str, Any]:
    if settings.text_model_provider != "ark":
        raise TextGenerationError(f"暂不支持的文本模型供应商：{settings.text_model_provider}")
    if not settings.ark_api_key:
        raise TextGenerationError("缺少 ARK_API_KEY，请在 .env 中配置。")

    url = f"{settings.ark_base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.ark_api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": settings.text_model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "stream": False,
        "response_format": {"type": "json_object"},
    }

    last_response = None
    for model in _model_candidates(settings.text_model_id):
        payload["model"] = model
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if response.status_code < 400:
            break
        last_response = response
        if response.status_code == 404:
            continue
        if "response_format" in payload:
            retry_payload = dict(payload)
            retry_payload.pop("response_format")
            response = requests.post(url, headers=headers, json=retry_payload, timeout=timeout)
            if response.status_code < 400:
                break
            last_response = response
        break
    else:
        response = last_response

    if response is None:
        raise TextGenerationError("文本模型调用失败：没有收到响应。")
    if response.status_code >= 400:
        raise TextGenerationError(
            f"文本模型调用失败：HTTP {response.status_code} {response.text[:500]}"
        )

    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise TextGenerationError(f"文本模型返回格式异常：{data}") from exc

    try:
        return _extract_json(content)
    except Exception as exc:
        raise TextGenerationError(f"文本模型未返回合法 JSON：{content[:500]}") from exc
