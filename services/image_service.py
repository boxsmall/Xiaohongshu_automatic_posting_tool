from pathlib import Path
from typing import Any

from services.model_clients.image_client import generate_image_with_refs
from services.ref_service import list_reference_images_by_type


def _shorten(text: str, max_chars: int = 800) -> str:
    text = " ".join((text or "").split())
    return text[:max_chars]


def build_image_prompt(
    style_profile: dict[str, Any],
    page: dict[str, Any],
    note_context: dict[str, Any] | None = None,
) -> str:
    template_path = Path("prompts") / "image_prompt_prompt.txt"
    template = (
        template_path.read_text(encoding="utf-8")
        if template_path.exists()
        else "请根据参考图风格生成一张竖版 3:4 小红书图文页。"
    )

    note_context = note_context or {}
    topic = note_context.get("topic", "")
    title = note_context.get("title", "")
    body = _shorten(note_context.get("body", ""), 900)
    hashtags = " ".join(f"#{tag}" for tag in note_context.get("hashtags", []))
    all_pages = note_context.get("pages", [])
    page_brief = "\n".join(
        [
            (
                f"图{item.get('page')}({item.get('type')}): "
                f"{item.get('main_text')} / {item.get('sub_text')} / "
                f"{item.get('visual_instruction')}"
            )
            for item in all_pages
        ]
    )

    return f"""{template}

当前整组笔记主题上下文：
主题/菜名：{topic}
发布标题：{title}
正文关键信息：{body}
话题标签：{hashtags}

整组三张图的内容规划：
{page_brief}

当前这一张图必须服务于同一个主题，不能生成与“{topic or title}”无关的菜、食材、场景或文字。

画幅：竖版 3:4，适合小红书图文笔记。
页面类型：{page.get("type")}
页码：{page.get("page")}
主标题：{page.get("main_text")}
副标题：{page.get("sub_text")}
视觉说明：{page.get("visual_instruction")}

参考风格要求：
{style_profile or "沿用参考图的配色、留白、字体层级、图文比例和整体版式。"}

硬性要求：
1. 画面必须清爽，文字少而清晰，手机端可读。
2. 不要二维码、联系方式、外链、水印、平台 Logo。
3. 不要生成夸张营销词和不实承诺。
4. 保持整组图片风格一致。
5. 图片上只放主标题和副标题的核心文字，不要塞满正文。
"""


def _filename_for_page(page: dict[str, Any]) -> str:
    if page.get("type") == "cover" or int(page.get("page", 1)) == 1:
        return "cover.png"
    return f"image_{page.get('page')}.png"


def generate_images_for_note(
    pages: list[dict[str, Any]],
    style_profile: dict[str, Any],
    ref_dir: str,
    output_dir: str,
    note_context: dict[str, Any] | None = None,
) -> list[str]:
    refs = list_reference_images_by_type(ref_dir)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    image_paths: list[str] = []
    for page in pages:
        page_type = page.get("type", "content")
        ref_images = refs.get(page_type) or refs["content"]
        path = output / _filename_for_page(page)
        prompt = build_image_prompt(style_profile, page, note_context=note_context)
        image_paths.append(generate_image_with_refs(prompt, ref_images, str(path)))

    return image_paths
