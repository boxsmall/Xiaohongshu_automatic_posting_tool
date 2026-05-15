import base64
import mimetypes
from pathlib import Path
from typing import Any, BinaryIO

import requests

from config import settings


class ImageGenerationError(RuntimeError):
    pass


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


def _validate_openai_relay_config() -> None:
    if settings.image_model_provider != "openai_relay":
        raise ImageGenerationError(
            f"暂不支持的图片模型供应商：{settings.image_model_provider}，请配置 IMAGE_MODEL_PROVIDER=openai_relay"
        )
    if not settings.openai_image_base_url:
        raise ImageGenerationError("缺少 OPENAI_IMAGE_BASE_URL，请在 .env 中配置中转站 /v1 地址。")
    if not settings.openai_image_api_key:
        raise ImageGenerationError("缺少 OPENAI_IMAGE_API_KEY，请在 .env 中配置中转站 Key。")


def _openai_image_base_url() -> str:
    base_url = settings.openai_image_base_url.rstrip("/")
    if not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"
    return base_url


def _base_payload(prompt: str, size: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": settings.image_model_id,
        "prompt": prompt,
        "n": 1,
    }

    image_size = size or settings.image_size
    if image_size:
        payload["size"] = image_size

    if settings.image_output_format:
        payload["output_format"] = settings.image_output_format

    return payload


def _image_file_tuple(path: str) -> tuple[str, tuple[str, BinaryIO, str]]:
    image_path = Path(path)
    mime = mimetypes.guess_type(image_path.name)[0] or "image/png"
    return "image", (image_path.name, image_path.open("rb"), mime)


def _close_files(files: list[tuple[str, tuple[str, BinaryIO, str]]]) -> None:
    for _, (_, file_obj, _) in files:
        file_obj.close()


def _post_openai_image_request(
    endpoint: str,
    payload: dict[str, Any],
    ref_images: list[str],
    timeout: int,
) -> dict[str, Any]:
    url = f"{_openai_image_base_url()}/{endpoint.lstrip('/')}"
    headers = {"Authorization": f"Bearer {settings.openai_image_api_key}"}

    files: list[tuple[str, tuple[str, BinaryIO, str]]] = []
    try:
        if ref_images:
            files = [_image_file_tuple(path) for path in ref_images]
            form_payload = {key: str(value) for key, value in payload.items()}
            response = requests.post(url, headers=headers, data=form_payload, files=files, timeout=timeout)
        else:
            json_headers = {**headers, "Content-Type": "application/json"}
            response = requests.post(url, headers=json_headers, json=payload, timeout=timeout)
    finally:
        _close_files(files)

    if response.status_code >= 400:
        raise ImageGenerationError(
            f"图片模型调用失败：HTTP {response.status_code} {response.text[:500]}"
        )

    try:
        return response.json()
    except ValueError as exc:
        raise ImageGenerationError(f"图片模型返回非 JSON 内容：{response.text[:500]}") from exc


def generate_image_with_refs(
    prompt: str,
    ref_images: list[str],
    output_path: str,
    size: str | None = None,
    timeout: int = 180,
) -> str:
    _validate_openai_relay_config()

    refs = ref_images[: settings.max_ref_images_per_page]
    payload = _base_payload(prompt, size)
    endpoint = "images/edits" if refs else "images/generations"
    data = _post_openai_image_request(endpoint, payload, refs, timeout)
    return _save_image_result(data, output_path)
