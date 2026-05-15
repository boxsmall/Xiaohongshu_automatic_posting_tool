from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from slugify import slugify

from config import settings
from services.copy_service import generate_note_copy
from services.export_service import save_draft_payload
from services.image_service import generate_images_for_note


def make_output_dir(topic: str) -> str:
    stamp = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d_%H%M%S")
    slug = slugify(topic, max_length=40) or "xhs_note"
    return str(Path(settings.output_dir) / f"{stamp}_{slug}")


def generate_full_note(
    topic: str,
    audience: str | None = None,
    tone: str | None = None,
    image_count: int = 3,
    output_dir: str | None = None,
) -> dict:
    output_dir = output_dir or make_output_dir(topic)
    style_profile = {
        "source": settings.ref_image_dir,
        "note": "根据本地参考图保持统一的小红书图文风格。",
    }

    note = generate_note_copy(
        topic=topic,
        audience=audience,
        tone=tone,
        image_count=image_count,
        style_profile=style_profile,
    )
    images = generate_images_for_note(
        pages=note["pages"],
        style_profile=style_profile,
        ref_dir=settings.ref_image_dir,
        output_dir=output_dir,
        note_context={
            "topic": topic,
            "title": note["title"],
            "body": note["body"],
            "hashtags": note["hashtags"],
            "pages": note["pages"],
        },
    )
    save_draft_payload(
        output_dir=output_dir,
        topic=topic,
        title=note["title"],
        body=note["body"],
        hashtags=note["hashtags"],
        image_paths=images,
        pages=note["pages"],
    )
    return {"output_dir": output_dir, **note, "images": images}
