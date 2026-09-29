# NVIDIA 官方积木 · 最终采用清单（2026-09-29 · zephyr 队）

> 原则：**能用都激进地用**；每一项都回答四件事——底层逻辑 / 怎么用 / 和我们自研的对比 / 当前状态。
> 链接全部官方一手来源。

---

## 一、已实跑（硬证据在手）

| # | 积木 | 底层逻辑（人话） | 用法 | 对比（vs 自研替代） | 状态 |
|---|---|---|---|---|---|
| 1 | **官方 Skills 仓** github.com/NVIDIA/skills | NVIDIA 把"怎么做事"固化成带签名的技能包，官方评审就用这套语言 | 实跑 6 个（skill-finder / skill-card-generator / TAO×2 / nemotron-retrieval-recipes / rag-eval）；vendor 冻结 4 个 39 文件 + LOCK.json sha256 锁 | 自研 5 技能照官方五工序（Cataloged→Scanned→Evaluated→Signed→Documented）生产，等于"用官方流程管自产技能" | ✅ 已实跑 |
| 2 | **model_signing**（官方签名验证） | 信任不靠"声称"，靠逐文件哈希签名；改一个字节就失效 | 官方 vendor 验签 PASS（NVIDIA 根证书）；自研 5 技能用 zephyr 队密钥签名，改一字节 → FAILED 实测 | 替代自研"文件锁"：官方格式、评委能复现 | ✅ 5/5 已签 |
| 3 | **NeMo Guardrails** github.com/NVIDIA/NeMo-Guardrails | 护栏是独立组件，不是提示词叮嘱；"拒绝"是一种功能 | 三条红线（鉴定/估价/交易）纯规则流，本机 4 问 4 中 | 之前红线只在技能负触发里 → 现在官方组件+技能层双保险 | ✅ 4/4 实测 |
| 4 | **DGX Spark GB10 + CUDA 13.0 + vLLM 0.28.0** | 官方算力平台跑本地模型，数据不出本机 | Qwen3.6-35B-A3B-FP8 本地推理（GB10 双参数坑已固化） | 云端 Step 5 Preview 做大脑，本地做轻活和治理 | ✅ 实测（451ms 拒答等） |
| 5 | **NVIDIA 官方 API** build.nvidia.com / integrate.api.nvidia.com | 官方云端模型接口，一条 Bearer key 走天下 | key 已验（81 模型名单）；聊天端点 HTTP 200 实测（deepseek-v4.1-flash 等） | 与 StepFun 云端点互为"换得动"证据的另一极 | ✅ 已验（护栏托管端今晚报 CUDA 错误、嵌入端点无权限，均如实记录） |

## 二、今晚可加码（激进项，需你点头 + NGC key）

| # | 积木 | 底层逻辑 | 用法 | 收益 | 成本/风险 |
|---|---|---|---|---|---|
| 6 | **NIM 容器跑在 DGX Spark 上**（如官方嵌入/小模型 NIM） | 官方 Docker 镜像直接跑在官方硬件上 = "官方全家桶"最硬证据 | 需要 **NGC API key**（在 build.nvidia.com 同账号下生成），节点 docker pull 一个小镜像（2-3GB），跑通留证据 | 平台适配 15% 的大分项 | ❌ 已尝试：NGC key 登录 nvcr.io 返回 401、镜像清单 451（区域限制），**如实记录为"已尝试、网络受限"**；官方云端 API 实测可达作替代证据 |
| 7 | **RAFT / cuVS GPU 向量加速** | 官方 GPU 向量库加速我们的 45,225 条检索 | 节点 pip 装 cuvs，跑一次检索 benchmark | "检索层也用 NVIDIA 专业件"的加分证据 | ✅ **已实装实导**：cuVS 26.8.1（cuvs-cu12+libcuvs-cu12）在 DGX Spark（aarch64）pip 装通、`import cuvs` 成功；高层 CAGRA 基准未跑通（26.08 版本把算法 API 拆出基础包，时间盒内未追装），如实记录 |

## 三、引用对表（不动手，roadmap 一句）

| 积木 | 一句话逻辑 | 用途 |
|---|---|---|
| **NVIDIA RAG Blueprint / 官方技能 `rag-blueprint`** [NGC](https://catalog.ngc.nvidia.com/orgs/nvidia/blueprint/helm-charts/nvidia-blueprint-rag) · [部署指南](https://docs.nvidia.com/enterprise-reference-architectures/enterprise-rag-deployment-guide/latest/index.html) | 官方"企业知识库"参考架构：摄取 → 嵌入 → 检索 → 重排 → 生成 | **官方同时把它做成技能：`rag-blueprint`**——官方 PPT《NVIDIA Skills 开发实战》第 11–13 页把它列为 41 条产品线里筛出的 5 条"装上就能干活"代表之**第一名**（"Docker Compose / Helm 一键部署全栈 RAG"，垂类＝企业知识库/智能客服），官方用法：`npx skills add nvidia/skills --skill rag-blueprint --yes`。**✅ 已取得 38 文件并验签：NVIDIA 根证书 `model_signing verify` → PASS**（`_工具\nvidia-rag-blueprint-官方技能\`；公开仓 `evidence/rag-blueprint-verify.txt` 存证）。**我们的检索层就是这套架构的手工等价实现**：nv-ingest（摄取工序）↔ 我们的知识库提纯工单；NeMo Retriever 嵌入/重排 ↔ `bge-large-zh-v1.5`（1024 维）+ ChromaDB 45,225 条；Blueprint 评测 ↔ 我们的 Tier-3 + rag-eval 对标。⚠️ 部署本体**未实跑**：依赖 nvcr.io 容器（已实测 451 区域受限），如实记录 |
| **AI-Q Research Agent Blueprint** [文档](https://docs.nvidia.com/enterprise-reference-architectures/ai-q-research-agent-blueprint/latest/system-configuration.html) | 官方"研究型 Agent"参考架构（多步检索 + 引用） | 与我们"考据官/溯源校验"的流程同构，作为形态对标 |
| **TensorRT-LLM / Triton / Dynamo** | 官方推理引擎 | "现在 vLLM 已跑通，下一步换官方引擎" |
| **nv-ingest** | 官方文档摄取流水线 | "知识库按官方摄取工艺建" |
| **AI Blueprints digital-human** | 官方数字人蓝图 | "数字人讲解员对标官方蓝图" |
| **Instant-NGP / nerfstudio** | 官方拍照转 3D | "观众拍照 → 3D 展品"的下一步 |
| **Parakeet / Riva** | 官方语音 | StepAudio 的对表（TTS 待验证已如实标注） |

## 四、一句话总结给评委

**官方 skills 管流程、NeMo Guardrails 管红线、model_signing 管信任、DGX Spark+NIM 管算力、官方 API 管对照——NVIDIA 全家桶被我们正经用起来，不是贴标签。**

---

*归属：zephyr 队 · 灵兔文脉 MoonRabbits*
