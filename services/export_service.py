import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def now_iso() -> str:
    return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")


def save_text_files(output_dir: str, title: str, body: str, hashtags: list[str]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "title.txt").write_text(title, encoding="utf-8")
    (output / "body.txt").write_text(body, encoding="utf-8")
    (output / "hashtags.txt").write_text("\n".join(hashtags), encoding="utf-8")
    publish = f"{title}\n\n{body}\n\n" + " ".join(f"#{tag}" for tag in hashtags)
    (output / "publish.md").write_text(publish, encoding="utf-8")


def save_draft_payload(
    output_dir: str,
    topic: str,
    title: str,
    body: str,
    hashtags: list[str],
    image_paths: list[str],
    pages: list[dict],
) -> str:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    timestamp = now_iso()
    payload = {
        "status": "pending_review",
        "topic": topic,
        "title": title,
        "body": body,
        "hashtags": hashtags,
        "images": image_paths,
        "pages": pages,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    path = output / "draft_payload.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    save_text_files(output_dir, title, body, hashtags)
    return str(path)


def load_draft_payload(output_dir: str) -> dict:
    path = Path(output_dir) / "draft_payload.json"
    if not path.exists():
        raise FileNotFoundError(f"未找到 draft_payload.json：{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def list_output_payload_dirs(base_dir: str, limit: int = 50) -> list[dict]:
    root = Path(base_dir)
    if not root.exists():
        return []

    results: list[dict] = []
    for directory in root.iterdir():
        if not directory.is_dir():
            continue
        payload_path = directory / "draft_payload.json"
        if not payload_path.exists():
            continue

        try:
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
        except Exception:
            payload = {}

        updated_at = payload.get("updated_at") or payload.get("created_at") or ""
        topic = payload.get("topic") or ""
        title = payload.get("title") or ""
        status = payload.get("status") or "unknown"
        label_topic = topic or title or directory.name
        label_time = updated_at.replace("T", " ")[:19] if updated_at else directory.name

        results.append(
            {
                "path": str(directory),
                "label": f"{label_time} | {label_topic} | {status}",
                "topic": topic,
                "title": title,
                "status": status,
                "updated_at": updated_at,
                "mtime": directory.stat().st_mtime,
            }
        )

    results.sort(key=lambda item: (item.get("updated_at") or "", item.get("mtime") or 0), reverse=True)
    return results[:limit]


def update_payload_status(output_dir: str, status: str) -> dict:
    path = Path(output_dir) / "draft_payload.json"
    payload = load_draft_payload(output_dir)
    payload["status"] = status
    payload["updated_at"] = now_iso()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def mark_payload_approved(output_dir: str) -> dict:
    return update_payload_status(output_dir, "approved")
