# 灵兔文脉 · Agent Skills 套件（NVIDIA DGX Spark 黑客松）

> 第三届 NVIDIA DGX Spark 黑客松 · Agent Skills 开发挑战赛
> 主题：**为 Agent 装上专业技能** ｜ 队伍：zephyr

---

## 〇、作品结构：三个 skill 角色的落地

> **哲学内核（甲方 2026-09-29 定案）**：道生一，一生二，二生三，三生万物。把脉（分）= 一生二：混沌想法 → 问出清浊、拆出结构；编排（博弈）= 二生三：多专家互相校验，生出经得起查的内容；粘合（合）= 三生万物：官方积木+自研+算力合流成链，落地成万物。整体 = 从合到分、分再到合；中间的能量 = 校验/拒答/签名这些"对抗产生信任"的机制。

| 角色（甲方 2026-09-26 拍板的边界） | 落地形态 |
|---|---|
| **Skill 1 · 需求工程化**（入口） | `bamai`（本目录） |
| **Skill 2 · 多专家编排**（主体） | `exhibit-narrative` + `source-verifier` + `audience-adapter`（三个可组合技能） |
| **Skill 3 · NVIDIA 资源粘合**（底座） | `engine/`（官方积木冻结 + LOCK + 校验脚本 + 适配层，见 §三） |

---

## 一、技能清单（可组合）

| skill | 中文名 | 一句话 | 可独立使用？ |
|---|---|---|---|
| `bamai` | 把脉 | 模糊想法 →（最多六问）→ 澄清的问题 + 工程需求 + 任务拆分 | ✅ |
| `exhibit-narrative` | 展品叙事官 | 展品照片 → **每句可溯源**的文化叙事 + 出处 + 置信度 | ✅（需知识库） |
| `source-verifier` | 溯源校验官 | 任意文本**逐句找出处**、给置信度、暴露冲突——**只校验不生成** | ✅ 通用件，零领域依赖 |
| `audience-adapter` | 观众适配官 | 按观众画像换表达与详略——**只换表达，不换事实** | ✅ |
| `base-memory-navigator` | 基座记忆导航 | 开工前先问后读，用最经济的方式对齐上下文（早期试水） | ✅ |

**组合链路（体现"Skills 设计与融合"）**：

```
bamai  →  exhibit-narrative  →  audience-adapter  →  source-verifier
  问清需求、拆好任务       产生内容+出处        换表达不动事实        最后一道闸
```

**为什么是"一套"而不是"一个"**：
- 评委 25% 权重明写「**Skills 设计与融合**」——可组合、可复用比单个孤立 skill 强；
- `source-verifier` 不含任何文博知识 → 任何"不许编造"的任务都能挂上它；
- 各技能职责单一（窄触发），符合官方「SKILL.md 是路由表不是百科」的心法。

---

## 二、目录结构

```
skills-src/
├── bamai/        # Skill 1：SKILL.md + evals(11，含 3 负向) + skill-card + BENCHMARK
├── exhibit-narrative/           # 旗舰（D6 定名）｜ SKILL.md + references/ + scripts/ + evals(16) + BENCHMARK + skill-card
│   ├── references/
│   │   ├── five-color.md        # 五色五季判定（清理版；原版留档 five-color.original-20260923.md）
│   │   ├── season-white.md      # 白·金季第一季范围（甲方 9/24 口径：白陶→白瓷→衍生青花）
│   │   ├── audience-styles.md   # 四类观众画像 + 篇幅档位
│   │   └── troubleshooting.md   # 排查手册
│   └── scripts/
│       ├── kb_search.py         # 知识库检索（库连不上走 exit 3，绝不假装"没有"）
│       └── verify_sources.py    # 出处与置信度校验（纯函数、零网络、零随机）
├── source-verifier/             # SKILL.md + evals(13) + BENCHMARK + skill-card
├── audience-adapter/            # SKILL.md + references/styles.md + evals(12) + BENCHMARK + skill-card
├── base-memory-navigator/       # SKILL.md v0.2.0（通用化；原版留档 SKILL.original-20260922.md）+ evals(6) + BENCHMARK
└── _runtime/
    ├── stepfun.mjs              # ★ StepFun 适配层（换模型只改 3 个值）
    └── run-selftest.mjs         # 自检脚本（已验证）
```

> 治理产物状态：SKILL.md **5/5** · skill-card **5/5**· evals **5/5** · BENCHMARK **5/5（模板，数据留空待实测）** · `skill.oms.sig` **0/5（待签名）**。

---

## 三、Skill 3 · 官方技能选型（筛选，不全上）

> 甲方 2026-09-29 拍板口径：「官方有的产品线和 300 多个 skills 不是全部都上，而是筛选出适合我们这个产品的。」

**四道筛子**：① 需求匹配（查询/叙事/语音/治理 ↔ 41 产品线）② 可跑性（赛期内、单机 DGX Spark、无 NVAIE 授权）③ 官方 demo 路径 ④ 红线（不改官方、锁 commit、sha256+署名）。

