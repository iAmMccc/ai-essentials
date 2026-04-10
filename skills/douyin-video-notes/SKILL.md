---
name: douyin-to-doc
description: |
  当用户要求提取抖音视频内容、获取视频字幕、总结视频内容时使用。
  输入一个抖音链接，自动提取文字内容并生成 Markdown 文档。
---

# 抖音视频转文档

输入抖音视频链接，自动提取视频中的文字内容，并通过 AI 总结生成 Markdown 文档。

## 工作流程

```
首次使用：运行登录脚本 → 扫码 → Cookie 保存到本地
    ↓
日常使用：输入抖音 URL → 自动提取字幕/音频转文字 → AI 总结 → 输出 Markdown
    ↓
Cookie 过期：脚本提示重新登录
```

## 依赖

| 工具 | 用途 | 安装 |
|------|------|------|
| playwright | 浏览器登录 + 页面解析 | `pip install playwright && python -m playwright install chromium` |
| ffmpeg | 音频提取 | `brew install ffmpeg` |
| openai-whisper | 语音转文字 | `pip install openai-whisper` |

## 使用

### 第一步：登录抖音（首次使用）

```bash
python3 scripts/douyin-login.py
```

脚本会打开浏览器，在抖音页面扫码登录。登录成功后 Cookie 自动保存到 `scripts/cookies.txt`，后续使用无需重复登录。

### 第二步：提取视频内容

```bash
python3 scripts/douyin-to-doc.py "抖音视频链接"
```

脚本会：
1. 用 Playwright 加载页面，提取视频标题和视频地址
2. 下载视频并提取音频
3. Whisper 语音转文字
4. AI 总结生成 Markdown

### 命令行参数

```bash
# 跳过 AI 总结，只输出原始文字
python3 scripts/douyin-to-doc.py "链接" --no-ai

# 指定模型（覆盖 config.json）
python3 scripts/douyin-to-doc.py "链接" --api-base https://api.openai.com/v1 --api-key sk-xxx --model gpt-4o-mini
```

## AI 总结配置

编辑 `config.json` 配置模型信息：

```json
{
  "api_base": "https://ark.cn-beijing.volces.com/api/v3",
  "api_key": "你的 API Key",
  "model": "doubao-1-5-lite-32k"
}
```

| 服务 | api_base | model |
|------|----------|-------|
| 豆包（火山方舟） | `https://ark.cn-beijing.volces.com/api/v3` | `doubao-1-5-lite-32k`（免费） |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |

不配置时脚本会跳过 AI 总结，只输出原始文字。

## 安装

```bash
curl -sL https://raw.githubusercontent.com/iAmMccc/ai-essentials/main/install-skill.sh | bash -s douyin-to-doc
```

## 注意事项

- `cookies.txt` 和 `cookies.json` 包含登录信息，已自动添加到 `.gitignore`，不要手动提交
- Cookie 有效期有限，过期后脚本会提示重新登录

## 免责声明

本工具仅供个人学习和研究使用，使用时请注意：

- **遵守平台规则**：使用本工具即表示你同意遵守抖音的用户协议和相关规定
- **尊重版权**：视频内容的著作权归原创作者所有，生成的笔记仅供个人学习参考，不得用于商业用途或公开传播
- **个人责任**：用户应对使用本工具的行为及其产生的后果自行承担责任
- **禁止商业用途**：禁止将本工具或其产出内容用于任何商业目的

本工具不存储、不转发、不分发任何视频内容，所有操作均在用户本地完成。
