import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    ref_image_dir: str = os.getenv("REF_IMAGE_DIR", "参考图")
    output_dir: str = os.getenv("OUTPUT_DIR", "assets/outputs")

    text_model_provider: str = os.getenv("TEXT_MODEL_PROVIDER", "ark")
    text_model_name: str = os.getenv("TEXT_MODEL_NAME", "Doubao-Seed-2.0-lite")
    text_model_id: str = os.getenv("TEXT_MODEL_ID", os.getenv("TEXT_MODEL_NAME", "Doubao-Seed-2.0-lite"))
    image_model_provider: str = os.getenv("IMAGE_MODEL_PROVIDER", "openai_relay")
    image_model_name: str = os.getenv("IMAGE_MODEL_NAME", "gpt-image-2")
    has_image_model_id_override: bool = "IMAGE_MODEL_ID" in os.environ
    image_model_id: str = os.getenv(
        "IMAGE_MODEL_ID", os.getenv("IMAGE_MODEL_NAME", "gpt-image-2")
    )

    ark_api_key: str = os.getenv("ARK_API_KEY", "")
    ark_base_url: str = os.getenv(
        "ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"
    ).rstrip("/")
    openai_image_base_url: str = os.getenv("OPENAI_IMAGE_BASE_URL", "").rstrip("/")
    openai_image_api_key: str = os.getenv("OPENAI_IMAGE_API_KEY", "")

    image_size: str = os.getenv("IMAGE_SIZE", "auto")
    image_output_format: str = os.getenv("IMAGE_OUTPUT_FORMAT", "png")
    max_ref_images_per_page: int = int(os.getenv("MAX_REF_IMAGES_PER_PAGE", "3"))

    xhs_browser_profile: str = os.getenv("XHS_BROWSER_PROFILE", "browser_profile/xhs")
    xhs_headless: bool = _bool_env("XHS_HEADLESS", False)
    xhs_post_fill_wait_seconds: int = int(os.getenv("XHS_POST_FILL_WAIT_SECONDS", "600"))


settings = Settings()


def ensure_runtime_dirs() -> None:
    Path(settings.output_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.xhs_browser_profile).mkdir(parents=True, exist_ok=True)
