FILE_INPUT = "input[type='file']"

IMAGE_FILE_INPUT_CANDIDATES = [
    "input.input-file[type='file'][accept='image/*']",
    "input[type='file'][accept*='image']",
    "input[type='file'][accept*='.png']",
    "input[type='file'][accept*='.jpg']",
    "input[type='file'][accept*='.jpeg']",
    "input[type='file'][accept*='.webp']",
]

IMAGE_ACCEPT_TOKENS = (
    "image/",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
)

VIDEO_ACCEPT_TOKENS = (
    "video/",
    ".mp4",
    ".mov",
    ".flv",
    ".f4v",
    ".mkv",
    ".rm",
    ".rmvb",
    ".m4v",
    ".mpg",
    ".mpeg",
    ".ts",
)

IMAGE_PUBLISH_MODE_TEXTS = [
    "发布图文",
    "图文",
    "上传图文",
    "发布笔记",
    "笔记",
]

IMAGE_PUBLISH_MODE_SELECTORS = [
    "[role='tab']:has-text('图文')",
    "[role='tab']:has-text('笔记')",
    "button:has-text('图文')",
    "button:has-text('笔记')",
    ".creator-tab:has-text('图文')",
    ".tab:has-text('图文')",
    ".upload-card:has-text('图文')",
    ".publish-type:has-text('图文')",
]

TITLE_CANDIDATES = [
    "input[placeholder*='标题']",
    "textarea[placeholder*='标题']",
    "[contenteditable='true']",
]

BODY_CANDIDATES = [
    "textarea[placeholder*='正文']",
    "textarea[placeholder*='描述']",
    "textarea[placeholder*='分享']",
    "div[contenteditable='true']",
]
