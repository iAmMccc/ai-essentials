# 抖音视频智能总结

输入抖音视频链接，自动生成结构化学习笔记。

## 快速开始

**安装**

```bash
curl -sL https://raw.githubusercontent.com/iAmMccc/ai-essentials/main/install-skill.sh | bash -s douyin-video-notes
```

> 国内无法访问 GitHub？直接将 `douyin-video-notes` 文件夹复制到本地即可。

**运行**

```bash
./douyin-video-notes/run.sh "抖音链接"
```

支持所有链接格式：标准链接、短链接、搜索页链接、直接粘贴分享文本都行。

首次运行会自动创建 Python 环境并安装依赖（需要已安装 `python3.12` 和 `ffmpeg`，没有的话执行 `brew install python@3.12 ffmpeg`）。

## 运行过程

脚本会按以下顺序执行，每一步都有提示，可随时跳过：

```
自动获取视频信息（标题、作者、点赞数等）
    ↓
自动下载视频 → 提取音频 → 语音转文字
    ↓
询问：是否登录抖音获取评论？（可跳过）
    ↓
询问：是否配置 AI 生成总结？（可跳过，填错可重试）
    ↓
生成结果
```

## 输出

```
output/视频标题/
├── raw/            视频 · 音频 · 字幕 · 评论
├── supplements/    补充信息（可手动添加）
└── output/         v1.md（AI 总结的笔记）
```

- 重复执行同一个链接，会自动生成新版本（v2、v3...），不覆盖旧版
- 在 `supplements/extra.md` 中添加额外信息（截图描述、相关链接等），重新执行会纳入总结

## 前置条件

只需两个系统级工具，其余由脚本自动安装：

```bash
brew install python@3.12 ffmpeg
```

> 国内 pip 安装慢？脚本使用独立虚拟环境，不影响系统。如果安装超时，可设置镜像源：`pip install -i https://pypi.tuna.tsinghua.edu.cn/simple`

## 免责声明

本工具仅供个人学习使用。视频内容版权归原创作者所有，生成的笔记不得用于商业用途或公开传播。使用即表示同意遵守抖音用户协议。所有操作在本地完成，不存储、不转发任何视频内容。
