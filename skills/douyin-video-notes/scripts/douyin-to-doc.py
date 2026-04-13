#!/usr/bin/env python3
"""
抖音视频转文档
输入抖音链接，自动提取字幕，通过 AI 总结生成 Markdown。

用法: python3 douyin-to-doc.py "抖音视频链接"

依赖: playwright, ffmpeg, openai-whisper
"""

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
from pathlib import Path
import urllib.request
import urllib.error


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_JSON = os.path.join(SCRIPT_DIR, "cookies.json")


def check_command(cmd):
    try:
        subprocess.run([cmd, "--version"], capture_output=True, check=False)
        return True
    except FileNotFoundError:
        return False


def check_cookies():
    if not os.path.exists(COOKIES_JSON):
        return False
    if os.path.getsize(COOKIES_JSON) < 50:
        return False
    return True


def extract_url_from_text(text):
    """从分享文本中提取 URL"""
    match = re.search(r"https?://[^\s]+", text)
    return match.group(0).rstrip("/") if match else text


def extract_video_id(url):
    """从各种抖音链接格式中提取视频 ID"""
    # 去掉 zsh 转义
    url = url.replace(r"\?", "?").replace(r"\=", "=").replace(r"\&", "&")

    # 精选页 / 搜索结果：视频 ID 在 modal_id 参数里
    modal_match = re.search(r"modal_id=(\d+)", url)
    if modal_match:
        return modal_match.group(1)

    # 标准链接：/video/数字ID
    match = re.search(r"/video/(\d+)", url)
    if match:
        return match.group(1)

    return None


def resolve_video_id(raw_input):
    """从任意格式的输入中解析出视频 ID"""
    # 先从文本中提取 URL（处理分享文本）
    url = extract_url_from_text(raw_input)

    # 直接尝试提取 video ID（标准链接、精选页、搜索结果）
    vid = extract_video_id(url)
    if vid:
        return vid

    # 短链接：需要重定向解析
    if "v.douyin.com" in url or "iesdouyin.com" in url:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                final_url = resp.url
                vid = extract_video_id(final_url)
                if vid:
                    return vid
        except Exception:
            pass

    return None


