#!/bin/bash

# AI Essentials - Skill 安装脚本
# 用法: curl -sL https://raw.githubusercontent.com/iAmMccc/ai-essentials/main/install-skill.sh | bash -s <skill-name>
# 示例: curl -sL https://raw.githubusercontent.com/iAmMccc/ai-essentials/main/install-skill.sh | bash -s git-commit

REPO="iAmMccc/ai-essentials"
BRANCH="main"
BASE_URL="https://raw.githubusercontent.com/${REPO}/${BRANCH}"
API_URL="https://api.github.com/repos/${REPO}/contents/skills"

SKILL_NAME="$1"

if [ -z "$SKILL_NAME" ]; then
  echo "用法: bash install-skill.sh <skill-name>"
  echo ""
  echo "可用的 Skills:"
  echo "  git-commit    自动分析 git diff，生成规范的中文 commit message"
  echo "  spm-local     SPM 本地依赖管理，绕过 Xcode 网络限制"
  echo ""
  echo "示例:"
  echo "  curl -sL ${BASE_URL}/install-skill.sh | bash -s git-commit"
  exit 1
fi

# 检测 AI 工具目录
TARGET_DIR=""
if [ -d ".claude" ]; then
  TARGET_DIR=".claude/skills"
elif [ -d ".cursor" ]; then
  TARGET_DIR=".cursor/skills"
else
  TARGET_DIR=".claude/skills"
fi

SKILL_DIR="${TARGET_DIR}/${SKILL_NAME}"

echo "正在安装 ${SKILL_NAME}..."

# 检查 Skill 是否存在（通过 SKILL.md 判断）
SKILL_URL="${BASE_URL}/skills/${SKILL_NAME}/SKILL.md"
HTTP_CODE=$(curl -sL -o /dev/null -w "%{http_code}" "$SKILL_URL")
if [ "$HTTP_CODE" != "200" ]; then
  echo "错误: Skill '${SKILL_NAME}' 不存在"
  echo "请检查 https://github.com/${REPO}/tree/${BRANCH}/skills/ 查看可用的 Skills"
  exit 1
fi

# 通过 GitHub API 获取 Skill 目录下的所有文件
download_dir() {
  local api_path="$1"
  local local_path="$2"

  mkdir -p "$local_path"

  # 获取目录内容列表
  local content
  content=$(curl -sL "${API_URL}/${SKILL_NAME}${api_path:+/$api_path}")

  # 解析 JSON（用 python3，macOS 自带）
  echo "$content" | python3 -c "
import json, sys
items = json.load(sys.stdin)
if not isinstance(items, list):
    sys.exit(0)
for item in items:
    print(item['type'] + '\t' + item['name'] + '\t' + item.get('download_url', ''))
" 2>/dev/null | while IFS=$'\t' read -r type name download_url; do
    if [ "$type" = "file" ] && [ -n "$download_url" ]; then
      curl -sL "$download_url" -o "${local_path}/${name}"
      # 保持脚本的可执行权限
      if [[ "$name" == *.sh ]]; then
        chmod +x "${local_path}/${name}"
      fi
    elif [ "$type" = "dir" ]; then
      download_dir "${api_path:+$api_path/}${name}" "${local_path}/${name}"
    fi
  done
}

# 下载整个 Skill 文件夹
download_dir "" "$SKILL_DIR"

# 验证安装结果
if [ -f "${SKILL_DIR}/SKILL.md" ]; then
  file_count=$(find "$SKILL_DIR" -type f | wc -l | tr -d ' ')
  echo "已安装到 ${SKILL_DIR}/（${file_count} 个文件）"
else
  echo "安装失败，请检查网络连接"
  rm -rf "$SKILL_DIR"
  exit 1
fi
