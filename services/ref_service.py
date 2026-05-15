from pathlib import Path


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def _is_image(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGE_EXTS


def list_reference_images(ref_dir: str) -> list[str]:
    root = Path(ref_dir)
    if not root.exists():
        raise FileNotFoundError(f"参考图文件夹不存在：{root}")

    images = sorted(str(p) for p in root.rglob("*") if _is_image(p))
    if not images:
        raise RuntimeError(f"参考图文件夹为空：{root}")
    return images


def list_reference_images_by_type(ref_dir: str) -> dict[str, list[str]]:
    root = Path(ref_dir)
    result = {"cover": [], "content": [], "ending": []}

    if not root.exists():
        raise FileNotFoundError(f"参考图文件夹不存在：{root}")

    for key in result:
        subdir = root / key
        if subdir.exists():
            result[key] = sorted(str(p) for p in subdir.rglob("*") if _is_image(p))

    # Also support the current simple Chinese file layout:
    # 参考图/封面参考图.png, 参考图/内容页参考图.png, 参考图/结尾页参考图.png
    for image in root.rglob("*"):
        if not _is_image(image):
            continue
        name = image.stem.lower()
        value = str(image)
        if any(token in name for token in ("cover", "封面")):
            result["cover"].append(value)
        elif any(token in name for token in ("ending", "end", "结尾", "收尾")):
            result["ending"].append(value)
        elif any(token in name for token in ("content", "内容", "正文")):
            result["content"].append(value)

    all_images = list_reference_images(ref_dir)
    for key in result:
        unique = sorted(dict.fromkeys(result[key]))
        result[key] = unique if unique else all_images

    return result