def fetch_video_info(video_id):
    """通过移动端分享页获取视频元数据（无需登录）"""

    info = {
        "title": "douyin_video",
        "video_url": None,
        "author": "",
        "tags": [],
        "likes": "",
        "comments_count": "",
        "favorites": "",
        "shares": "",
        "publish_time": "",
    }

    # 请求移动端分享页（无需登录）
    share_url = f"https://www.iesdouyin.com/share/video/{video_id}/"
    try:
        req = urllib.request.Request(share_url, headers={
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  请求失败: {e}")
        return info

    # 提取元数据
    def extract(pattern, text, default=""):
        m = re.search(pattern, text)
        return m.group(1) if m else default

    raw_desc = extract(r'"desc":"([^"]*)"', html)
    info["author"] = extract(r'"nickname":"([^"]*)"', html)
    info["likes"] = extract(r'"digg_count":(\d+)', html)
    info["comments_count"] = extract(r'"comment_count":(\d+)', html)
    info["favorites"] = extract(r'"collect_count":(\d+)', html)
    info["shares"] = extract(r'"share_count":(\d+)', html)

    # 发布时间
    create_time = extract(r'"create_time":(\d+)', html)
    if create_time:
        from datetime import datetime
        info["publish_time"] = datetime.fromtimestamp(int(create_time)).strftime("%Y-%m-%d %H:%M")

    # 从描述中分离标题和标签
    tags = re.findall(r"#(\S+)", raw_desc)
    clean_title = re.sub(r"\s*#\S+", "", raw_desc).strip()
    if not clean_title:
        clean_title = "douyin_video"
    clean_title = re.sub(r'[\\/:*?"<>|\n\r]', '_', clean_title).strip()
    if len(clean_title) > 80:
        clean_title = clean_title[:80]

    info["title"] = clean_title
    info["tags"] = tags

    # 视频下载地址
    play_match = re.search(r'"play_addr":\{[^}]*"url_list":\["([^"]+)"', html)
    if play_match:
        video_url = play_match.group(1).replace("\\u002F", "/")
        if not video_url.startswith("http"):
            video_url = "https:" + video_url
        info["video_url"] = video_url

    return info


async def fetch_comments(url, video_author="", max_scroll=5):
    """用 Playwright 打开页面，滚动加载评论并提取"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return []

    with open(COOKIES_JSON, "r", encoding="utf-8") as f:
        cookies = json.load(f)

    # 由调用方打印进度

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        await context.add_cookies(cookies)
        page = await context.new_page()

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(5)

        # 滚动页面加载评论
        for i in range(max_scroll):
            await page.evaluate("window.scrollBy(0, 800)")
            await asyncio.sleep(2)

        # 提取评论区全文
        raw_text = await page.evaluate("""
            () => {
                const container = document.querySelector('[class*="comment-mainContent"]');
                return container ? container.innerText : '';
            }
        """)

        # 从 DOM 获取带「作者」标签的用户名列表
        author_tagged = await page.evaluate("""
            () => {
                const tags = document.querySelectorAll('[class*="comment-item-tag-text"]');
                const names = new Set();
                for (const tag of tags) {
                    if (tag.innerText.trim() === '作者') {
                        // 往上找到 info-wrap，取第一个子元素（用户名）
                        const wrap = tag.closest('[class*="comment-item-info-wrap"]');
                        if (wrap && wrap.children[0]) {
                            const name = wrap.children[0].innerText.trim().replace('\\n作者', '').trim();
                            names.add(name);
                        }
                    }
                }
                return Array.from(names);
            }
        """)

        await browser.close()

        # 合并作者识别：页面提取的作者名 + DOM 标签标记的作者
        author_names = set(author_tagged or [])
        if video_author:
            author_names.add(video_author)

        # 解析评论文本
        comments = parse_comment_text(raw_text, author_names)
        # 由调用方打印进度
        return comments


def parse_comment_text(raw_text, author_names=None):
    """解析评论区的纯文本，提取结构化评论"""
    if not raw_text or not raw_text.strip():
        return []

    author_names = author_names or set()
    comments = []
    lines = raw_text.strip().split("\n")

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 跳过空行和系统文字
        if not line or line in ("分享", "回复", "加载中", "全部评论", "...") or line.startswith("展开"):
            i += 1
            continue

        # 跳过时间行
        if re.match(r"^\d+.*前·", line) or re.match(r"^\d{4}-", line):
            i += 1
            continue

        # 跳过纯数字行（点赞数）
        if re.match(r"^\d+$", line):
            i += 1
            continue

        # 跳过标签
        if line == "作者":
            i += 1
            continue

        # 剩下的非空行：可能是作者名或评论内容
        # 规律：作者名后面跟 ... 再跟评论内容
        author = line
        content = ""

        # 向后找内容
        j = i + 1
        while j < len(lines):
            next_line = lines[j].strip()
            if next_line == "...":
                j += 1
                continue
            if next_line == "作者":
                j += 1
                continue
            if not next_line:
                j += 1
                continue
            # 时间行说明上一条评论结束
            if re.match(r"^\d+.*前·", next_line) or re.match(r"^\d{4}-", next_line):
                break
            # 纯数字（点赞数）或操作按钮
            if next_line in ("分享", "回复") or re.match(r"^\d+$", next_line):
                break
            if next_line.startswith("展开"):
                break
            # 这就是评论内容
            content = next_line
            break

        if content and len(content) > 1:
            # 找点赞数（在时间行之后的纯数字）
            likes = "0"
            for k in range(j, min(j + 5, len(lines))):
                lk = lines[k].strip()
                if re.match(r"^\d+$", lk):
                    likes = lk
                    break

            is_author = author in author_names
            comments.append({
                "author": author,
                "content": content,
                "likes": likes,
                "is_author": is_author
            })

        i = j + 1 if j > i else i + 1

    return comments


def save_comments(comments, raw_dir):
    """保存评论到 raw 目录"""
    if not comments:
        return

    # JSON 格式（原始数据）
    json_path = os.path.join(raw_dir, "comments.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(comments, f, ensure_ascii=False, indent=2)

    # TXT 格式（可读）
    txt_path = os.path.join(raw_dir, "comments.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        for c in comments:
            author = c.get("author", "匿名")
            content = c.get("content", "")
            likes = c.get("likes", "0")
            tag = "（作者）" if c.get("is_author") else ""
            f.write(f"[{author}]{tag} {content}")
            if likes and likes != "0":
                f.write(f"  ({likes} 赞)")
            f.write("\n")

    # 由调用方打印进度


def download_file(url, output_path):
    """下载文件"""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://www.douyin.com/"
        })
        with urllib.request.urlopen(req, timeout=120) as resp:
            with open(output_path, "wb") as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        return size_mb
    except Exception as e:
        print(f"  下载失败: {e}")
        return 0


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
        print("错误: 需要 openai-whisper")
        print("安装: pip install openai-whisper")
        return None

    model = whisper.load_model("base")
    result = model.transcribe(audio_path, language="zh")

    # 带换行的完整文本（按 segment 分段）
    segments = result.get("segments", [])
    if segments:
        lines = [seg.get("text", "").strip() for seg in segments if seg.get("text", "").strip()]
        text = "\n".join(lines)
    else:
        text = result.get("text", "").strip()

    if not text:
        text = None

    return text


def cleanup_ai_output(text):
    """后处理：清理 AI 输出中的第三方视角用词"""
    replacements = [
        ("该内容", ""),
        ("该方法", "这个方法"),
        ("该视频", ""),
        ("该技巧", "这个技巧"),
        ("该工具", "这个工具"),
        ("该流程", "这个流程"),
        ("作者指出", ""),
        ("作者提到", ""),
        ("作者分享了", ""),
        ("视频讲解了", ""),
        ("视频中提到", ""),
        ("本视频", ""),
        ("部分开发者", "开发者"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)

    # 清理替换后可能出现的多余空格和空行
    text = re.sub(r"  +", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text


def ai_summarize(text, supplements_text, config, comments_text="", video_info=None):
    """AI 总结"""
    api_base = config.get("api_base", "").rstrip("/")
    api_key = config.get("api_key", "")
    model = config.get("model", "doubao-seed-2-0-mini-260215")

    if not api_base or not api_key:
        return None

    # 由调用方打印进度

    has_supplements = bool(supplements_text and supplements_text.strip())
    has_comments = bool(comments_text and comments_text.strip())

    parts = ["原始内容"]
    if has_comments:
        parts.append("评论区")
    if has_supplements:
        parts.append("用户补充信息")
    basis = " + ".join(parts)

    # 构建来源元数据
    vi = video_info or {}
    meta_lines = [f"- 链接：（由调用方填入）"]
    if vi.get("author"):
        meta_lines.append(f"- 作者：{vi['author']}")
    if vi.get("publish_time"):
        meta_lines.append(f"- 发布时间：{vi['publish_time']}")
    if vi.get("tags"):
        meta_lines.append(f"- 标签：{'、'.join(vi['tags'])}")
    if vi.get("likes"):
        meta_lines.append(f"- 数据：{vi['likes']} 赞 · {vi['comments_count']} 评论 · {vi['favorites']} 收藏 · {vi['shares']} 转发")
    meta_lines.append(f"- 生成依据：{basis}")
    meta_block = "\n".join(meta_lines)

    prompt = f"""把下面的视频内容整理成学习笔记。直接写知识点，不要转述。

格式要求和示例：

## 来源
{meta_block}

## 摘要
示例（注意语气）：
「Vibe Coding 从零开始不要凭空让 AI 写代码，正确做法是从 GitHub 找成熟开源项目，让 AI 学习后按需改造，效率远高于从零开发。」
（2-3 句话，不超过 100 字。像上面的示例一样直接写观点。禁止用「该内容」「该视频」「该方法」开头。）

## 要点
示例（注意语气）：
- 不要凭空让 AI 从零写代码
- 从 GitHub 找成熟开源项目作为基础
- 让 AI 学习项目代码后按需改造
（3-8 条，每条不超过 30 字。禁止用「该」字开头。）

## 正文
示例（注意语气）：
「### 常见误区
直接用 AI 从零写代码容易陷入需求模糊、代码破碎的死循环。问题不在 AI 能力不够，而是没有给它好的参考基础。
### 正确做法
从 GitHub 找一个成熟的开源项目...
### 注意事项
使用开源项目时要遵守对应的开源协议。」
（像上面的示例一样，直接写知识点。用小标题分段。评论区有价值的信息融入正文。禁止出现「该方法」「作者指出」「视频中提到」。）

## 评论
（保留有价值的讨论，忽略纯求资源的。）

禁止用词清单（全文不得出现）：该内容、该方法、该视频、该技巧、作者指出、视频讲解、本视频、部分开发者

视频文字内容：
{text}"""

    if has_supplements:
        prompt += f"""

用户补充信息：
{supplements_text}"""

    if comments_text:
        prompt += f"""

评论区内容：
{comments_text}

评论区处理规则：
- 标记为（作者）的评论是视频作者的补充说明，将有价值的信息融入正文
- 其他用户的评论单独作为「## 评论」章节，保留有价值的反馈和讨论
- 忽略纯求资源、纯表情、无实质内容的评论
- 如果有作者对用户的回复，保留对话关系"""

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
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            return cleanup_ai_output(content)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        print(f"  AI 总结失败（HTTP {e.code}）: {body[:200]}")
        return None
    except Exception as e:
        print(f"  AI 总结失败: {e}")
        return None


def load_supplements(supplements_dir):
    """读取补充信息目录下的所有文本内容（忽略未编辑的模板）"""
    texts = []
    if not os.path.isdir(supplements_dir):
        return ""

    # 模板中的占位文字，匹配到说明用户没有编辑过
    placeholder_markers = ["在这里添加你的补充信息", "（在这里添加"]

    for f in sorted(Path(supplements_dir).iterdir()):
        if f.is_file() and f.suffix in (".md", ".txt"):
            try:
                content = f.read_text(encoding="utf-8").strip()
                if not content:
                    continue
                # 检查是否是未编辑的模板
                is_template = any(marker in content for marker in placeholder_markers)
                if is_template:
                    continue
                texts.append(f"--- {f.name} ---\n{content}")
            except Exception:
                pass
    return "\n\n".join(texts)


def load_config():
    for path in ["config.json", os.path.join(SCRIPT_DIR, "..", "config.json")]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    return {}


def get_next_version(output_dir):
    """获取下一个版本号"""
    existing = list(Path(output_dir).glob("v*.md"))
    if not existing:
        return "v1"
    nums = []
    for f in existing:
        match = re.match(r"v(\d+)", f.stem)
        if match:
            nums.append(int(match.group(1)))
    return f"v{max(nums) + 1}" if nums else "v1"



def main():
    parser = argparse.ArgumentParser(description="抖音视频转 Markdown 文档")
    parser.add_argument("url", help="抖音视频链接")
    parser.add_argument("--api-base", help="AI API 地址（覆盖 config.json）")
    parser.add_argument("--api-key", help="AI API Key（覆盖 config.json）")
    parser.add_argument("--model", help="AI 模型名称（覆盖 config.json）")
    parser.add_argument("--no-ai", action="store_true", help="跳过 AI 总结")
    parser.add_argument("--output-dir", default="output", help="输出根目录（默认 output）")
    args = parser.parse_args()

    # 检查依赖
    if not check_command("ffmpeg"):
        print("错误: 需要安装 ffmpeg")
        print("安装: brew install ffmpeg")
        sys.exit(1)

    # 加载配置
    config = load_config()
    if args.api_base:
        config["api_base"] = args.api_base
    if args.api_key:
        config["api_key"] = args.api_key
    if args.model:
        config["model"] = args.model

    # 解析视频 ID
    print(f"· 解析链接...", end="", flush=True)
    video_id = resolve_video_id(args.url)
    if not video_id:
        print("失败（无法提取视频 ID）")
        sys.exit(1)
    clean_url = f"https://www.douyin.com/video/{video_id}"
    print(f"完成")

    # 获取视频元数据（无需登录）
    print(f"· 获取视频信息...", end="", flush=True)
    video_info = fetch_video_info(video_id)
    title = video_info["title"]
    video_url = video_info["video_url"]
    author_name = video_info["author"]

    if not video_url:
        print("失败（无法获取视频地址）")
        sys.exit(1)
    print("完成")

    # 视频信息
    print("")
    print("── 视频信息 ──────────────────")
    print(f"  标题: {title}")
    if author_name:
        print(f"  作者: {author_name}")
    if video_info["likes"]:
        print(f"  数据: {video_info['likes']} 赞 · {video_info['comments_count']} 评论 · {video_info['favorites']} 收藏 · {video_info['shares']} 转发")
    if video_info["tags"]:
        print(f"  标签: {', '.join(video_info['tags'])}")
    if video_info["publish_time"]:
        print(f"  发布: {video_info['publish_time']}")
    print("")

    # 创建输出目录结构
    project_dir = os.path.join(args.output_dir, title)
    raw_dir = os.path.join(project_dir, "raw")
    supplements_dir = os.path.join(project_dir, "supplements")
    output_dir = os.path.join(project_dir, "output")

    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(supplements_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    # 文件路径
    video_path = os.path.join(raw_dir, "video.mp4")
    audio_path = os.path.join(raw_dir, "audio.mp3")
    transcript_path = os.path.join(raw_dir, "transcript.txt")

    # 检测已有文件，跳过重复步骤
    has_audio = os.path.exists(audio_path) and os.path.getsize(audio_path) > 1000
    has_video = os.path.exists(video_path) and os.path.getsize(video_path) > 1000
    has_transcript = os.path.exists(transcript_path) and os.path.getsize(transcript_path) > 10

    if has_transcript:
        print("· 检测到已有字幕，跳过下载和转写")
        transcript = Path(transcript_path).read_text(encoding="utf-8")
    else:
        if has_audio:
            print("· 检测到已有音频，跳过下载")
        else:
            print("· 下载视频...", end="", flush=True)
            size = download_file(video_url, video_path)
            if size == 0:
                print("失败")
                sys.exit(1)
            print(f"完成（{size:.1f} MB）")

            print("· 提取音频...", end="", flush=True)
            if not extract_audio(video_path, audio_path):
                audio_path = video_path
                print("跳过（直接使用视频文件）")
            else:
                audio_size = os.path.getsize(audio_path) / (1024 * 1024)
                print(f"完成（{audio_size:.1f} MB）")

            # 视频默认保留在 raw/ 目录

        # 语音转文字
        import warnings
        print("· 转为文字...", end="", flush=True)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            transcript = transcribe_audio(audio_path)
        if not transcript:
            print("失败")
            sys.exit(1)
        print(f"完成（{len(transcript)} 字）")

        # 保存字幕
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(transcript)

    # 获取评论（需要登录，可选）
    comments_json_path = os.path.join(raw_dir, "comments.json")
    comments_txt_path = os.path.join(raw_dir, "comments.txt")
    if not os.path.exists(comments_json_path):
        if check_cookies():
            print("· 获取评论...", end="", flush=True)
            comments = asyncio.run(fetch_comments(clean_url, video_author=author_name))
            if comments:
                save_comments(comments, raw_dir)
                print(f"完成（{len(comments)} 条）")
            else:
                print("无评论")
        else:
            print("· 跳过评论获取（未登录）")
    else:
        print("· 检测到已有评论，跳过获取")

    # 生成补充信息模板（如果不存在）
    extra_path = os.path.join(supplements_dir, "extra.md")
    if not os.path.exists(extra_path):
        with open(extra_path, "w", encoding="utf-8") as f:
            f.write(f"# 补充信息\n\n")
            f.write(f"视频链接: {clean_url}\n\n")
            f.write(f"（在这里添加额外信息：GitHub 地址、工具名称、关键截图描述、相关链接等）\n")

    # 读取评论文本（参与 AI 总结）
    comments_text = ""
    if os.path.exists(comments_txt_path):
        comments_text = Path(comments_txt_path).read_text(encoding="utf-8").strip()

    # AI 总结
    summary_version = None
    if not args.no_ai and config.get("api_key"):
        print("· AI 总结...")
        supplements_text = load_supplements(supplements_dir)
        summary = ai_summarize(transcript, supplements_text, config, comments_text=comments_text, video_info=video_info)
        if summary:
            summary = summary.replace("（由调用方填入）", clean_url)
            summary_version = get_next_version(output_dir)
            summary_path = os.path.join(output_dir, f"{summary_version}.md")
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\n{summary}\n")
            print("  完成")
        else:
            print("  失败")
    elif not args.no_ai and not config.get("api_key"):
        print("· 未配置 AI 模型，无法生成总结。")
        print("")
        try:
            choice = input("是否配置 AI 模型进行内容总结？(y/n) [默认 y]：").strip().lower()
        except (EOFError, KeyboardInterrupt):
            choice = "n"

        if choice in ("", "y", "yes"):
            print("")
            print("请填写 AI 模型信息（用于将视频内容总结为结构化文档）：")
            print("")
            print("  api_base: AI 服务的接口地址")
            print("    豆包（火山方舟）: https://ark.cn-beijing.volces.com/api/v3")
            print("    OpenAI:          https://api.openai.com/v1")
            print("    DeepSeek:        https://api.deepseek.com/v1")
            print("")

            try:
                api_base = input("  api_base: ").strip()
                api_key = input("  api_key:  ").strip()
                model = input("  model（模型名称，如 doubao-seed-2-0-mini-260215）: ").strip()
            except (EOFError, KeyboardInterrupt):
                api_base = ""

            if api_base and api_key and model:
                config["api_base"] = api_base
                config["api_key"] = api_key
                config["model"] = model

                # 保存到 config.json
                config_path = os.path.join(SCRIPT_DIR, "..", "config.json")
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                print(f"\n  已保存配置，下次无需重复填写。")
                print("")

                # 执行 AI 总结
                print("· AI 总结...")
                supplements_text = load_supplements(supplements_dir)
                summary = ai_summarize(transcript, supplements_text, config, comments_text=comments_text, video_info=video_info)
                if summary:
                    summary = summary.replace("（由调用方填入）", clean_url)
                    summary_version = get_next_version(output_dir)
                    summary_path = os.path.join(output_dir, f"{summary_version}.md")
                    with open(summary_path, "w", encoding="utf-8") as f:
                        f.write(f"# {title}\n\n{summary}\n")
                    print("  完成")
                else:
                    print("  失败")
            else:
                print("\n  配置不完整，跳过 AI 总结。")
        else:
            print("· 跳过 AI 总结")

    # 输出结果
    raw_contents = []
    if os.path.exists(transcript_path):
        raw_contents.append("字幕")
    if os.path.exists(audio_path):
        raw_contents.append("音频")
    if os.path.exists(video_path):
        raw_contents.append("视频")
    if os.path.exists(comments_txt_path):
        raw_contents.append("评论")

    output_file = f"{summary_version}.md" if summary_version else "（未生成）"

    print("")
    print("── 输出结果 ──────────────────")
    print(f"  {project_dir}/")
    print(f"  ├── raw/          {' · '.join(raw_contents)}")
    print(f"  ├── supplements/  补充信息（可编辑）")
    print(f"  └── output/       {output_file}")
    print("")

    if summary_version and not args.no_ai:
        next_ver = get_next_version(output_dir)
        print(f"编辑 supplements/ 后重新执行，将生成 {next_ver}.md。")


if __name__ == "__main__":
    main()
