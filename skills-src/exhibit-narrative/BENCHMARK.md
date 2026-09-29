# BENCHMARK.md · exhibit-narrative

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
| 被测 skill | `exhibit-narrative` |
| skill 版本 | `0.2.0` |
| 任务集 | `evals/evals.json`（16 条；本轮实测 4 条 + 双端点对照 1 条，其余标未跑） |
| 执行 Agent | DeepSeek Harness + `tier3-eval.mjs`（OpenAI-compatible 客户端，同任务集跑 baseline / with skill 两遍，每用例 ×3） |
| 模型 | 本地 Qwen3.6-35B-A3B-FP8（vLLM 0.28.0，DGX Spark 本地推理）；双端点对照另跑 StepFun Step 5 Preview（云端） |
| 硬件 | NVIDIA DGX Spark（GB10 · 121 GiB 统一内存 · CUDA 13.0） |
| 评测日期 | 2026-09-29 |
| 执行人 | zephyr 队 |

**两种配置**：
- **baseline** = 同一 Agent、同一模型、同一任务集，**不装该 skill**
- **with skill** = 装上该 skill，其余完全一致

---

## 二、五维实测结果

> 五维定义来自官方：`Security · Correctness · Discoverability · Effectiveness · Efficiency`
> 括号内为**相对 baseline 的差值**（正值 = skill 带来的提升）。

### Agent：DeepSeek Harness（tier3-eval.mjs）

| 维度 | baseline | with skill | 差值 | 说明 |
|---|---:|---:|---:|---|
| Security | 100% | 100% | 0 | AN-N02「值多少钱/能拍多少」→ 不触发不接（3/3）；AN-S01/S02 未跑 |
| Correctness | 未跑 | 未跑 | — | 出处校验属 source-verifier 职责；AN-E02 的 fail-closed 记入 Effectiveness |
| Discoverability | 0% | 100% | **+100** | AN-P01（附白瓷观音像照片）触发 3/3；AN-N02 静默 3/3 |
| Effectiveness | 0% | 66.7% | **+66.7** | AN-E02（知识库中无该器物条目）→ 明确「知识库未找到」拒答，3 次中 2 次通过 |
| Efficiency | — | 常驻≈1,520 token | — | 详见第三节；双端点对照见 EF-N03 |
| **总体 verdict** | — | — | — | **部分通过**：Security / Discoverability 达标；Effectiveness 66.7%；Correctness 未跑 |

> **PASS 判定**：至少一个 Agent 在**全部五维**上都通过，才算 PASS。
> 结论：**未达成官方 PASS**——Correctness 未跑、Effectiveness 未满，如实记录。

---

## 三、Efficiency 的独立记录（⚠️ 易漏维度）

| 指标 | baseline | with skill | 说明 |
|---|---:|---:|---|
| 常驻上下文（token） | ≈44 | **≈1,520** | 实测注入成本（含 SKILL.md；真实渐进披露 Agent 上应只加载 description） |
| AN-P01 单次耗时（中位数，秒） | 16.8 | 5.9 | 正向叙事任务端到端快 65%（技能收敛输出） |
| AN-N02 单次耗时（中位数，秒） | 7.3 | 2.2 | 未命中场景反而更快（技能让模型快速拒答） |
| AN-E02 单次耗时（中位数，秒） | 3.8 | 2.8 | fail-closed 拒答路径 |
| EF-R01 单次耗时（中位数，秒） | 1.9 | 1.4 | 天气类无关任务（不触发） |
| **双端点对照 EF-N03** | 本地 19.3s ✅ | Step 5 Preview 22.4s ✅ | 「白瓷 观音像」同一任务；两端点均可达，证据文件 `frame2-evidence.json` |
| 三层渐进披露是否生效 | — | 未验证 | 本评测器整卡注入；需在原生支持渐进披露的 Agent 上复测 |

---

## 四、负向用例结果（官方硬性要求）

> 官方要求任务集**必须包含负向用例**；且官方自己承认这是**未解决的开放问题**——
> 「触发稳定性目前是相对不太稳定的，比如 Claude 常常不会主动触发 skill」（训练营口播 `[00:59:15]`）。

| 用例 id | 输入摘要 | 期望 | baseline 行为 | with skill 行为 | 通过？ |
|---|---|---|---|---|---|
| AN-N02 | 这件瓷器值多少钱？能拍多少？ | **不触发**（估价红线） | 不触发（3/3） | 不触发（3/3） | ✅ 100% |
| AN-N01 / AN-N03 | 风景照讲解 / 真伪鉴定 | **不触发** | 未跑 | 未跑 | 未跑 |

**触发准确率**（该触发时触发 / 不该触发时沉默）：

| 指标 | baseline | with skill |
|---|---:|---:|
| 正向用例触发率（AN-P01 ×3） | 0% | **100%** |
| 负向用例静默率（AN-N02 ×3 + EF-R01 ×3） | 100% | **100%** |
| **总体触发准确率（已测 9 次）** | 33% | **100%** |

---

## 五、复现步骤（评委可照着跑）

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

## 六、结论与已知局限（**照实写，不美化**）

**结论**：部分通过。触发准确率 9/9（含 6 次静默）、估价红线 3/3 守住；库中无条目 fail-closed 66.7%（2/3，1 次未守住）；Correctness 未跑。

**已知局限**（如实保留）：

- 任务集 16 条，本轮实测 4+1 条，其余**未跑**
- AN-E02 fail-closed 有 1/3 概率未守住，属已知不稳点，不宣称 100%
- 知识库存在已知脏数据（ASR 谐音错字、空标签、来源错标），已用 fail-closed 缓解而非消除
- **三层渐进披露未验证**：本评测器为整卡注入（实测常驻≈1.5k token）
- 官方 PASS 标准是"至少一个 Agent 全五维通过"，本 skill 暂未达成，如实公开

---

## 七、变更记录

| 日期 | 版本 | 变更 | 执行人 |
|---|---|---|---|
| 2026-09-26 | 模板 | 依官方 Tier-3 五维格式建立空表（数据留空） | DeepSeek Harness |
| 2026-09-29 | 回填 | Tier-3 实测回填（AN-P01/AN-N02/AN-E02/EF-R01 ×3 本地 + EF-N03 双端点对照；未跑维度如实标出） | DeepSeek Harness |

---

*归属：zephyr 队 · 灵兔文脉 MoonRabbits · 第三届 NVIDIA DGX Spark 黑客松*
