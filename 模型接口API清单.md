# 模型接口 API 清单

本文档只记录模型和外部接口需求。具体产品流程见 `完整方案.md`。

## 1. 第一版必须接入的接口

第一版真正必须接入的模型接口只有两个：

| 接口 | 是否必须 | 用途 |
|---|---:|---|
| 文本生成 API | 是 | 根据选题生成标题、正文、话题和图片页文案 |
| 图片生成 API | 是 | 根据图片页文案和本地参考图生成小红书图文图片 |

浏览器自动化不属于模型 API。小红书草稿创建第一版不使用官方开放 API，而是通过 Playwright 打开官方创作平台，由人工登录和最终确认。

## 2. 建议预留的接口

| 接口 | 是否必须 | 用途 |
|---|---:|---|
| 多模态风格分析 API | 可选 | 读取参考图，总结配色、构图、字体层级、版式风格 |
| 文本安全审核 API | 可选 | 检查文案是否有违规或高风险表达 |
| 图片安全审核 API | 可选 | 检查生成图片是否存在违规内容 |
| OCR/图片文字检测 API | 可选 | 检查生成图中文字是否清晰、是否错字 |

## 3. 接口一：文本生成 API

### 3.1 用途

根据用户输入的选题，生成一套结构化小红书图文内容。

### 3.2 输入

```json
{
  "topic": "AI工具效率提升",
  "audience": "职场新人、内容创作者",
  "tone": "真诚、实用、不夸张",
  "image_count": 5,
  "style_profile": {
    "layout": "大标题封面，内容页信息分块",
    "color": "高对比但不刺眼",
    "font": "标题醒目，正文短句"
  }
}
```

### 3.3 输出

要求模型输出严格 JSON：

```json
{
  "title": "这5个AI工具，真的帮我少做了很多重复活",
  "body": "最近我把工作里最重复的几个环节重新整理了一下...",
  "hashtags": ["AI工具", "效率工具", "职场干货", "打工人"],
  "pages": [
    {
      "page": 1,
      "type": "cover",
      "main_text": "5个AI工具",
      "sub_text": "少做重复活",
      "visual_instruction": "封面要有强对比标题和明确利益点"
    },
    {
      "page": 2,
      "type": "content",
      "main_text": "先整理重复任务",
      "sub_text": "把每天固定做的事列出来",
      "visual_instruction": "使用清单式排版"
    }
  ]
}
```

### 3.4 推荐抽象函数

```python
def generate_note_copy(
    topic: str,
    audience: str | None = None,
    tone: str | None = None,
    image_count: int = 5,
    style_profile: dict | None = None
) -> dict:
    ...
```

### 3.5 可选供应商

第一版文案模型确定使用：

```bash
TEXT_MODEL_PROVIDER=ark
TEXT_MODEL_NAME=Doubao-Seed-2.0-lite
# 可选：火山方舟控制台实际 endpoint/model ID
# TEXT_MODEL_ID=doubao-seed-2-0-lite-260215
ARK_API_KEY=你的火山方舟Key
```

| 供应商 | 可用模型类型 | 备注 |
|---|---|---|
| 火山方舟 | Doubao-Seed-2.0-lite | 第一版文案模型，负责标题、正文、话题和图片页文案 |
| 阿里云百炼 | 通义千问文本模型 | 适合中文文案 |
| OpenAI | GPT 系列文本模型 | 适合结构化输出和复杂改写 |
| 其他兼容 OpenAI SDK 的服务 | Chat Completions | 便于统一封装 |

## 4. 接口二：图片生成 API

### 4.1 用途

根据每页图片文案和参考图风格，生成小红书图文图片。

### 4.2 能力要求

图片模型最好支持：

- 文生图
- 图生图或参考图生图
- 多张参考图输入
- 风格一致性
- 批量生成
- 竖图比例，如 3:4 或 4:5
- 生成结果可保存为本地图片

### 4.3 输入

```json
{
  "prompt": "请根据参考图风格生成一张小红书图文页...",
  "ref_images": [
    "assets/refs/my_style/cover/cover_01.png",
    "assets/refs/my_style/cover/cover_02.png"
  ],
  "size": "1080x1440",
  "page": {
    "page": 1,
    "type": "cover",
    "main_text": "5个AI工具",
    "sub_text": "少做重复活",
    "visual_instruction": "封面要醒目、标题清晰"
  }
}
```

### 4.4 输出

```json
{
  "image_path": "assets/outputs/20260514_173000_ai_tools/cover.png",
  "provider": "ark",
  "model": "Doubao-Seedream-5.0-lite",
  "page": 1
}
```

### 4.5 推荐抽象函数

```python
def generate_image_with_refs(
    prompt: str,
    ref_images: list[str],
    output_path: str,
    size: str = "1080x1440"
) -> str:
    ...
```

批量生成：

```python
def generate_images_for_note(
    pages: list[dict],
    style_profile: dict,
    ref_dir: str,
    output_dir: str
) -> list[str]:
    ...
```

### 4.6 可选供应商

第一版图片模型确定使用：

```bash
IMAGE_MODEL_PROVIDER=ark
IMAGE_MODEL_NAME=Doubao-Seedream-5.0-lite
IMAGE_MODEL_ID=doubao-seedream-5-0-260128
ARK_API_KEY=你的火山方舟Key
```

