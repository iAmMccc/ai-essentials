#!/usr/bin/env python3
"""
抖音视频转文档
输入抖音链接，自动提取字幕或语音转文字，再通过 AI 总结生成 Markdown。

用法: python3 douyin-to-doc.py "抖音视频链接"

依赖: playwright, ffmpeg, openai-whisper (可选)
"""

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
import urllib.request
import urllib.error


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_JSON = os.path.join(SCRIPT_DIR, "cookies.json")


def check_command(cmd):
    """检查命令是否可用"""
    try:
        subprocess.run([cmd, "--version"], capture_output=True, check=False)
        return True
    except FileNotFoundError:
        return False


def check_cookies():
    """检查 Cookie 文件是否存在"""
    if not os.path.exists(COOKIES_JSON):
        return False
    if os.path.getsize(COOKIES_JSON) < 50:
        return False
    return True


async def fetch_video_page(url):
    """用 Playwright 打开抖音页面，提取视频标题和音频/视频地址"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("错误: 需要安装 playwright")
        print("  pip install playwright && python -m playwright install chromium")
        sys.exit(1)

    # 加载 Cookie
    with open(COOKIES_JSON, "r", encoding="utf-8") as f:
        cookies = json.load(f)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        # 注入 Cookie
        await context.add_cookies(cookies)

        page = await context.new_page()

        print("正在加载页面...")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # 等待页面渲染
        await asyncio.sleep(8)

        # 提取标题
        title = "douyin_video"
        try:
            for selector in [
                'meta[property="og:title"]',
                'meta[name="title"]',
                "title"
            ]:
                el = await page.query_selector(selector)
                if el:
                    content = await el.get_attribute("content") if selector != "title" else await el.inner_text()
                    if content and len(content) > 2:
                        title = content.split(" - ")[0].strip()
                        break

            if title == "douyin_video":
                desc_el = await page.query_selector('[data-e2e="video-desc"]')
                if desc_el:
                    desc = await desc_el.inner_text()
                    if desc and len(desc) > 2:
                        title = desc[:50]
        except Exception:
            pass

        title = re.sub(r'[\\/:*?"<>|\n\r]', '_', title).strip()

        # 从页面 script 标签中提取视频信息（抖音把视频数据嵌入在 SSR JSON 中）
        video_url = None
        try:
            video_url = await page.evaluate("""
                () => {
                    // 方法 1：从 video 元素的 source 获取
                    const video = document.querySelector('video source');
                    if (video && video.src) return video.src;

                    const videoEl = document.querySelector('video');
                    if (videoEl && videoEl.src && videoEl.src.startsWith('http')) return videoEl.src;

                    // 方法 2：从页面 SSR 数据中提取
                    const scripts = document.querySelectorAll('script');
                    for (const s of scripts) {
                        const text = s.textContent || '';
                        // 查找包含 playAddr 的 JSON
                        if (text.includes('playAddr') || text.includes('play_addr')) {
                            try {
                                // 尝试匹配 JSON 中的视频地址
                                const match = text.match(/"playApi"\\s*:\\s*"([^"]+)"/);
                                if (match) return match[1];

                                const match2 = text.match(/"play_addr"\\s*:\\s*\\{[^}]*"url_list"\\s*:\\s*\\["([^"]+)"/);
                                if (match2) return match2[1];
                            } catch(e) {}
                        }
                    }

                    // 方法 3：从 __RENDER_DATA__ 中提取
                    const renderData = document.getElementById('RENDER_DATA');
                    if (renderData) {
                        try {
                            const decoded = decodeURIComponent(renderData.textContent);
                            const match = decoded.match(/"playApi"\\s*:\\s*"([^"]+)"/);
                            if (match) return match[1];
                        } catch(e) {}
                    }

                    return null;
                }
            """)
        except Exception:
            pass

        # 如果从 JS 拿到的是相对路径，补全域名
        if video_url and not video_url.startswith("http"):
            video_url = "https:" + video_url if video_url.startswith("//") else "https://www.douyin.com" + video_url

        await browser.close()
        return title, video_url


def download_media(video_url, output_path):
    """下载视频/音频文件"""
    print("正在下载音频...")
    try:
        req = urllib.request.Request(video_url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://www.douyin.com/"
        })
        with urllib.request.urlopen(req, timeout=60) as resp:
            with open(output_path, "wb") as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"  已下载（{size_mb:.1f} MB）")
        return True
    except Exception as e:
        print(f"  下载失败: {e}")
        return False


def extract_audio(video_path, audio_path):
    """从视频中提取音频"""
    try:
        subprocess.run(
            ["ffmpeg", "-i", video_path, "-vn", "-acodec", "libmp3lame", "-q:a", "4", audio_path, "-y"],
            capture_output=True, check=True, timeout=60
        )
        return True
    except Exception:
        return False


def transcribe_audio(audio_path):
    """Whisper 语音转文字"""
    try:
        import whisper
    except ImportError:
        print("错误: 需要 openai-whisper 来进行语音转文字")
        print("安装: pip install openai-whisper")
        return None

    print("正在语音转文字（首次使用需下载模型）...")
    model = whisper.load_model("base")
    result = model.transcribe(audio_path, language="zh")
    text = result.get("text", "").strip()

    if text:
        print(f"  转写完成（{len(text)} 字）")
    else:
        print("  转写结果为空")

    return text


def ai_summarize(text, config):
    """AI 总结"""
    api_base = config.get("api_base", "").rstrip("/")
    api_key = config.get("api_key", "")
    model = config.get("model", "doubao-1-5-lite-32k")

    if not api_base or not api_key:
        return None

    print(f"正在 AI 总结（{model}）...")

    prompt = f"""请根据以下视频文字内容，生成一份结构化的 Markdown 文档。

