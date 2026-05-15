from pathlib import Path

import streamlit as st

from config import ensure_runtime_dirs, settings
from services.export_service import list_output_payload_dirs, load_draft_payload
from services.generation_service import generate_full_note
from services.ref_service import list_reference_images_by_type
from services.review_service import approve_output, reject_output
from services.xhs_search_service import research_xhs_topics
from services.xhs_draft_service import create_draft_from_output


st.set_page_config(page_title="小红书图文草稿工具", layout="wide")
ensure_runtime_dirs()


def _init_state() -> None:
    st.session_state.setdefault("output_dir", "")
    st.session_state.setdefault("topic", "")
    st.session_state.setdefault("topic_research", None)


def _show_reference_images() -> None:
    st.subheader("参考图")
    try:
        refs = list_reference_images_by_type(settings.ref_image_dir)
    except Exception as exc:
        st.error(str(exc))
        return

    cols = st.columns(3)
    for col, key, label in zip(cols, ["cover", "content", "ending"], ["封面", "内容页", "结尾页"]):
        with col:
            st.caption(f"{label}：{len(refs[key])} 张")
            if refs[key]:
                st.image(refs[key][0], use_container_width=True)


def _show_payload(output_dir: str) -> None:
    try:
        payload = load_draft_payload(output_dir)
    except Exception as exc:
        st.warning(str(exc))
        return

    status = payload.get("status", "unknown")
    st.subheader("预览")
    st.caption(f"输出目录：{output_dir}")
    st.caption(f"状态：{status}")

    left, right = st.columns([0.9, 1.1])
    with left:
        st.text_input("标题", value=payload.get("title", ""), disabled=True)
        st.text_area("正文", value=payload.get("body", ""), height=260, disabled=True)
        st.text_input(
            "话题",
            value=" ".join(f"#{tag}" for tag in payload.get("hashtags", [])),
            disabled=True,
        )

        page_rows = []
        for page in payload.get("pages", []):
            page_rows.append(
                {
                    "页码": page.get("page"),
                    "类型": page.get("type"),
                    "主标题": page.get("main_text"),
                    "副标题": page.get("sub_text"),
                }
            )
        if page_rows:
            st.dataframe(page_rows, use_container_width=True, hide_index=True)

    with right:
        images = payload.get("images", [])
        if images:
            cols = st.columns(2)
            for index, image_path in enumerate(images):
                with cols[index % 2]:
                    if Path(image_path).exists():
                        st.image(image_path, caption=Path(image_path).name, use_container_width=True)
                    else:
                        st.warning(f"图片不存在：{image_path}")
        else:
            st.info("还没有生成图片。")

    st.subheader("审核")
    approve_col, reject_col, draft_col = st.columns([1, 1, 2])
    with approve_col:
        if st.button("通过", use_container_width=True):
            approve_output(output_dir)
            st.success("已标记为审核通过。")
            st.rerun()
    with reject_col:
        if st.button("驳回", use_container_width=True):
            reject_output(output_dir)
            st.warning("已标记为驳回。")
            st.rerun()
    with draft_col:
        disabled = status not in {"approved", "draft_created"}
        if st.button("通过并生成小红书草稿", disabled=disabled, use_container_width=True):
            with st.spinner("正在打开小红书创作平台并填充草稿..."):
                create_draft_from_output(output_dir)
            st.success("草稿已填入小红书创作平台，请在浏览器中检查。")
            st.rerun()


