import json
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from config import settings
from services.topic_service import generate_topic_candidates_from_items


XHS_SEARCH_URL = "https://www.xiaohongshu.com/search_result?keyword={keyword}"


def _now_iso() -> str:
    return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")


def _make_research_dir() -> Path:
    stamp = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d_%H%M%S")
    path = Path(settings.output_dir) / "topic_research" / f"{stamp}_xhs_search"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _page_text_snapshot(page, limit: int = 1200) -> str:
    try:
        text = page.locator("body").inner_text(timeout=3000)
    except Exception as exc:
        return f"<页面文本读取失败：{exc}>"
    return " ".join(text.split())[:limit]


def _normalize_url(href: str | None) -> str:
    if not href:
        return ""
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        return "https://www.xiaohongshu.com" + href
    return href


def _extract_items_from_page(page, keyword: str, limit: int) -> list[dict]:
    script = """
    ({ limit }) => {
      const noteSections = Array.from(document.querySelectorAll('section.note-item'));
      const linkCards = Array.from(document.querySelectorAll('a[href*="/explore/"], a[href*="/discovery/item/"]'))
        .map(a => a.closest('section.note-item') || a.closest('[class*="note"]') || a.parentElement)
        .filter(Boolean);
      const nodes = noteSections.length ? noteSections : linkCards;
      const seen = new Set();
      const items = [];
      for (const node of nodes) {
        const text = (node.innerText || node.textContent || '').replace(/\\s+/g, ' ').trim();
        const linkNode = node.matches && node.matches('a[href]') ? node : node.querySelector && node.querySelector('a[href*="/explore/"], a[href*="/discovery/item/"]');
        const href = linkNode ? linkNode.getAttribute('href') : '';
        if (!text || text.length < 4) continue;
        if (!href && text.length < 12) continue;
        const key = (href || text).slice(0, 220);
        if (seen.has(key)) continue;
        seen.add(key);
        items.push({
          title_or_text: text.slice(0, 260),
          author: '',
          visible_metric: '',
          url: href || '',
        });
        if (items.length >= limit) break;
      }
      return items;
    }
    """
    raw_items = page.evaluate(script, {"limit": limit * 3})
    items = []
    for item in raw_items:
        text = str(item.get("title_or_text") or "").strip()
        url = _normalize_url(item.get("url"))
        if _looks_like_blocked_or_login_text(text):
            continue
        if not text and not url:
            continue
        if keyword and text == keyword:
            continue
        if not _looks_relevant_for_keyword(text, keyword):
            continue
        items.append(
            {
                "title_or_text": text,
                "author": str(item.get("author") or "").strip(),
                "visible_metric": str(item.get("visible_metric") or "").strip(),
                "url": url,
                "collected_at": _now_iso(),
            }
        )
        if len(items) >= limit:
            break
    return items


def _keyword_tokens(keyword: str) -> list[str]:
    tokens = [
        keyword,
        "减脂",
        "低卡",
        "高蛋白",
        "鸡胸",
        "虾仁",
        "魔芋",
        "黄瓜",
        "口蘑",
        "凉拌",
        "拌菜",
        "食谱",
        "做法",
        "餐",
    ]
    return list(dict.fromkeys([token for token in tokens if token]))


def _looks_relevant_for_keyword(text: str, keyword: str) -> bool:
    return any(token in text for token in _keyword_tokens(keyword))


def _looks_like_blocked_or_login_text(text: str) -> bool:
    markers = [
        "登录后查看搜索结果",
        "扫码成功",
        "请在手机上确认",
        "获取验证码",
        "手机号登录",
        "用户协议",
        "隐私政策",
        "验证码",
        "重新扫码",
    ]
    return any(marker in text for marker in markers)


def _is_login_or_blocked_page(page) -> bool:
    snapshot = _page_text_snapshot(page, limit=1600)
    return _looks_like_blocked_or_login_text(snapshot)


def _submit_search_keyword(page, keyword: str) -> None:
    selectors = [
        "input[placeholder*='搜索']",
        "input[type='search']",
        ".search-input input",
        "input",
    ]
    for selector in selectors:
        locator = page.locator(selector)
        for index in range(locator.count()):
            item = locator.nth(index)
            try:
                if not item.is_visible():
                    continue
                item.click(timeout=1500)
                item.fill(keyword, timeout=1500)
                item.press("Enter", timeout=1500)
                page.wait_for_timeout(4000)
                return
            except Exception:
                continue


def collect_xhs_search_notes(keyword: str = "减脂餐做法", limit: int = 20) -> list[dict]:
    search_url = XHS_SEARCH_URL.format(keyword=quote(keyword))
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=settings.xhs_browser_profile,
            headless=False,
            viewport={"width": 1440, "height": 1000},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.new_page()
        page.goto(search_url, wait_until="domcontentloaded")

        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PlaywrightTimeoutError:
            pass

        if _is_login_or_blocked_page(page):
            snapshot = _page_text_snapshot(page)
            current_url = page.url
            page.bring_to_front()
            page.wait_for_timeout(15000)
            if _is_login_or_blocked_page(page):
                context.close()
                raise RuntimeError(
                    "小红书搜索页需要登录或人工验证，已暂停等待但仍未进入搜索结果。"
                    "请在浏览器中完成登录/验证后重试。\n"
                    f"当前 URL：{current_url}\n页面文本快照：{snapshot}"
                )

        _submit_search_keyword(page, keyword)

        items: list[dict] = []
        for _ in range(8):
            items = _extract_items_from_page(page, keyword, limit)
            if len(items) >= limit:
                break
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(2000)

        if not items:
            snapshot = _page_text_snapshot(page)
            current_url = page.url
            context.close()
            raise RuntimeError(
                "没有采集到小红书搜索结果。可能需要登录、遇到验证码/风控，或页面结构已变化。\n"
                f"当前 URL：{current_url}\n页面文本快照：{snapshot}"
            )

        context.close()
        return items[:limit]


def save_topic_research(keyword: str, raw_items: list[dict], candidates: list[dict]) -> str:
    research_dir = _make_research_dir()
    (research_dir / "raw_items.json").write_text(
        json.dumps(raw_items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (research_dir / "topic_candidates.json").write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [f"# 小红书选题采集：{keyword}", "", f"- 采集数量：{len(raw_items)}", f"- 候选数量：{len(candidates)}", ""]
    for index, item in enumerate(candidates, start=1):
        points = "、".join(item.get("selling_points", []))
        ingredients = "、".join(item.get("ingredients_hint", []))
        lines.extend(
            [
                f"## {index}. {item.get('topic', '')}",
                f"- 理由：{item.get('reason', '')}",
                f"- 卖点：{points}",
                f"- 食材：{ingredients}",
                f"- 难度：{item.get('difficulty', '')}",
                "",
            ]
        )
    (research_dir / "research_summary.md").write_text("\n".join(lines), encoding="utf-8")
    return str(research_dir)


def research_xhs_topics(keyword: str = "减脂餐做法", limit: int = 20, count: int = 8) -> dict:
    raw_items = collect_xhs_search_notes(keyword=keyword, limit=limit)
    candidates = generate_topic_candidates_from_items(raw_items, count=count, keyword=keyword)
    research_dir = save_topic_research(keyword, raw_items, candidates)
    return {
        "keyword": keyword,
        "raw_items": raw_items,
        "candidates": candidates,
        "research_dir": research_dir,
    }
