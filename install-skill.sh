#!/bin/bash

# AI Essentials - Skill 安装脚本
# 用法: curl -sL https://raw.githubusercontent.com/iAmMccc/ai-essentials/main/install-skill.sh | bash -s <skill-name>
# 示例: curl -sL https://raw.githubusercontent.com/iAmMccc/ai-essentials/main/install-skill.sh | bash -s git-commit

REPO="iAmMccc/ai-essentials"
BRANCH="main"
BASE_URL="https://raw.githubusercontent.com/${REPO}/${BRANCH}"

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
SKILL_BASE="${BASE_URL}/skills/${SKILL_NAME}"

echo "正在安装 ${SKILL_NAME}..."

# 检查 Skill 是否存在
HTTP_CODE=$(curl -sL -o /dev/null -w "%{http_code}" "${SKILL_BASE}/SKILL.md")
if [ "$HTTP_CODE" != "200" ]; then
  echo "错误: Skill '${SKILL_NAME}' 不存在"
  echo "请检查 https://github.com/${REPO}/tree/${BRANCH}/skills/ 查看可用的 Skills"
  exit 1
fi

# 每个 Skill 的文件清单（相对于 Skill 根目录）
# 新增 Skill 时在这里添加对应的文件列表
case "$SKILL_NAME" in
  git-commit)
    FILES="SKILL.md"
    ;;
  spm-local)
    FILES="SKILL.md packages.json.example scripts/fetch-packages.sh"
    ;;
  *)
    # 未知 Skill，只下载 SKILL.md
    FILES="SKILL.md"
    ;;
esac

# 逐个下载文件
fail=0
for file in $FILES; do
  dir=$(dirname "$file")
  if [ "$dir" != "." ]; then
    mkdir -p "${SKILL_DIR}/${dir}"
  else
    mkdir -p "${SKILL_DIR}"
  fi

  curl -sL "${SKILL_BASE}/${file}" -o "${SKILL_DIR}/${file}"
  if [ $? -ne 0 ]; then
    echo "  下载失败: ${file}"
    fail=1
  else
    # .sh 文件加可执行权限
    if [[ "$file" == *.sh ]]; then
      chmod +x "${SKILL_DIR}/${file}"
    fi
  fi
done

# 验证
if [ "$fail" -eq 0 ] && [ -f "${SKILL_DIR}/SKILL.md" ]; then
  file_count=$(echo "$FILES" | wc -w | tr -d ' ')
  echo "已安装到 ${SKILL_DIR}/（${file_count} 个文件）"
else
  echo "安装失败，请检查网络连接"
  rm -rf "$SKILL_DIR"
  exit 1
fi
