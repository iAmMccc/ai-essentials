#!/bin/bash

# 抖音视频转文档 - 入口脚本
# 用法:
#   ./run.sh login              首次扫码登录
#   ./run.sh "抖音链接"          提取内容并生成文档
#   ./run.sh "抖音链接" --no-ai  只提取，不做 AI 总结

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 检测可用的 Python（playwright 不支持 3.14+）
find_python() {
  for cmd in python3.12 python3.13 python3.11 python3.10 python3; do
    if command -v "$cmd" &>/dev/null; then
      # 检查版本号，跳过 3.14+
      version=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
      major=$(echo "$version" | cut -d. -f1)
      minor=$(echo "$version" | cut -d. -f2)
      if [ "$major" = "3" ] && [ "$minor" -ge 10 ] && [ "$minor" -le 13 ]; then
        echo "$cmd"
        return 0
      fi
    fi
  done
  return 1
}

PYTHON=$(find_python)
if [ -z "$PYTHON" ]; then
  echo "错误: 未找到兼容的 Python（需要 3.10 ~ 3.13）"
  echo ""
  echo "安装方式:"
  echo "  brew install python@3.12"
  exit 1
fi

PYTHON_VERSION=$("$PYTHON" --version 2>&1)

# 检测依赖
check_deps() {
  local missing=()

  # ffmpeg
  if ! command -v ffmpeg &>/dev/null; then
    missing+=("ffmpeg (brew install ffmpeg)")
  fi

  # playwright
  if ! "$PYTHON" -c "import playwright" &>/dev/null; then
    missing+=("playwright ($PYTHON -m pip install playwright && $PYTHON -m playwright install chromium)")
  fi

  # whisper（可选但推荐）
  if ! "$PYTHON" -c "import whisper" &>/dev/null; then
    missing+=("openai-whisper ($PYTHON -m pip install openai-whisper)")
  fi

  if [ ${#missing[@]} -gt 0 ]; then
    echo "缺少依赖:"
    for dep in "${missing[@]}"; do
      echo "  - $dep"
    done
    echo ""
    echo "安装完依赖后重新执行。"
    exit 1
  fi
}

# 无参数时显示帮助
if [ -z "$1" ]; then
  echo "抖音视频转文档"
  echo ""
  echo "使用 $PYTHON_VERSION"
  echo ""
  echo "用法:"
  echo "  $0 login              首次扫码登录抖音"
  echo "  $0 \"抖音链接\"          提取内容并生成文档"
  echo "  $0 \"抖音链接\" --no-ai  只提取原始内容，不做 AI 总结"
  echo ""
  echo "示例:"
  echo "  $0 login"
  echo "  $0 \"https://www.douyin.com/video/xxx\""
  exit 0
fi

# 登录
if [ "$1" = "login" ]; then
  check_deps
  echo "使用 $PYTHON_VERSION"
  "$PYTHON" "$SCRIPT_DIR/scripts/douyin-login.py"
  exit $?
fi

# 提取内容
check_deps
echo "使用 $PYTHON_VERSION"
"$PYTHON" "$SCRIPT_DIR/scripts/douyin-to-doc.py" "$@"
