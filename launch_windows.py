from __future__ import annotations

import importlib.util
import os
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
APP_FILE = ROOT_DIR / "app.py"
ENV_FILE = ROOT_DIR / ".env"
ENV_EXAMPLE_FILE = ROOT_DIR / ".env.example"


def _port_is_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def _ensure_env_file() -> None:
    if ENV_FILE.exists() or not ENV_EXAMPLE_FILE.exists():
        return

    shutil.copyfile(ENV_EXAMPLE_FILE, ENV_FILE)
    print("已自动创建 .env，请在里面填写真实的 ARK_API_KEY 后再生成内容。")


def _require_streamlit() -> bool:
    if importlib.util.find_spec("streamlit") is not None:
        return True

    print("没有检测到 Streamlit。请先在当前目录执行：")
    print("python -m pip install -r requirements.txt")
    print("python -m playwright install chromium")
    return False


def main() -> int:
    os.chdir(ROOT_DIR)
    _ensure_env_file()

    if not APP_FILE.exists():
        print(f"找不到入口文件：{APP_FILE}")
        return 1

    if not _require_streamlit():
        return 1

    port = int(os.getenv("STREAMLIT_PORT", "8501"))
    address = os.getenv("STREAMLIT_ADDRESS", "127.0.0.1")
    browser_host = "127.0.0.1" if address in {"0.0.0.0", "::"} else address
    url = f"http://{browser_host}:{port}"

    if _port_is_open(browser_host, port):
        print(f"检测到工具已经在运行，正在打开：{url}")
        webbrowser.open(url)
        return 0

    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(APP_FILE),
        "--server.port",
        str(port),
        "--server.address",
        address,
        "--server.headless",
        "true",
    ]

    print("正在启动小红书图文工具...")
    print(f"本机访问地址：{url}")
    if address == "0.0.0.0":
        print("当前已开启局域网访问，请用本机局域网 IP 加端口访问。")

    process = subprocess.Popen(command, cwd=ROOT_DIR)

    for _ in range(80):
        if process.poll() is not None:
            return process.returncode or 1
        if _port_is_open(browser_host, port):
            webbrowser.open(url)
            break
        time.sleep(0.5)
    else:
        print("服务启动时间较长，请稍等后手动打开浏览器访问上面的地址。")

    try:
        return process.wait()
    except KeyboardInterrupt:
        print("正在关闭服务...")
        process.terminate()
        try:
            return process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            return process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
