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
  # 都没有，默认创建 .claude/skills
  TARGET_DIR=".claude/skills"
fi

SKILL_DIR="${TARGET_DIR}/${SKILL_NAME}"

# 下载 Skill 文件
SKILL_URL="${BASE_URL}/skills/${SKILL_NAME}/SKILL.md"

echo "正在安装 ${SKILL_NAME}..."

# 检查 Skill 是否存在
HTTP_CODE=$(curl -sL -o /dev/null -w "%{http_code}" "$SKILL_URL")
if [ "$HTTP_CODE" != "200" ]; then
  echo "错误: Skill '${SKILL_NAME}' 不存在"
  echo "请检查 https://github.com/${REPO}/tree/${BRANCH}/skills/ 查看可用的 Skills"
  exit 1
fi

# 创建目录并下载
mkdir -p "$SKILL_DIR"
curl -sL "$SKILL_URL" -o "${SKILL_DIR}/SKILL.md"

if [ $? -eq 0 ]; then
  echo "已安装到 ${SKILL_DIR}/SKILL.md"
else
  echo "安装失败，请检查网络连接"
  exit 1
fi
