---
name: douyin-video-notes
description: |
  抖音视频智能总结。输入抖音链接，自动提取语音内容，通过 AI 生成结构化笔记。
---

# 抖音视频智能总结

输入抖音视频链接，自动下载视频、提取音频、转为文字、获取评论，通过 AI 生成结构化笔记。

## 一、使用手册

### 1. 安装

在你想要存放输出文件的目录下执行：

```bash
cd ~/Desktop/your-workspace    # 切换到你的工作目录
curl -sL https://raw.githubusercontent.com/iAmMccc/ai-essentials/main/install-skill.sh | bash -s douyin-video-notes
```

> 国内网络无法访问 GitHub？通过其他方式获取 `douyin-video-notes` 文件夹，复制到本地即可。安装后的所有操作不依赖 GitHub。

执行时脚本会自动检测依赖，缺少时会提示安装命令。以下是依赖列表，供参考：

| 工具 | 用途 | 安装 |
|------|------|------|
| Python 3.10~3.13 | 运行环境 | `brew install python@3.12` |
| playwright | 页面解析 + 登录 | `pip install playwright && python -m playwright install chromium` |
| ffmpeg | 音频提取 | `brew install ffmpeg` |
| openai-whisper | 转为文字 | `pip install openai-whisper` |

> 国内用户可使用 pip 镜像源加速：`pip install -i https://pypi.tuna.tsinghua.edu.cn/simple`

### 2. 配置 AI（可选）

脚本会自动提取视频的字幕、音频转文字和评论。如果你还希望 AI 帮你整理成结构化笔记，需要配置一个 AI 模型。

首次执行时脚本会交互引导填写，你需要提供三个信息：
- `api_base`：AI 服务的接口地址
- `api_key`：你的 API 密钥
- `model`：模型名称

也可以直接编辑配置文件：

```bash
open douyin-video-notes/config.json
```

不配置则跳过 AI 总结，只保留原始内容。

### 3. 执行

```bash
./douyin-video-notes/run.sh "抖音视频链接"
```

脚本会自动检测环境、提示登录、下载视频、转为文字、获取评论、AI 总结，全程无需额外操作。

### 4. 补充信息（可选）

如果你有视频中未体现的额外信息，可以手动补充后重新执行，AI 会将补充内容纳入总结并生成新版本（v2、v3...）。

补充方式：
- **文字信息**（GitHub 地址、工具名称、关键数据等）：编辑 `output/视频标题/supplements/extra.md`
- **图片、截图、文档等文件**：直接放入 `output/视频标题/supplements/` 目录

然后重新执行：

```bash
./douyin-video-notes/run.sh "同一个抖音链接"
```

## 二、输出结构

```
output/视频标题/
├── raw/            视频 · 音频 · 字幕 · 评论
├── supplements/    补充信息（extra.md + 截图等文件）
└── output/         v1.md（重复执行生成新版本）
```

## 三、免责声明

本工具仅供个人学习和研究使用，使用时请注意：

- **遵守平台规则**：使用本工具即表示你同意遵守抖音的用户协议和相关规定
- **尊重版权**：视频内容的著作权归原创作者所有，生成的笔记仅供个人学习参考，不得用于商业用途或公开传播
- **个人责任**：用户应对使用本工具的行为及其产生的后果自行承担责任
- **禁止商业用途**：禁止将本工具或其产出内容用于任何商业目的

本工具不存储、不转发、不分发任何视频内容，所有操作均在用户本地完成。
