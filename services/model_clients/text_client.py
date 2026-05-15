import json
import re
from typing import Any

import requests
from requests import RequestException

from config import settings


class TextGenerationError(RuntimeError):
    pass


class TextRelayHTTPError(TextGenerationError):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


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


def _request_session() -> requests.Session:
    session = requests.Session()
    session.trust_env = settings.openai_text_use_env_proxy
    return session


def _openai_text_base_url() -> str:
    base_url = settings.openai_text_base_url.rstrip("/")
    if not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"
    return base_url


def _validate_openai_relay_config() -> None:
    if settings.text_model_provider != "openai_relay":
        raise TextGenerationError(
            f"暂不支持的文本模型供应商：{settings.text_model_provider}，请配置 TEXT_MODEL_PROVIDER=openai_relay"
        )
    if not settings.openai_text_base_url:
        raise TextGenerationError("缺少 OPENAI_TEXT_BASE_URL，请在 .env 中配置中转站 /v1 地址。")
    if not settings.openai_text_api_key:
        raise TextGenerationError("缺少 OPENAI_TEXT_API_KEY，请在 .env 中配置中转站 Key。")


def _chat_completion(payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    url = f"{_openai_text_base_url()}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openai_text_api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = _request_session().post(url, headers=headers, json=payload, timeout=timeout)
    except RequestException as exc:
        proxy_hint = ""
        if not settings.openai_text_use_env_proxy:
            proxy_hint = "；当前已禁用环境代理，如你的中转站必须走代理，请设置 OPENAI_TEXT_USE_ENV_PROXY=true"
        raise TextGenerationError(f"文本模型网络请求失败：{exc}{proxy_hint}") from exc

    if response.status_code >= 400:
        raise TextRelayHTTPError(
            response.status_code,
            f"文本模型调用失败：HTTP {response.status_code} {response.text[:500]}"
        )

    try:
        return response.json()
    except ValueError as exc:
        raise TextGenerationError(f"文本模型返回非 JSON 内容：{response.text[:500]}") from exc


def chat_json(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    timeout: int = 90,
) -> dict[str, Any]:
    _validate_openai_relay_config()

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

    try:
        data = _chat_completion(payload, timeout)
    except TextRelayHTTPError:
        retry_payload = dict(payload)
        retry_payload.pop("response_format", None)
        data = _chat_completion(retry_payload, timeout)
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise TextGenerationError(f"文本模型返回格式异常：{data}") from exc

    try:
        return _extract_json(content)
    except Exception as exc:
        raise TextGenerationError(f"文本模型未返回合法 JSON：{content[:500]}") from exc
