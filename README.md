# 小红书减脂餐图文自动化工具

这是一个面向小红书减脂餐内容生产的本地 Streamlit 工具。它可以基于选题生成标题、正文、图片提示词和配图，支持从小红书公开搜索页采集轻量选题灵感，并在人工确认后辅助创建小红书图文草稿。

## 功能概览

- 文案生成：使用 Doubao-Seed-2.0-lite 生成小红书风格标题、正文和发布文案。
- 图片生成：通过 OpenAI 兼容中转站调用 gpt-image-2，生成 3 张主题相关图文配图。
- 参考图管理：读取 `参考图` 文件夹中的封面、内容页、结尾页参考图，页面中默认折叠展示。
- 选题灵感：通过 Playwright 打开小红书搜索页，搜索“减脂餐做法”，采集公开可见卡片信息后提炼原创菜谱选题。
- 内容导入：可从 `assets/outputs` 选择历史生成内容目录导入预览。
- 草稿辅助：登录后可辅助进入小红书创作页上传图片并填充标题正文，但不会自动发布。

## 目录说明

```text
.
├── app.py                         # Streamlit 主入口
├── config.py                      # 环境变量配置
├── requirements.txt               # Python 依赖
├── prompts/                       # 文案、图片、审核、选题提炼提示词
├── services/                      # 生成、导出、审核、采集等服务
├── automation/                    # 小红书发布页 Playwright 自动化
├── 参考图/                        # 图片生成参考图
├── 完整方案.md                    # 产品与实现方案
└── 模型接口API清单.md             # 模型接口清单
```

运行时产生的内容会写入 `assets/outputs`，浏览器登录态会写入 `browser_profile/xhs`。这些目录已被 `.gitignore` 排除，不会上传到仓库。

## 快速开始

### Windows 双击启动

在 Windows 上可以直接双击项目根目录里的：

```text
start_windows_app.bat
```

它会自动启动 Streamlit 服务，并打开默认浏览器访问 `http://127.0.0.1:8501`。

首次运行前仍需要先安装依赖：

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
```

如果想让同一局域网内的其他设备访问，可以在 PowerShell 中这样启动：

```powershell
$env:STREAMLIT_ADDRESS="0.0.0.0"
.\start_windows_app.bat
```

然后在其他设备浏览器打开 `http://本机局域网IP:8501`。例如本机 IP 是 `192.168.111.10` 时，访问 `http://192.168.111.10:8501`。

### 从 Git 远程拉取运行

如果要在另一台电脑或服务器上通过 Git 打开项目，先拉取远程仓库：

```bash
git clone https://github.com/boxsmall/Xiaohongshu_automatic_posting_tool.git
cd Xiaohongshu_automatic_posting_tool
```

然后按下面步骤安装依赖、配置 `.env` 并启动 Streamlit。启动成功后，在当前机器浏览器打开 `http://127.0.0.1:8501`。

如果部署在远程服务器上，需要把启动地址改为可被外部访问：

```bash
python -m streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

然后通过 `http://服务器IP:8501` 访问。服务器防火墙或安全组需要放行 `8501` 端口。

注意：GitHub 只是 Git 代码仓库，不能直接运行这个 Streamlit 后端项目。想要一个公网网页链接，需要部署到 Streamlit Cloud、Render、Railway 或自有服务器，并在部署平台配置 `ARK_API_KEY`、`OPENAI_IMAGE_BASE_URL`、`OPENAI_IMAGE_API_KEY` 等环境变量。

1. 安装依赖：

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
```

2. 创建本地环境变量文件：

```bash
copy .env.example .env
```

然后在 `.env` 中填入你的火山方舟 `ARK_API_KEY`，以及图片中转站的 `OPENAI_IMAGE_BASE_URL` 和 `OPENAI_IMAGE_API_KEY`。当前默认模型配置为：

- 文案模型：`Doubao-Seed-2.0-lite`
- 图片模型：`gpt-image-2`

图片模型走 OpenAI Images API 兼容中转站：

```env
IMAGE_MODEL_PROVIDER=openai_relay
IMAGE_MODEL_NAME=gpt-image-2
IMAGE_MODEL_ID=gpt-image-2
OPENAI_IMAGE_BASE_URL=https://你的中转站地址/v1
OPENAI_IMAGE_API_KEY=你的中转站Key
OPENAI_IMAGE_USE_ENV_PROXY=false
OPENAI_IMAGE_FALLBACK_TO_GENERATION=true
OPENAI_IMAGE_RETRY_COUNT=1
OPENAI_IMAGE_RETRY_DELAY_SECONDS=2
IMAGE_SIZE=auto
IMAGE_OUTPUT_FORMAT=png
```

`OPENAI_IMAGE_BASE_URL` 推荐填写到 `/v1`，如果只填写中转站根域名，程序会自动补 `/v1`。
默认不继承系统代理，避免中转站请求被本机代理干扰；如果你的中转站必须通过本机代理访问，再把 `OPENAI_IMAGE_USE_ENV_PROXY=true`。
如果中转站在 `/images/edits` 上返回 `524` 或其他临时 5xx，程序会先重试，再自动降级到 `/images/generations`，用纯文本提示词生成图片。

如果中转站不是 OpenAI Images API 兼容格式，需要按中转站文档调整 `services/model_clients/image_client.py` 的请求字段。

3. 启动页面：

```bash
python -m streamlit run app.py --server.port 8501 --server.address 127.0.0.1
```

浏览器打开 `http://127.0.0.1:8501` 即可使用。

## 使用流程

1. 可手动输入减脂餐选题，或点击“从小红书自动找选题”采集灵感。
2. 点击“生成内容”，系统会生成文案、图片提示词和 3 张配图。
3. 在页面预览标题、正文、图片和审核结果。
4. 审核通过后，可点击生成小红书草稿。脚本只会辅助填写草稿，不会自动发布。
5. 历史内容可通过“选择已生成内容文件夹”下拉框重新导入。

## 安全边界

- 不上传 `.env`，不要把真实 API Key 写入文档或代码。
- 不上传 `browser_profile`，避免泄露小红书登录态。
- 不绕过登录、验证码或风控。
- 不自动点赞、收藏、评论、关注或发布。
- 小红书搜索采集只读取公开可见卡片信息，用于趋势参考，不复制原文。

## 常见问题

### 访问 `127.0.0.1:8501` 提示连接被拒绝

说明 Streamlit 服务没有运行或已退出。重新执行启动命令即可。

### 小红书草稿停留在登录或验证页面

这是正常保护机制。请在浏览器中手动完成登录或验证，脚本不会尝试绕过。

### 图片上传误入视频发布页

脚本会优先切换到图文模式，并只选择支持图片的 file input。如果小红书页面结构变化，错误信息会输出当前 file input 的调试信息，方便继续适配。
