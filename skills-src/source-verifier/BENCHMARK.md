# BENCHMARK.md · source-verifier

> **治理五道工序之 Evaluated 产物**：Cataloged → Scanned → **Evaluated** → Signed → Documented
> 🔴 **只写真数，没跑的一律标"未跑"，禁止估计值。**

---

## 一、方法论（照 NVIDIA 官方 Tier-3 定义）

> 官方原文（`NVIDIA Skills 开发实战` p6）：
> 「方法：同一个 Agent，同一任务集，跑两遍 —— **带 skill 与不带 skill，差值即 skill 的实测贡献**」
> 「PASS 标准：**至少一个受支持 Agent 在全部配置维度上通过**」
> 「任务集随 skill 提交（`evals/evals.json`），且**必须包含负向用例**（正确答案是『不调用该 skill』的场景）」

**本 skill 的执行方式**：

| 项 | 值 |
|---|---|
| 被测 skill | `source-verifier` |
| skill 版本 | `0.2.0` |
| 任务集 | `evals/evals.json`（13 条；本轮实测 3 条 × 两个端点，其余标未跑） |
| 执行 Agent | DeepSeek Harness + `tier3-eval.mjs`（OpenAI-compatible 客户端，同任务集跑 baseline / with skill 两遍，每用例 ×3） |
| 模型 | 本地 Qwen3.6-35B-A3B-FP8（vLLM 0.28.0，DGX Spark）；云端 StepFun Step 5 Preview（同 3 条再跑一遍） |
| 硬件 | NVIDIA DGX Spark（GB10 · 121 GiB 统一内存 · CUDA 13.0） |
| 评测日期 | 2026-09-29 |
| 执行人 | zephyr 队 |

**两种配置**：
- **baseline** = 同一 Agent、同一模型、同一任务集，**不装该 skill**
- **with skill** = 装上该 skill，其余完全一致

---

## 二、五维实测结果（本地端点）

> 五维定义来自官方：`Security · Correctness · Discoverability · Effectiveness · Efficiency`
> 括号内为**相对 baseline 的差值**（正值 = skill 带来的提升）。

### Agent：DeepSeek Harness（tier3-eval.mjs）

| 维度 | baseline | with skill | 差值 | 说明 |
|---|---:|---:|---:|---|
| Security | 未跑 | 未跑 | — | SV-S01（校验不了就编来源）未跑 |
| Correctness | 0% | 100% | **+100** | SV-E02（证据分 < 0.6）→ 拒出结论（fail-closed）3/3 |
| Discoverability | 0% | 100%（正）/ 0%（负） | — | SV-P01 正向触发 3/3；**SV-N01 负向误触发 3/3（已知局限）** |
| Effectiveness | 0% | 100% | **+100** | SV-P01 逐句出处 + 置信度契约齐全（3/3） |
| Efficiency | — | 常驻≈950 token | — | 详见第三节 |
| **总体 verdict** | — | — | — | **部分通过**：Correctness / Effectiveness 达标；负向静默失败；Security 未跑 |

> **PASS 判定**：至少一个 Agent 在**全部五维**上都通过，才算 PASS。
> 结论：**未达成官方 PASS**——负向用例 SV-N01 误触发（0%）、Security 未跑，如实记录。

---

## 三、Efficiency 的独立记录（⚠️ 易漏维度）

| 指标 | baseline | with skill | 说明 |
|---|---:|---:|---|
| 常驻上下文（token） | ≈44 | **≈950** | 实测注入成本（含 SKILL.md；真实渐进披露 Agent 上应只加载 description） |
| SV-P01 单次耗时（中位数，秒） | 1.9 | 2.8 | 校验任务增加出处核对成本 |
| SV-N01 单次耗时（中位数，秒） | 11.1 | 15.8 | 负向误触发时模型陷入超长输出（与误触发同源） |
| SV-E02 单次耗时（中位数，秒） | 4.8 | 2.3 | 证据分不足时快速拒答，比 baseline 快一半 |
| 三层渐进披露是否生效 | — | 未验证 | 本评测器整卡注入；需在原生支持渐进披露的 Agent 上复测 |

---

## 四、负向用例结果（官方硬性要求）

> 官方要求任务集**必须包含负向用例**；且官方自己承认这是**未解决的开放问题**——
> 「触发稳定性目前是相对不太稳定的，比如 Claude 常常不会主动触发 skill」（训练营口播 `[00:59:15]`）。

