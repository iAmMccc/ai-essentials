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

# Skill 安装后的初始化（按需）
case "$SKILL_NAME" in
  spm-local)
    if [ ! -d "Packages" ]; then
      mkdir -p Packages/Caches Packages/scripts
      cp "${SKILL_DIR}/packages.json.example" Packages/packages.json
      cp "${SKILL_DIR}/scripts/fetch-packages.sh" Packages/scripts/fetch-packages.sh
      chmod +x Packages/scripts/fetch-packages.sh

      # 将 Caches 加入 .gitignore
      if [ -f ".gitignore" ]; then
        if ! grep -q "Packages/Caches" .gitignore 2>/dev/null; then
          echo "" >> .gitignore
          echo "# SPM 本地缓存（三方库源码不提交）" >> .gitignore
          echo "Packages/Caches/" >> .gitignore
        fi
      else
        echo "# SPM 本地缓存（三方库源码不提交）" > .gitignore
        echo "Packages/Caches/" >> .gitignore
      fi

      echo ""
      echo "已初始化 Packages/ 目录："
      echo "  Packages/packages.json              ← 在这里配置依赖"
      echo "  Packages/scripts/fetch-packages.sh  ← 执行下载"
      echo "  Packages/Caches/                    ← 三方库下载目录"
      echo ""
      echo "说明："
      echo "  通过终端将 SPM 三方库下载到本地，在 Xcode 中以 Add Local 方式引入。"
      echo "  Packages/Caches/ 已自动添加到 .gitignore，三方库源码不会被提交。"
      echo ""
      echo "下一步："
      echo "  1. 编辑 Packages/packages.json，添加你的依赖"
      echo "  2. 执行 ./Packages/scripts/fetch-packages.sh"
      echo "  3. 在 Xcode 中 Add Local 添加 Packages/Caches/ 下的库"
    else
      echo ""
      echo "Packages/ 目录已存在，跳过初始化。"
    fi
    ;;
esac
