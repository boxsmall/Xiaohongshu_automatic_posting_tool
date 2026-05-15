import base64
import mimetypes
from pathlib import Path
from typing import Any

import requests

from config import settings


class ImageGenerationError(RuntimeError):
    pass


def _model_candidates(model_id: str) -> list[str]:
    if settings.has_image_model_id_override:
        return [model_id]

    candidates = [
        model_id,
        "doubao-seedream-5-0-260128",
        "doubao-seedream-5-0-lite",
        "seedream-5-0-lite",
    ]
    return list(dict.fromkeys([item for item in candidates if item]))


def _image_to_data_url(path: str) -> str:
    image_path = Path(path)
    mime = mimetypes.guess_type(image_path.name)[0] or "image/png"
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _save_image_result(data: dict[str, Any], output_path: str) -> str:
    items = data.get("data")
    if not items:
        raise ImageGenerationError(f"图片模型返回格式异常：{data}")

    first = items[0]
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    b64 = first.get("b64_json") or first.get("base64") or first.get("image_base64")
    if b64:
        if "," in b64 and b64.strip().startswith("data:"):
            b64 = b64.split(",", 1)[1]
        path.write_bytes(base64.b64decode(b64))
        return str(path)

    url = first.get("url") or first.get("image_url")
    if url:
        response = requests.get(url, timeout=120)
        response.raise_for_status()
        path.write_bytes(response.content)
        return str(path)

    raise ImageGenerationError(f"未找到可保存的图片结果：{first}")


def generate_image_with_refs(
    prompt: str,
    ref_images: list[str],
    output_path: str,
    size: str | None = None,
    timeout: int = 180,
) -> str:
    if settings.image_model_provider != "ark":
        raise ImageGenerationError(f"暂不支持的图片模型供应商：{settings.image_model_provider}")
    if not settings.ark_api_key:
        raise ImageGenerationError("缺少 ARK_API_KEY，请在 .env 中配置。")

    refs = ref_images[: settings.max_ref_images_per_page]
    encoded_refs = [_image_to_data_url(path) for path in refs]

    payload: dict[str, Any] = {
        "model": settings.image_model_id,
        "prompt": prompt,
        "size": size or settings.image_size,
        "output_format": settings.image_output_format,
        "response_format": "b64_json",
        "watermark": False,
        "sequential_image_generation": "disabled",
        "extra_body": {
            "provider": {
                "enable_image_base64": True,
                "enable_image_origin_data": True,
            }
        },
    }
    if encoded_refs:
        payload["image"] = encoded_refs if len(encoded_refs) > 1 else encoded_refs[0]

    url = f"{settings.ark_base_url}/images/generations"
    headers = {
        "Authorization": f"Bearer {settings.ark_api_key}",
        "Content-Type": "application/json",
    }

    last_response = None
    for model in _model_candidates(settings.image_model_id):
        payload["model"] = model
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if response.status_code < 400:
            break
        last_response = response
        if response.status_code == 404:
            continue
        if payload.get("response_format") == "b64_json":
            retry_payload = dict(payload)
            retry_payload["response_format"] = "url"
            response = requests.post(url, headers=headers, json=retry_payload, timeout=timeout)
            if response.status_code < 400:
                break
            last_response = response
        break
    else:
        response = last_response

    if response is None:
        raise ImageGenerationError("图片模型调用失败：没有收到响应。")
    if response.status_code >= 400:
        raise ImageGenerationError(
            f"图片模型调用失败：HTTP {response.status_code} {response.text[:500]}"
        )

    return _save_image_result(response.json(), output_path)