def main() -> None:
    _init_state()

    st.title("小红书图文草稿工具")

    with st.sidebar:
        st.header("配置")
        st.text_input("参考图目录", value=settings.ref_image_dir, disabled=True)
        st.text_input("输出目录", value=settings.output_dir, disabled=True)
        st.text_input("文案模型", value=settings.text_model_name, disabled=True)
        st.text_input("图片模型", value=settings.image_model_name, disabled=True)
        st.caption("API Key 从 .env 读取，页面不显示。")

    with st.expander("参考图", expanded=False):
        _show_reference_images()

    st.subheader("生成")
    with st.expander("从小红书自动找选题", expanded=False):
        keyword = st.text_input("搜索关键词", value="减脂餐做法", key="xhs_search_keyword")
        research_col, info_col = st.columns([1, 2])
        with research_col:
            if st.button("自动采集并生成选题", use_container_width=True):
                with st.spinner("正在打开小红书搜索页采集选题灵感..."):
                    st.session_state.topic_research = research_xhs_topics(
                        keyword=keyword.strip() or "减脂餐做法",
                        limit=20,
                        count=8,
                    )
                st.success("选题候选已生成。")
        with info_col:
            st.caption("只采集搜索页公开可见卡片信息，用于提炼原创选题；不抓取隐藏内容，不自动互动。")

        research = st.session_state.topic_research
        if research:
            st.caption(
                f"采集目录：{research.get('research_dir')} | "
                f"采集 {len(research.get('raw_items', []))} 条 | "
                f"候选 {len(research.get('candidates', []))} 个"
            )
            for index, candidate in enumerate(research.get("candidates", []), start=1):
                title = candidate.get("topic", "")
                points = "、".join(candidate.get("selling_points", []))
                ingredients = "、".join(candidate.get("ingredients_hint", []))
                cols = st.columns([2, 3, 1])
                with cols[0]:
                    st.markdown(f"**{index}. {title}**")
                    st.caption(candidate.get("reason", ""))
                with cols[1]:
                    st.caption(f"卖点：{points}")
                    st.caption(f"食材：{ingredients} | 难度：{candidate.get('difficulty', '')}")
                with cols[2]:
                    if st.button("使用", key=f"use_topic_{index}", use_container_width=True):
                        st.session_state.topic = title
                        st.rerun()

    with st.form("generate_form"):
        topic = st.text_input(
            "选题",
            placeholder="例如：酸辣鸡胸黄瓜拌菜",
            key="topic",
        )
        audience = st.text_input("目标人群", value="小红书内容创作者、职场新人")
        tone = st.text_input("语气", value="真诚、实用、不夸张")
        image_count = st.slider("图片张数", min_value=3, max_value=8, value=3)
        submitted = st.form_submit_button("生成内容", use_container_width=True)

    if submitted:
        if not topic.strip():
            st.error("请先输入选题。")
        else:
            with st.spinner("正在生成文案和图片，这一步可能需要一点时间..."):
                result = generate_full_note(
                    topic=topic.strip(),
                    audience=audience.strip() or None,
                    tone=tone.strip() or None,
                    image_count=image_count,
                )
            st.session_state.output_dir = result["output_dir"]
            st.success("生成完成，下面可以预览和审核。")
            st.rerun()

    st.subheader("导入已生成内容")
    output_dirs = list_output_payload_dirs(settings.output_dir)
    if output_dirs:
        label_to_path = {item["label"]: item["path"] for item in output_dirs}
        current_index = 0
        for index, item in enumerate(output_dirs):
            if item["path"] == st.session_state.output_dir:
                current_index = index
                break

        selected_label = st.selectbox(
            "选择已生成内容文件夹",
            options=list(label_to_path.keys()),
            index=current_index,
            help="只显示包含 draft_payload.json 的有效生成结果。",
        )
        import_col, current_col = st.columns([1, 3])
        with import_col:
            if st.button("导入选中内容", use_container_width=True):
                st.session_state.output_dir = label_to_path[selected_label]
                st.rerun()
        with current_col:
            st.caption(f"当前输出目录：{st.session_state.output_dir or '未选择'}")
    else:
        st.info("暂无可导入生成内容。")

    with st.expander("手动输入输出目录", expanded=False):
        manual_output_dir = st.text_input(
            "输出目录路径",
            value=st.session_state.output_dir,
            placeholder="例如：assets/outputs/20260515_094750_xxx",
        )
        if st.button("导入手动目录", use_container_width=True):
            st.session_state.output_dir = manual_output_dir.strip()
            st.rerun()

    if st.session_state.output_dir:
        _show_payload(st.session_state.output_dir)
    else:
        st.info("输入选题并生成后，会在这里显示预览和审核按钮。")


if __name__ == "__main__":
    main()