| 档 | skill | 用法 |
|---|---|---|
| 🟢 实跑 | `nvidia-skill-finder` | 官方目录路由：演示"在 382 个里选对"的方法与技能命中日志 |
| 🟢 实跑 | `skill-card-generator` | 官方治理卡片生成器（demo 第 4 步同款工具） |
| 🥈 冻结证据 | `tao-generate-image-grounding` · `tao-generate-referring-expressions` | 整目录冻结于 `engine/vendor`（锁 commit + sha256），证明"真比过、真筛过"；**不当主链路**（ARM64 容器未验证、单次 90–150 秒、搬不走） |
| 🟡 方法对标 | `nemotron-retrieval-recipes` · `rag-eval` | 检索"embed 召回 → rerank 排序"与 RAGAS 评测方法学，写入 BENCHMARK 协议与答辩材料 |
| 🔵 阶跃语音 | StepAudio Skills（StepFun 打包的 TTS/ASR） | 讲解语音，赛后接入（平台适配 15% 的另一半） |
| ⛔ 明确不用 | dynamo / megatron / slurm / jetson / doca / cuopt / tao-train / earth2studio / omniverse / warp / isaac… | 领域不符 / 无对应硬件 / 搬不走（详见 `engine/LOCK.json` 与 `_知识库\05-决策日志.md` D27） |

**官方积木全部冻结在 `engine/vendor/nvidia-skills/`（39 文件，含 SKILL.md / skill-card / skill.oms.sig / evals / BENCHMARK），配 `engine/scripts/verify-lock.mjs` 逐文件 sha256 核对。** 一个字节都不改（改了签名即失效，官方原话）；环境差异全在 `engine/adapter/`。

---

## 四、运行时适配层 `_runtime/stepfun.mjs`

**设计目标**：**换模型只改 3 个值**（`baseUrl` / `model` / `apiKey`）——正是官方说的"任何 OpenAI 兼容端点"。

### 已实测并固化进代码的坑

| 坑 | 现象 | 代码里的处理 |
|---|---|---|
| 推理模型吃额度 | `step-5-preview` 的 `max_tokens=16` → `content` 为空（token 全被 `reasoning` 吃掉） | 默认 `max_tokens=1024`；空了自动放大 4 倍重试（`retryOnEmpty`） |
| 端点是两个 | `/v1`（按量）与 `/step_plan/v1`（订阅额度） | 默认走 `/step_plan/v1` |
| 返回带思考链 | `message.reasoning` | 一并返回，供"可解释的可信生成"使用 |

### 自检结果（2026-09-23 实测）

```
① 配置自检   endpoint=…/step_plan/v1  model=step-5-preview  ok=true  reply="通了"
② 坑复现     max_tokens=16 不重试 → content 长度 0，reasoning 43 字
③ 坑修复     同请求 + 自动重试 → content 58 字，retried=true
```

**密钥**：`process.env.STEPFUN_API_KEY` 或库外文件；**本模块永不打印密钥**（只用 `maskKey()` 掩码显示）。

---

## 五、交付物清单（赛事要求对照）

| 赛事要求 | 对应产物 | 状态 |
|---|---|---|
| **必须包含 skill markdown 文件** | `*/SKILL.md` ×5 | ✅ |
| 部署说明：如何设计 Agent Skills | 本 README + 各 SKILL.md + `engine/adapter` | ✅ |
| 技术栈说明：NVIDIA SDK / 模型 + StepFun 模型 | 见 §六 | ⏳ SDK 具名待补 |
| 项目说明文档 ≥500 字 | `README（竞赛仓库首页）.md`（草案 977 字，待落地） | ⏳ |
| 演示视频（B 站） | 三帧分镜脚本已备 | ⏳ |
| 十日谈征文 | `_知识库\征文\` 5 篇初稿 + 3 篇骨架 | 🔄 |
| Tier-3 评测证据 | `evals/evals.json` ×5 ✅ / `BENCHMARK.md` ×5 待实测回填 | 🔄 |

---

## 六、技术栈

| 层 | 组件 |
|---|---|
| 硬件 | **NVIDIA DGX Spark（GB10）**，121 GiB 统一内存 |
| 本地模型 | **Qwen3.6-35B-A3B-FP8**（35GB，ModelScope 已下载） |
| 推理服务 | **vLLM 0.28.0**（GB10 需 `VLLM_USE_DEEP_GEMM=0` + `--moe-backend triton`） |
| 云端模型 | **StepFun Step 5 Preview**（600B/27B MoE · 1M 上下文 · 视觉输入）；训练营 PDF 口径 **Step 3.7 Flash**（198B/11B · 256K · Apache-2.0 · Day-0 NIM）两者并列说明 |
| 云端端点 | `https://api.stepfun.com/step_plan/v1`（订阅额度） |
| 知识库 | ChromaDB `moon_rabbits_kb`，**45,225 条**，嵌入 `bge-large-zh-v1.5`（1024 维） |
| 官方技能生态 | NVIDIA/skills（固定 commit `d8519c5`，冻结于 `engine/vendor`） |
| skill 规范 | Anthropic 开源 Agent Skills 规范（`SKILL.md` + `references/` + `scripts/` + `evals/`） |

---

## 七、红线（写死在每个 SKILL.md 里）

1. **fail-closed**：知识库未收录 → 明确说"未找到"，**绝不编造**；
2. **永不碰**：真伪鉴定、市场估价、文物交易；
3. **不复制**展签/图录原文（版权）——只提取事实，叙事原创；
4. **不打印**任何明文 token / 密钥 / 内网地址；
5. **不改** checked-in 配置、官方 skill 或用户原始文件。