| 供应商 | 可用模型类型 | 备注 |
|---|---|---|
| 火山方舟 | Doubao-Seedream-5.0-lite | 第一版图片模型，负责根据参考图和图片页文案生成小红书图文图片 |
| 阿里云百炼 | 通义万相 | 支持图像生成、编辑、风格相关能力 |
| 火山方舟 | Seedream 等图像模型 | 适合中文图片生成和多图参考场景 |
| OpenAI | 图像生成模型 | 适合高质量图像生成和编辑 |
| 其他图像服务 | 文生图/图生图模型 | 只要能封装成统一函数即可 |

## 5. 接口三：多模态风格分析 API（可选）

### 5.1 用途

读取参考图，总结稳定的视觉风格，减少每次生成图片时的随机性。

### 5.2 输入

```json
{
  "ref_images": [
    "assets/refs/my_style/cover/cover_01.png",
    "assets/refs/my_style/content/content_01.png"
  ],
  "analysis_goal": "总结小红书图文设计风格"
}
```

### 5.3 输出

```json
{
  "color_palette": "高明度背景，重点色用于标题和关键词",
  "layout": "封面大标题居中，内容页分块说明",
  "typography": "标题大而粗，正文短句，层级清楚",
  "visual_elements": "使用少量图标、线框、标签块",
  "avoid": "不要复杂背景、不要过多小字、不要水印"
}
```

### 5.4 推荐抽象函数

```python
def analyze_style_from_refs(ref_images: list[str]) -> dict:
    ...
```

## 6. 接口四：文本安全审核 API（可选）

### 6.1 用途

检查标题、正文和话题中是否包含明显违规、夸大、敏感或平台不友好的表达。

### 6.2 输入

```json
{
  "title": "这5个AI工具，真的帮我少做了很多重复活",
  "body": "最近我把工作里最重复的几个环节重新整理了一下...",
  "hashtags": ["AI工具", "效率工具", "职场干货"]
}
```

### 6.3 输出

```json
{
  "passed": true,
  "risk_level": "low",
  "issues": [],
  "suggestions": []
}
```

### 6.4 推荐抽象函数

```python
def review_text_safety(title: str, body: str, hashtags: list[str]) -> dict:
    ...
```

## 7. 接口五：图片安全审核 API（可选）

### 7.1 用途

检查生成图片中是否包含不适合发布的内容。

### 7.2 输入

```json
{
  "images": [
    "assets/outputs/20260514_173000_ai_tools/cover.png",
    "assets/outputs/20260514_173000_ai_tools/image_1.png"
  ]
}
```

### 7.3 输出

```json
{
  "passed": true,
  "risk_level": "low",
  "issues": []
}
```

### 7.4 推荐抽象函数

```python
def review_image_safety(image_paths: list[str]) -> dict:
    ...
```

## 8. 接口六：OCR/图片文字检测 API（可选）

### 8.1 用途

检查生成图片中文字是否可识别，减少图片中文字模糊、错字、乱码的问题。

### 8.2 输入

```json
{
  "image_path": "assets/outputs/20260514_173000_ai_tools/cover.png"
}
```

### 8.3 输出

```json
{
  "detected_text": ["5个AI工具", "少做重复活"],
  "readability": "good",
  "issues": []
}
```

### 8.4 推荐抽象函数

```python
def check_image_text_readability(image_path: str) -> dict:
    ...
```

## 9. 非模型接口：小红书创作平台自动化

这一部分不是模型 API，而是浏览器自动化。

### 9.1 自动化目标

```text
打开小红书创作平台
-> 等待人工登录
-> 上传图片
-> 填写标题
-> 填写正文和话题
-> 停留等待人工确认
```

### 9.2 推荐抽象函数

```python
def create_xhs_draft(
    title: str,
    body: str,
    hashtags: list[str],
    image_paths: list[str],
    user_data_dir: str,
    headless: bool = False
) -> None:
    ...
```

### 9.3 明确不做

- 不自动点击发布。
- 不绕过登录。
- 不自动处理验证码。
- 不规避风控。
- 不调用非公开接口。

## 10. 第一版最小接口配置

`.env` 中至少需要：

```bash
TEXT_MODEL_PROVIDER=ark
TEXT_MODEL_NAME=Doubao-Seed-2.0-lite
ARK_API_KEY=你的火山方舟Key

IMAGE_MODEL_PROVIDER=ark
IMAGE_MODEL_NAME=Doubao-Seedream-5.0-lite
IMAGE_MODEL_ID=doubao-seedream-5-0-260128
```

如果后续切换成其他火山方舟图像模型：

```bash
IMAGE_MODEL_PROVIDER=ark
IMAGE_MODEL_NAME=seedream
ARK_API_KEY=你的火山方舟Key
```

如果使用 OpenAI 或兼容服务：

```bash
IMAGE_MODEL_PROVIDER=openai
IMAGE_MODEL_NAME=gpt-image-1
OPENAI_API_KEY=你的OpenAIKey
```

具体模型名称和调用参数应在实现时放到 `config.py`，不要散落在业务代码里。

## 11. 建议的接口封装层

为避免后续更换供应商时大改业务代码，建议统一封装：

```text
services/
  model_clients/
    __init__.py
    text_client.py
    image_client.py
    style_client.py
    safety_client.py
```

业务层只调用统一接口：

```python
text_client.generate_json(...)
image_client.generate_with_refs(...)
style_client.analyze_refs(...)
safety_client.review_text(...)
```

## 12. 第一版接口优先级

```text
P0：文本生成 API
P0：图片生成 API
P1：多模态风格分析 API
P1：文本安全审核 API
P2：图片安全审核 API
P2：OCR/图片文字检测 API
```

第一版可以先不做 P1/P2，只要保证人工审核页面足够清晰即可。