要求：
1. 先写一段 3-5 句话的摘要
2. 然后是完整的正文内容（整理通顺，去掉口语化的语气词）
3. 最后提炼 3-8 个要点

视频文字内容：
{text}"""

    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 4096
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{api_base}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            print("  总结完成")
            return content
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        print(f"  AI 总结失败（HTTP {e.code}）: {body[:200]}")
        return None
    except Exception as e:
        print(f"  AI 总结失败: {e}")
        return None


def generate_markdown(title, raw_text, ai_summary=None):
    """生成最终的 Markdown 文档"""
    if ai_summary:
        return f"# {title}\n\n{ai_summary}\n"
    else:
        return f"# {title}\n\n## 正文\n\n{raw_text}\n"


def load_config():
    """加载配置文件"""
    for path in ["config.json", os.path.join(SCRIPT_DIR, "..", "config.json")]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    return {}


def main():
    parser = argparse.ArgumentParser(description="抖音视频转 Markdown 文档")
    parser.add_argument("url", help="抖音视频链接")
    parser.add_argument("--api-base", help="AI API 地址（覆盖 config.json）")
    parser.add_argument("--api-key", help="AI API Key（覆盖 config.json）")
    parser.add_argument("--model", help="AI 模型名称（覆盖 config.json）")
    parser.add_argument("--no-ai", action="store_true", help="跳过 AI 总结，只输出原始文字")
    args = parser.parse_args()

    # 检查依赖
    if not check_command("ffmpeg"):
        print("错误: 需要安装 ffmpeg")
        print("安装: brew install ffmpeg")
        sys.exit(1)

    # 检查 Cookie
    if not check_cookies():
        print("未检测到抖音登录信息，请先执行登录：")
        print(f"  python3 {os.path.join(SCRIPT_DIR, 'douyin-login.py')}")
        sys.exit(1)

    # 加载配置
    config = load_config()
    if args.api_base:
        config["api_base"] = args.api_base
    if args.api_key:
        config["api_key"] = args.api_key
    if args.model:
        config["model"] = args.model

    # 用 Playwright 加载页面，提取标题和视频地址
    print(f"正在解析: {args.url}")
    title, video_url = asyncio.run(fetch_video_page(args.url))
    print(f"视频标题: {title}")

    if not video_url:
        print("错误: 无法从页面提取视频地址")
        sys.exit(1)

    # 下载视频并提取音频，然后转文字
    raw_text = None
    with tempfile.TemporaryDirectory() as work_dir:
        video_path = os.path.join(work_dir, "video.mp4")
        audio_path = os.path.join(work_dir, "audio.mp3")

        if download_media(video_url, video_path):
            # 提取音频
            print("正在提取音频...")
            if extract_audio(video_path, audio_path):
                raw_text = transcribe_audio(audio_path)
            else:
                # 可能本身就是音频文件，直接转写
                raw_text = transcribe_audio(video_path)

    if not raw_text:
        print("错误: 无法提取视频文字内容")
        sys.exit(1)

    # AI 总结
    ai_summary = None
    if not args.no_ai and config.get("api_key"):
        ai_summary = ai_summarize(raw_text, config)
    elif not args.no_ai and not config.get("api_key"):
        print("未配置 AI（跳过总结，只输出原始文字）")

    # 生成 Markdown
    markdown = generate_markdown(title, raw_text, ai_summary)
    output_path = f"{title}.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"\n已生成: {output_path}")


if __name__ == "__main__":
    main()
