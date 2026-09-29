#!/usr/bin/env bash
# adapter/env.sh — 唯一的「环境差异层」
# 纪律（官方原话）：改了官方 Skill，签名就不再成立 → 环境差异一律放这里，绝不写回 vendor/
# 用法： source adapter/env.sh

# ── GB10 必踩坑（DGX Spark 实测，不加会报 CUDA_ERROR_INVALID_IMAGE）
export VLLM_USE_DEEP_GEMM=0
export VLLM_MOE_BACKEND="${VLLM_MOE_BACKEND:-triton}"

# ── 本地推理端点（vLLM，OpenAI 兼容）。端口不写进公开材料，用环境变量注入。
export LOCAL_VLM_BASE_URL="${LOCAL_VLM_BASE_URL:-http://127.0.0.1:8000/v1}"
export LOCAL_VLM_MODEL="${LOCAL_VLM_MODEL:-Qwen3.6-35B-A3B-FP8}"
export LOCAL_VLM_API_KEY="${LOCAL_VLM_API_KEY:-EMPTY}"   # 本地 vLLM 通常不校验

# ── 知识库（自研检索，非官方）
export KB_PATH="${KB_PATH:-}"
export KB_COLLECTION="${KB_COLLECTION:-moon_rabbits_kb}"

# ── 自检：缺 key 时明确报错，而不是跑出一堆噪声
if [ "${VLM_BACKEND:-openai}" = "stepfun" ] && [ -z "${STEPFUN_API_KEY:-}" ]; then
  echo "⚠️ VLM_BACKEND=stepfun 但 STEPFUN_API_KEY 未注入。请由甲方用环境变量注入，不要写进任何文件。" >&2
fi

echo "adapter/env.sh 已加载：VLLM_USE_DEEP_GEMM=$VLLM_USE_DEEP_GEMM · MOE_BACKEND=$VLLM_MOE_BACKEND · 本地端点=$LOCAL_VLM_BASE_URL"
