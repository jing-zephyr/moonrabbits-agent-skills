# skill-card · exhibit-narrative

> NVIDIA Verified Skill 治理五道工序之 **Documented** 产物（信任记录）。
> 参考工序：Cataloged → Scanned → Evaluated → Signed → **Documented**

| 项 | 内容 |
|---|---|
| **skill 名** | `exhibit-narrative` |
| **中文名** | 展品叙事官 |
| **版本** | 0.2.0 |
| **一句话** | 从一件展品的照片或信息，生成"每句可溯源"的文化叙事 |
| **Owner** | zephyr 队（灵兔文脉 MoonRabbits 项目） |
| **License** | Apache-2.0 |

## 做什么 / 给谁用

| 做什么 | 给谁用 |
|---|---|
| 展品 → 可溯源叙事 + 出处 + 置信度 | 看展观众（小程序/H5 用户） |
| 生成展签、看展笔记、讲解稿 | 博物馆观众服务、教育场景 |
| 按观众画像调整讲述 | 家长、教师、专业观众、外国观众 |

## 依赖

| 类型 | 依赖 | 说明 |
|---|---|---|
| 数据 | 陶瓷史知识库（ChromaDB，45,225 条） | **只从库取事实**；库为空则拒答 |
| 模型 | 任一 OpenAI 兼容端点（本地 Qwen3.6 / StepFun Step 5 Preview） | **换模型只改 3 个值** |
| 脚本 | `scripts/kb_search.py`、`scripts/verify_sources.py` | 按需执行 |
| 兄弟 skill | `source-verifier`（校验）、`audience-adapter`（适配） | 可组合 |

## 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| **知识库幻觉**（ASR 谐音错字、空标签） | 输出不可靠事实 | **fail-closed**：检索不到即拒答；出处必须可点 |
| **越界请求**（鉴定/估价/交易） | 合规风险 | SKILL.md 写明 negative triggers + 硬约束；评测含负向用例 |
| **版权**（复制展签/图录原文） | 侵权风险 | 硬约束：只提取事实，叙事原创 |
| **密钥泄露** | 安全事故 | 硬约束：不打印明文 token；密钥只在服务端 |
| **图像不足**（模糊/非展品） | 误判 | 前置检查：不满足则**先问用户**，不许猜 |

## 部署地域（Deployment Geography）

| 项 | 说明 |
|---|---|
| 适用地域 | 全球（无地域限制） |
| 推理位置 | 知识库检索与生成**默认在本地 NVIDIA DGX Spark 上完成** |
| 数据留存 | 本地部署时，文献与用户照片**不出本机** |
| 跨境传输 | 若启用云端模型（StepFun `api.stepfun.com`）：仅发送**当前查询与用户上传的展品照片**；**不发送知识库全文** |
| 敏感数据 | 不处理个人隐私数据、企业涉密数据；不处理非展品类图像 |

## 支撑材料（References）

| 类型 | 出处 |
|---|---|
| 技能规范 | Anthropic Agent Skills 开放规范（`SKILL.md` + `references/` + `scripts/` + `evals/`） |
| 治理框架 | NVIDIA-Verified Agent Skills（Cataloged → Scanned → Evaluated → Signed → Documented） |
| 评测方法 | NVIDIA `SkillEvaluator` Tier-3（同 Agent 同任务集，带/不带 skill 跑两遍） |
| 安全扫描 | NVIDIA `SkillSpector`（68 种漏洞模式 / 17 类，对齐 OWASP LLM Top 10 · OWASP Agentic AI Risks · MITRE ATLAS） |
| 签名规范 | OpenSSF Model Signing（`skill.oms.sig` 分离式签名 + 根证书验证） |
| 本项目任务集 | `evals/evals.json`（16 条，含 3 条负向用例） |
| 本项目实测 | `BENCHMARK.md`（五维：Security · Correctness · Discoverability · Effectiveness · Efficiency） |
| 确定性内核 | `scripts/verify_sources.py`（判定规则与 `scripts/verify-conflict-rules.js` 同源） |
| 领域参考 | `references/five-color.md`（五色季判定，未确认处已标注）、`references/audience-styles.md`、`references/troubleshooting.md` |

## 伦理与边界（Ethical）

| 事项 | 立场 |
|---|---|
| 真伪鉴定 / 市场估价 / 文物交易 | **永不提供**（监管敏感领域，写死在负触发与硬约束里，并由负向用例 AN-N02/N03 覆盖） |
| 版权 | 只提取**事实**（年代/窑口/工艺）；叙事文本**原创生成**；**不复制**展签/图录原文 |
| 文化表述 | 以知识库来源与馆方资料为准；**来源冲突时显式暴露**并标注存疑，不擅自定论 |
| 文化框架的使用 | 五色观**仅用于叙事连接与组织框架**，**不得替代考据事实**；未确认的季**不得推断** |
| 不确定性 | 检索不到即明确说「知识库未找到」，**绝不编造**（fail-closed） |
| AI 生成标注 | 输出按平台规范标注「AI 生成」 |
| 不替代人 | 定位为**辅助讲解**，不替代策展人、讲解员与专业鉴定机构 |
| 密钥 | 不打印任何明文 token / 密钥 / 内网地址 |

## 评测状态

| 项 | 状态 |
|---|---|
| `evals/evals.json` | ✅ 16 条（含 3 条负向、4 条 Efficiency、3 条边界、2 条安全、1 条组合） |
| `BENCHMARK.md`（带/不带 skill 五维对比） | ✅ 已实测回填（每用例 ×3 取中位数；原始数据见公开仓 `evidence/`） |
| 签名 `skill.oms.sig` | ⏳ 待签名 |