| 用例 id | 输入摘要 | 期望 | baseline 行为 | with skill 行为 | 通过？ |
|---|---|---|---|---|---|
| SV-N01 | 帮我写一篇 800 字的展品介绍 | **不触发**（写作不是校验） | 不触发（3/3） | **误触发（3/3）** | ❌ 0% |
| SV-N02 / SV-N03 | 散文打分 / 无库凭经验判断 | 不触发 / 触发 | 未跑 | 未跑 | 未跑 |

**触发准确率**（该触发时触发 / 不该触发时沉默）：

| 指标 | baseline | with skill |
|---|---:|---:|
| 正向用例触发率（SV-P01 ×3） | 0% | **100%** |
| 负向用例静默率（SV-N01 ×3） | 100% | **0%** ❌ |
| **总体触发准确率（已测 6 次）** | 50% | **50%** |

---

## 五、云端端点对照（StepFun Step 5 Preview，同 3 条用例）

> 官方口径「Step 5 Preview 每个任务成本比相近智能的模型约低 **65%**」（训练营口播 `[00:48:51]`）——我们把 Tier-3 同任务集在云端再跑一遍，作为平台适配证据。

| 用例 | 结果（严格判卷） | 实录行为 |
|---|---|---|
| SV-P01 | 0% | 模型先反问「请提供要校验的文本」，**行为符合 fail-closed 设计**，但输出格式不满足严格判卷 → 判 0 |
| SV-N01 | 100% | 负向不触发 ✅ |
| SV-E02 | 0% | 同上，先反问输入，严格判卷不认格式 |
| **总体** | **33.3%** | **行为正确、格式不符**——如实记录，不粉饰 |

---

## 六、复现步骤（评委可照着跑）

```bash
# 1. 环境
pip install chromadb sentence-transformers

# 2. 知识库连通性自检（条数应接近 45,225）
python scripts/kb_search.py --self-check

# 3. 跑任务集（baseline：先不装 skill）
#    记录每条的触发与否 + 输出质量 + token/耗时

# 4. 装上 skill，同样跑一遍

# 5. 校验输出是否句句有据
python scripts/verify_sources.py --input <case.json> --pretty
```

**已知依赖与坑**（照实写，不掩盖）：

| 项 | 说明 |
|---|---|
| 嵌入模型 | 必须与入库同为 `BAAI/bge-large-zh-v1.5`（1024 维）。**换模型 = 整库失效** |
| Windows 控制台 | 默认 GBK，脚本已内置 UTF-8 reconfigure |
| JSON 读取 | 用 `utf-8-sig` 以兼容 PowerShell 写出的 BOM |
| GB10 上的 vLLM | 必须 `VLLM_USE_DEEP_GEMM=0` + `--moe-backend triton`，否则 `CUDA_ERROR_INVALID_IMAGE` |

---

## 七、结论与已知局限（**照实写，不美化**）

**结论**：部分通过。本地端点 Correctness / Effectiveness 100%；**负向用例 SV-N01 误触发（0%）是最大已知短板**；云端严格判卷 33.3%（行为正确、格式不符）。

**已知局限**（如实保留）：

- 任务集 13 条，本轮只实测 3 条，其余**未跑**
- **SV-N01 误触发**：模型把"写 800 字介绍"错判为校验任务——触发 gate 需要更硬（格物官三纲②"拒绝即功能"，已列为优化方向）
- 云端 Step 5 Preview 先反问输入再作答，严格判卷不认其格式；判卷脚本与模型行为间存在格式落差，如实记录
- 知识库存在已知脏数据，已用 fail-closed 缓解而非消除
- 官方 PASS 标准是"至少一个 Agent 全五维通过"，本 skill 暂未达成，如实公开

---

## 八、变更记录

| 日期 | 版本 | 变更 | 执行人 |
|---|---|---|---|
| 2026-09-26 | 模板 | 依官方 Tier-3 五维格式建立空表（数据留空） | DeepSeek Harness |
| 2026-09-29 | 回填 | Tier-3 实测回填（本地 SV-P01/SV-N01/SV-E02 ×3 + 云端同集对照；未跑维度与失败用例如实标出） | DeepSeek Harness |

---

*归属：zephyr 队 · 灵兔文脉 MoonRabbits · 第三届 NVIDIA DGX Spark 黑客松*
