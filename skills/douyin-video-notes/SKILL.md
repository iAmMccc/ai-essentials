---
name: douyin-video-notes
description: |
  抖音视频智能总结。输入抖音链接，自动提取语音内容，通过 AI 生成结构化笔记。
---

# 抖音视频智能总结

输入抖音视频链接，自动下载视频、提取音频、语音转文字、获取评论，通过 AI 生成结构化笔记。

## 使用

```bash
./run.sh "抖音视频链接"
```

首次使用会自动提示扫码登录，无需单独操作。脚本会自动检测 Python 版本和依赖，缺少时提示安装。

### 参数

```bash
./run.sh "链接" --no-ai          # 跳过 AI 总结，只提取原始内容
./run.sh "链接" --api-base URL --api-key KEY --model NAME   # 指定模型
```

## 输出结构

```
output/视频标题/
├── raw/            视频 · 音频 · 字幕 · 评论
├── supplements/    补充信息（可手动编辑）
└── output/         v1.md（AI 总结，重复执行生成新版本）
```

## 依赖

| 工具 | 用途 | 安装 |
|------|------|------|
| playwright | 页面解析 + 登录 | `pip install playwright && python -m playwright install chromium` |
| ffmpeg | 音频提取 | `brew install ffmpeg` |
| openai-whisper | 语音转文字 | `pip install openai-whisper` |

> 依赖安装需要网络，国内用户可使用 pip 镜像源：`pip install -i https://pypi.tuna.tsinghua.edu.cn/simple`

## AI 总结配置

首次未配置时脚本会交互引导填写，也可以手动编辑 `config.json`：

| 服务 | api_base | model |
|------|----------|-------|
| 豆包（火山方舟） | `https://ark.cn-beijing.volces.com/api/v3` | `doubao-seed-2-0-mini-260215` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |

## 安装

```bash
curl -sL https://raw.githubusercontent.com/iAmMccc/ai-essentials/main/install-skill.sh | bash -s douyin-video-notes
```

或直接将 `douyin-video-notes` 文件夹复制到本地使用，后续操作不依赖 GitHub。

## 免责声明

本工具仅供个人学习和研究使用，使用时请注意：

- **遵守平台规则**：使用本工具即表示你同意遵守抖音的用户协议和相关规定
- **尊重版权**：视频内容的著作权归原创作者所有，生成的笔记仅供个人学习参考，不得用于商业用途或公开传播
- **个人责任**：用户应对使用本工具的行为及其产生的后果自行承担责任
- **禁止商业用途**：禁止将本工具或其产出内容用于任何商业目的

本工具不存储、不转发、不分发任何视频内容，所有操作均在用户本地完成。
