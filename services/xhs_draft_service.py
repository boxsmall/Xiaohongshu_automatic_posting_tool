from config import settings
from automation.xhs_creator_bot import create_xhs_draft
from services.export_service import load_draft_payload, update_payload_status


def create_draft_from_output(output_dir: str) -> None:
    payload = load_draft_payload(output_dir)
    if payload.get("status") not in {"approved", "draft_created"}:
        raise RuntimeError("请先审核通过，再创建小红书草稿。")

    create_xhs_draft(
        title=payload["title"],
        body=payload["body"],
        hashtags=payload.get("hashtags", []),
        image_paths=payload.get("images", []),
        user_data_dir=settings.xhs_browser_profile,
        headless=settings.xhs_headless,
    )
    update_payload_status(output_dir, "draft_created")

