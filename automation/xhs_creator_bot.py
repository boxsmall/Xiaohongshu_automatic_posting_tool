from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from automation.selectors import (
    BODY_CANDIDATES,
    FILE_INPUT,
    IMAGE_ACCEPT_TOKENS,
    IMAGE_FILE_INPUT_CANDIDATES,
    IMAGE_PUBLISH_MODE_SELECTORS,
    IMAGE_PUBLISH_MODE_TEXTS,
    TITLE_CANDIDATES,
    VIDEO_ACCEPT_TOKENS,
)
from config import settings


XHS_PUBLISH_URL = "https://creator.xiaohongshu.com/publish/publish?source=official"
XHS_IMAGE_PUBLISH_URLS = [
    "https://creator.xiaohongshu.com/publish/publish?source=official&type=normal",
    "https://creator.xiaohongshu.com/publish/publish?source=official&type=image",
    "https://creator.xiaohongshu.com/publish/publish?source=official&noteType=image",
]


def build_xhs_body(body: str, hashtags: list[str]) -> str:
    tags = " ".join(f"#{tag.strip('# ')}" for tag in hashtags if tag.strip("# "))
    return f"{body.strip()}\n\n{tags}".strip()


def _normalize_accept(accept: str | None) -> str:
    return (accept or "").replace(" ", "").lower()


def _accepts_image(accept: str | None) -> bool:
    normalized = _normalize_accept(accept)
    return any(token in normalized for token in IMAGE_ACCEPT_TOKENS)


def _accepts_video(accept: str | None) -> bool:
    normalized = _normalize_accept(accept)
    return any(token in normalized for token in VIDEO_ACCEPT_TOKENS)


def _input_debug_rows(page) -> list[dict]:
    rows = []
    inputs = page.locator(FILE_INPUT)
    for index in range(inputs.count()):
        item = inputs.nth(index)
        try:
            accept = item.get_attribute("accept") or ""
            multiple = item.get_attribute("multiple") is not None
            class_name = item.get_attribute("class") or ""
            outer_html = item.evaluate("el => el.outerHTML").replace("\n", " ")[:300]
        except Exception as exc:
            accept = f"<读取失败：{exc}>"
            multiple = False
            class_name = ""
            outer_html = ""
        rows.append(
            {
                "index": index,
                "accept": accept,
                "multiple": multiple,
                "class": class_name,
                "outer_html": outer_html,
            }
        )
    return rows


def _format_input_debug(rows: list[dict]) -> str:
    if not rows:
        return "未找到任何 input[type='file']。"
    return "\n".join(
        [
            (
                f"#{row['index']} accept={row['accept']!r} "
                f"multiple={row['multiple']} class={row['class']!r} "
                f"html={row.get('outer_html', '')!r}"
            )
            for row in rows
        ]
    )


def _page_text_snapshot(page, limit: int = 1200) -> str:
    try:
        text = page.locator("body").inner_text(timeout=2000)
    except Exception as exc:
        return f"<页面文本读取失败：{exc}>"
    text = " ".join(text.split())
    return text[:limit]


def _is_in_viewport(locator) -> bool:
    try:
        box = locator.bounding_box(timeout=1000)
    except Exception:
        return False
    if not box:
        return False
    return box["x"] >= 0 and box["y"] >= 0 and box["width"] > 0 and box["height"] > 0


def _click_locator_candidates(locator, timeout: int = 2000) -> bool:
    try:
        count = locator.count()
    except Exception:
        return False

    for index in range(count - 1, -1, -1):
        item = locator.nth(index)
        try:
            if not item.is_visible() or not _is_in_viewport(item):
                continue
            try:
                item.click(timeout=timeout)
            except Exception:
                item.click(timeout=timeout, force=True)
            return True
        except Exception:
            continue
    return False


def ensure_image_publish_mode(page) -> None:
    if page.locator("input[type='file'][accept*='.png']").count() > 0:
        return
    if page.locator("input[type='file'][accept*='image']").count() > 0:
        return

    for selector in IMAGE_PUBLISH_MODE_SELECTORS:
        try:
            locator = page.locator(selector)
            if not _click_locator_candidates(locator):
                continue
            page.wait_for_timeout(2000)
            if page.locator("input[type='file'][accept*='.png']").count() > 0:
                return
            if page.locator("input[type='file'][accept*='image']").count() > 0:
                return
        except Exception:
            continue

    for text in IMAGE_PUBLISH_MODE_TEXTS:
        for exact in (True, False):
            locator = page.get_by_text(text, exact=exact)
            try:
                if not _click_locator_candidates(locator):
                    continue
                page.wait_for_timeout(2000)
                if page.locator("input[type='file'][accept*='.png']").count() > 0:
                    return
                if page.locator("input[type='file'][accept*='image']").count() > 0:
                    return
            except Exception:
                continue

    # Some deployments use query params to choose the publishing kind.
    original_url = page.url
    for url in XHS_IMAGE_PUBLISH_URLS:
        if page.url == url:
            continue
        try:
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            if page.locator("input[type='file'][accept*='.png']").count() > 0:
                return
            if page.locator("input[type='file'][accept*='image']").count() > 0:
                return
        except Exception:
            continue
    if page.url != original_url:
        try:
            page.goto(original_url, wait_until="domcontentloaded")
            page.wait_for_timeout(1500)
        except Exception:
            pass


