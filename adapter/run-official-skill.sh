#!/usr/bin/env bash
# adapter/run-official-skill.sh — 用「壳」跑官方 skill，官方文件一个字节都不动
# 学官方做法：workspace/tools/run-official-skill.sh（环境差异放外部适配层）
# 用法: adapter/run-official-skill.sh <skill名> --args ...
set -euo pipefail

SKILL="${1:-}"; shift || true
if [ -z "$SKILL" ]; then
  echo "用法: run-official-skill.sh <skill名> [-- 参数...]" >&2
  echo "已冻结的官方 skill:" >&2
  ls -1 "$(cd "$(dirname "$0")/.." && pwd)/vendor/nvidia-skills" >&2
  exit 2
fi

REPO="$(cd "$(dirname "$0")/.." && pwd)"
DIR="$REPO/vendor/nvidia-skills/$SKILL"

if [ ! -f "$DIR/SKILL.md" ]; then
  echo "❌ vendor 里没有这个官方 skill: $SKILL" >&2
  echo "   本脚本只跑冻结过的官方 skill；要新增请先走 scripts/sync.mjs 并更新 LOCK.json。" >&2
  exit 3
fi

# 冻结完整性：跑之前先验一次签名文件在不在（内容比对交给 verify-lock.mjs / pre-push-check.mjs）
if [ ! -f "$DIR/skill.oms.sig" ]; then
  echo "❌ $SKILL 缺 skill.oms.sig —— 治理产物不齐，官方流水线会拒收，我们也一样。" >&2
  exit 4
fi

# 环境差异只在这里注入
# shellcheck disable=SC1091
source "$REPO/adapter/env.sh"

# 端点选择：默认本地 vLLM；VLM_BACKEND=stepfun 时切到云端（只改三个值）
if [ "${VLM_BACKEND:-local}" = "stepfun" ]; then
  export VLM_BASE_URL="https://api.stepfun.com/step_plan/v1"
  export VLM_MODEL="${VLM_MODEL:-step-5-preview}"
  export VLM_API_KEY="${STEPFUN_API_KEY:?STEPFUN_API_KEY 未注入（由甲方环境变量注入，勿落盘）}"
else
  export VLM_BASE_URL="$LOCAL_VLM_BASE_URL"
  export VLM_MODEL="$LOCAL_VLM_MODEL"
  export VLM_API_KEY="$LOCAL_VLM_API_KEY"
fi

echo "▶ 跑官方 skill: $SKILL"
echo "  端点: $VLM_BASE_URL"
echo "  模型: $VLM_MODEL"
echo "  官方目录（只读）: $DIR"

# 优先用官方自带的入口脚本；没有就给出手工调用指引（不猜路径）
if [ -x "$DIR/scripts/run.sh" ]; then
  exec "$DIR/scripts/run.sh" "$@"
elif [ -f "$DIR/scripts/run.py" ]; then
  exec python3 "$DIR/scripts/run.py" "$@"
else
  echo "ℹ️ 该官方 skill 没有单一入口脚本，按其 SKILL.md 的步骤执行；本壳已把端点与模型注入为环境变量。" >&2
  echo "   SKILL.md: $DIR/SKILL.md" >&2
  exit 0
fi
