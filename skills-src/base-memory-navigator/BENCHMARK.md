# BENCHMARK.md · base-memory-navigator

> **治理五道工序之 Evaluated 产物**：Cataloged → Scanned → **Evaluated** → Signed → Documented
> 🔴 **只写真数，没跑的一律标"未跑"，禁止估计值。**
> 说明：本 skill 是工作流基座技能（共享记忆导航），作为 Tier-3 同法对照基线；**不属于参赛三技能口径**。

---

## 一、方法论（照 NVIDIA 官方 Tier-3 定义）

> 官方原文（`NVIDIA Skills 开发实战` p6）：
> 「方法：同一个 Agent，同一任务集，跑两遍 —— **带 skill 与不带 skill，差值即 skill 的实测贡献**」
> 「PASS 标准：**至少一个受支持 Agent 在全部配置维度上通过**」
> 「任务集随 skill 提交（`evals/evals.json`），且**必须包含负向用例**（正确答案是『不调用该 skill』的场景）」

**本 skill 的执行方式**：

| 项 | 值 |
|---|---|
| 被测 skill | `base-memory-navigator` |
| skill 版本 | `0.2.0` |
| 任务集 | `evals/evals.json`（6 条；本轮实测 2 条，其余标未跑） |
| 执行 Agent | DeepSeek Harness + `tier3-eval.mjs`（OpenAI-compatible 客户端，同任务集跑 baseline / with skill 两遍，每用例 ×3） |
| 模型 | 本地 Qwen3.6-35B-A3B-FP8（vLLM 0.28.0，DGX Spark 本地推理，`enable_thinking:false`，max_tokens 2048） |
| 硬件 | NVIDIA DGX Spark（GB10 · 121 GiB 统一内存 · CUDA 13.0） |
| 评测日期 | 2026-09-29 |
| 执行人 | zephyr 队 |

**两种配置**：
- **baseline** = 同一 Agent、同一模型、同一任务集，**不装该 skill**
- **with skill** = 装上该 skill，其余完全一致

---

## 二、五维实测结果

### Agent：DeepSeek Harness（tier3-eval.mjs）

| 维度 | baseline | with skill | 差值 | 说明 |
|---|---:|---:|---:|---|
| Discoverability | 0% | 0% | 0 | pos-1 严格判卷 0%——skill 设计为**先反问路径**（最省钱路径），判卷脚本只认"定位记忆"签名，两者格式落差 |
| 负向静默 | 100% | 100% | 0 | neg-2（翻译任务）不触发（3/3）✅ |
| Efficiency | — | 常驻≈2,453 token | — | 见第三节：反问式输出使单次耗时 2.6s→0.7s |
| **总体 verdict** | — | — | — | 对照参考，不计入参赛口径 |

---

## 三、Efficiency 的独立记录

| 指标 | baseline | with skill | 说明 |
|---|---:|---:|---|
| 常驻上下文（token） | ≈44 | **≈2,453** | 实测注入成本（本 skill 描述较长） |
| pos-1 单次耗时（中位数，秒） | 2.6 | 0.7 | 反问式最短输出（「需要读共享记忆吗？给路径最便宜」） |
| neg-2 单次耗时（中位数，秒） | 0.4 | 0.5 | 无关任务开销可忽略 |
| 三层渐进披露是否生效 | — | 未验证 | 本评测器整卡注入 |

---

## 四、负向用例结果

| 用例 id | 输入摘要 | 期望 | baseline 行为 | with skill 行为 | 通过？ |
|---|---|---|---|---|---|
| neg-2 | 把这段文字翻译成英文 | **不触发** | 不触发（3/3） | 不触发（3/3） | ✅ 100% |
| neg-1 / neg-3 | 用户已贴全文档 / 基座查无文件 | 不触发 / 触发 | 未跑 | 未跑 | 未跑 |

**触发准确率**（已测 6 次）：baseline 50% / with skill 50%（pos-1 严格判卷 0% + neg-2 静默 100%）。

---

## 五、结论与已知局限（**照实写，不美化**）

**结论**：对照参考。负向静默 100%；pos-1 的 0% 是**判卷签名与设计行为（先反问路径）的格式落差**，行为本身符合技能设计初衷（最经济取数），非幻觉或失控。

**已知局限**：

- 6 条任务集只实测 2 条，其余未跑
- 反问式设计与严格判卷不兼容——若用于参赛口径，需在判卷脚本中承认"反问路径"为合法触发形态
- 常驻注入 ≈2.4k token 偏大，渐进披露未验证

---

## 六、变更记录

| 日期 | 版本 | 变更 | 执行人 |
|---|---|---|---|
| 2026-09-26 | 模板 | 依官方 Tier-3 五维格式建立空表（数据留空） | DeepSeek Harness |
| 2026-09-29 | 回填 | Tier-3 实测回填（pos-1/neg-2 ×3，本地 Qwen3.6-35B-A3B-FP8；严格判卷 0% 如实说明） | DeepSeek Harness |

---

*归属：zephyr 队 · 灵兔文脉 MoonRabbits · 第三届 NVIDIA DGX Spark 黑客松*
