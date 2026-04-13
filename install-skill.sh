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
  echo "  git-commit      自动分析 git diff，生成规范的中文 commit message"
  echo "  spm-local       SPM 本地依赖管理，绕过 Xcode 网络限制"
  echo "  smart-notes     智能笔记生成器，支持抖音/微信公众号"
  echo "  ui-diff         对比 UI 设计稿与 App 截图，检查间距/对齐/样式差异"
  echo ""
  echo "示例:"
  echo "  curl -sL ${BASE_URL}/install-skill.sh | bash -s git-commit"
  exit 1
fi

SKILL_BASE="${BASE_URL}/skills/${SKILL_NAME}"

echo "正在安装 ${SKILL_NAME}..."

# 读取 install.conf 确定安装类型
INSTALL_TYPE=$(curl -sL "${SKILL_BASE}/install.conf" | grep "^type=" | cut -d= -f2 | tr -d '[:space:]')

if [ -z "$INSTALL_TYPE" ]; then
  echo "错误: Skill '${SKILL_NAME}' 不存在或缺少 install.conf"
  echo "请检查 https://github.com/${REPO}/tree/${BRANCH}/skills/"
  exit 1
fi

# 检查两个目录是否指向同一位置（软链接或相同真实路径）
same_skills_dir() {
  local dir1="$1" dir2="$2"
  # 目录不存在则不同
  [ -d "$dir1" ] && [ -d "$dir2" ] || return 1
  # 比较真实路径
  local real1 real2
  real1=$(cd "$dir1" 2>/dev/null && pwd -P)
  real2=$(cd "$dir2" 2>/dev/null && pwd -P)
  [ "$real1" = "$real2" ]
}

# 根据 type 决定安装目录列表
SKILL_DIRS=""
case "$INSTALL_TYPE" in
  ai-tool)
    has_claude=false
    has_cursor=false
    [ -d ".claude" ] && has_claude=true
    [ -d ".cursor" ] && has_cursor=true

    if $has_claude && $has_cursor; then
      # 两个都有，检查 skills 目录是否指向同一位置
      mkdir -p .claude/skills .cursor/skills 2>/dev/null
      if same_skills_dir ".claude/skills" ".cursor/skills"; then
        echo "检测到 .cursor/skills 与 .claude/skills 指向同一目录，只安装一份"
        SKILL_DIRS=".claude/skills/${SKILL_NAME}"
      else
        SKILL_DIRS=".claude/skills/${SKILL_NAME} .cursor/skills/${SKILL_NAME}"
      fi
    elif $has_claude; then
      SKILL_DIRS=".claude/skills/${SKILL_NAME}"
    elif $has_cursor; then
      SKILL_DIRS=".cursor/skills/${SKILL_NAME}"
    else
      # 都没有，两个都装，兼容 Claude Code 和 Cursor
      SKILL_DIRS=".claude/skills/${SKILL_NAME} .cursor/skills/${SKILL_NAME}"
    fi
    ;;
  root-md)
    # 直接在根目录放 CLAUDE.md 和 AGENTS.md，兼容所有 AI 工具
    ROOT_MD_MODE=true
    ;;
  standalone)
    SKILL_DIRS="${SKILL_NAME}"
    ;;
  *)
    echo "错误: 未知的安装类型 '${INSTALL_TYPE}'"
    exit 1
    ;;
esac

# 获取文件清单（从 SKILL.md 是否存在来验证）
HTTP_CODE=$(curl -sL -o /dev/null -w "%{http_code}" "${SKILL_BASE}/SKILL.md")
if [ "$HTTP_CODE" != "200" ]; then
  echo "错误: Skill '${SKILL_NAME}' 不存在"
  exit 1
fi

# root-md 模式：下载 SKILL.md 内容，写入 CLAUDE.md 和 AGENTS.md
if [ "${ROOT_MD_MODE}" = true ]; then
  fail=0
  curl -sL "${SKILL_BASE}/SKILL.md" -o "AGENTS.md"
  if [ $? -ne 0 ]; then
    echo "  下载失败: AGENTS.md"
    fail=1
  fi
  echo "请遵循 AGENTS.md 中的所有规则。" > "CLAUDE.md"

  if [ "$fail" -eq 0 ] && [ -f "AGENTS.md" ]; then
    echo "已安装到当前目录："
    echo "  CLAUDE.md   ← Claude Code 自动读取"
    echo "  AGENTS.md   ← Cursor 自动读取"
    mkdir -p images
    echo ""
    echo "下一步："
    echo "  1. 在 images/ 下按页面建子文件夹，每个放 2 张图（设计稿 + 截图）"
    echo "  2. 打开 Claude Code 或 Cursor，执行 /ui-diff images"
  else
    echo "安装失败，请检查网络连接"
    rm -f "CLAUDE.md" "AGENTS.md"
    exit 1
  fi
  exit 0
fi

# 每个 Skill 的文件清单
case "$SKILL_NAME" in
  git-commit)
    FILES="SKILL.md"
    ;;
  spm-local)
    FILES="SKILL.md packages.json.example scripts/fetch-packages.sh"
    ;;
  smart-notes)
    FILES="SKILL.md README.md config.json.example install.conf run.sh scripts/main.py scripts/summarizer.py scripts/output.py scripts/douyin-login.py scripts/platforms/__init__.py scripts/platforms/douyin.py scripts/platforms/wechat.py"
    ;;
  *)
    FILES="SKILL.md"
    ;;
esac

# 下载文件到所有目标目录
fail=0
for SKILL_DIR in $SKILL_DIRS; do
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
      if [[ "$file" == *.sh ]]; then
        chmod +x "${SKILL_DIR}/${file}"
      fi
    fi
  done
done

# 验证
if [ "$fail" -eq 0 ]; then
  file_count=$(echo "$FILES" | wc -w | tr -d ' ')
  for SKILL_DIR in $SKILL_DIRS; do
    if [ -f "${SKILL_DIR}/SKILL.md" ]; then
      echo "已安装到 ${SKILL_DIR}/（${file_count} 个文件）"
    fi
  done
else
  echo "安装失败，请检查网络连接"
  for SKILL_DIR in $SKILL_DIRS; do
    rm -rf "$SKILL_DIR"
  done
  exit 1
fi

# 安装后初始化
case "$SKILL_NAME" in
  spm-local)
    if [ ! -d "Packages" ]; then
      mkdir -p Packages/Caches Packages/scripts
      cp "${SKILL_DIR}/packages.json.example" Packages/packages.json
      cp "${SKILL_DIR}/scripts/fetch-packages.sh" Packages/scripts/fetch-packages.sh
      chmod +x Packages/scripts/fetch-packages.sh

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