def find_image_file_input(page):
    rows = _input_debug_rows(page)
    matches = []
    inputs = page.locator(FILE_INPUT)

    for selector in IMAGE_FILE_INPUT_CANDIDATES:
        candidates = page.locator(selector)
        for index in range(candidates.count()):
            item = candidates.nth(index)
            accept = item.get_attribute("accept") or ""
            if _accepts_image(accept) and not _accepts_video(accept):
                multiple = item.get_attribute("multiple") is not None
                matches.append((item, multiple))

    if not matches:
        for index in range(inputs.count()):
            item = inputs.nth(index)
            accept = item.get_attribute("accept") or ""
            if _accepts_image(accept) and not _accepts_video(accept):
                multiple = item.get_attribute("multiple") is not None
                matches.append((item, multiple))

    if matches:
        for item, multiple in matches:
            if multiple:
                return item, multiple, rows
        return matches[0][0], matches[0][1], rows

    has_only_video = bool(rows) and all(_accepts_video(row["accept"]) for row in rows)
    if has_only_video:
        raise RuntimeError(
            "当前页面可能停留在视频发布模式，只找到了视频上传入口。"
            "请切换到“图文”/“发布图文”后重试。\n"
            f"文件上传入口调试信息：\n{_format_input_debug(rows)}\n"
            f"页面文本快照：\n{_page_text_snapshot(page)}"
        )

    raise RuntimeError(
        "未找到支持图片的上传 input。请确认页面已经进入图文发布模式。\n"
        f"文件上传入口调试信息：\n{_format_input_debug(rows)}\n"
        f"页面文本快照：\n{_page_text_snapshot(page)}"
    )


def wait_for_login_or_publish_page(page) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except PlaywrightTimeoutError:
        pass

    for _ in range(90):
        ensure_image_publish_mode(page)
        try:
            find_image_file_input(page)
            return
        except RuntimeError:
            pass
        page.wait_for_timeout(1000)

    # Leave control with the user for manual login/navigation, then try once more.
    page.bring_to_front()
    page.wait_for_timeout(15000)
    ensure_image_publish_mode(page)
    find_image_file_input(page)


def upload_images(page, image_paths: list[str]) -> None:
    file_input, multiple, _ = find_image_file_input(page)
    if multiple or len(image_paths) == 1:
        file_input.set_input_files(image_paths)
        page.wait_for_timeout(5000)
        return

    for image_path in image_paths:
        file_input, _, _ = find_image_file_input(page)
        file_input.set_input_files(image_path)
        page.wait_for_timeout(2500)


def _fill_first_available(page, selectors: list[str], text: str, prefer_second: bool = False) -> None:
    for selector in selectors:
        locator = page.locator(selector)
        count = locator.count()
        if count == 0:
            continue
        target = locator.nth(1) if prefer_second and count > 1 else locator.first
        try:
            target.click()
            target.fill(text)
            return
        except Exception:
            try:
                target.click()
                page.keyboard.insert_text(text)
                return
            except Exception:
                continue
    raise RuntimeError(f"未找到可填写的输入区域：{selectors}")


def fill_title(page, title: str) -> None:
    _fill_first_available(page, TITLE_CANDIDATES, title)


def fill_body(page, body: str) -> None:
    _fill_first_available(page, BODY_CANDIDATES, body, prefer_second=True)


def create_xhs_draft(
    title: str,
    body: str,
    hashtags: list[str],
    image_paths: list[str],
    user_data_dir: str | None = None,
    headless: bool | None = None,
    wait_seconds: int | None = None,
) -> None:
    resolved_images = [str(Path(path).resolve()) for path in image_paths]
    missing = [path for path in resolved_images if not Path(path).exists()]
    if missing:
        raise FileNotFoundError(f"图片不存在：{missing[0]}")

    final_body = build_xhs_body(body, hashtags)
    user_data_dir = user_data_dir or settings.xhs_browser_profile
    headless = settings.xhs_headless if headless is None else headless
    wait_seconds = settings.xhs_post_fill_wait_seconds if wait_seconds is None else wait_seconds

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=headless,
            viewport={"width": 1440, "height": 1000},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.new_page()
        page.goto(XHS_PUBLISH_URL, wait_until="domcontentloaded")

        wait_for_login_or_publish_page(page)
        upload_images(page, resolved_images)
        fill_title(page, title)
        fill_body(page, final_body)
        page.bring_to_front()
        page.wait_for_timeout(max(wait_seconds, 0) * 1000)
        context.close()
