# 签名说明（SIGNING.md 草稿 · 公开仓定稿用）

> 状态：草稿（2026-09-29 18:30）。定稿后随公开仓"预赛提交定稿"单次提交进入 `moonrabbits-agent-skills`。
> 用途：回答评委"你们的签名到底签了什么、怎么验证"。

---

## 一、两个签名体系，诚实区分

| 体系 | 谁签的 | 证明什么 | 验证材料 |
|---|---|---|---|
| **官方 vendor 技能** | NVIDIA（官方技能仓自带 `skill.oms.sig`） | 该技能是 NVIDIA 官方签发、未被篡改 | NVIDIA 根证书 `nv-agent-root-cert.pem`（随仓公开） |
| **我们自研技能** | zephyr 队（EC P-256 私钥，2026-09-29 实签） | 技能自签名之日起未被篡改（完整性） | 公开的公钥 `zephyr-signing-key.pub.pem`（随仓公开） |

**诚实声明**：自研技能的签名证明的是**可验证的完整性**，不代表任何 NVIDIA 官方认证徽章；NVIDIA 官方徽章只属于官方技能。我们的立场（三帧之"信得过"）：**信任不来自注册表的徽章，来自可验证的完整性。**

## 二、验证方法（评委可复现）

```bash
# 1. 装官方工具链
pip install model-signing

# 2. 验证官方 vendor 技能（NVIDIA 签名 + 根证书）
model_signing verify certificate vendor/nvidia-skills/nvidia-skill-finder \
  --signature vendor/nvidia-skills/nvidia-skill-finder/skill.oms.sig \
  --certificate_chain nv-agent-root-cert.pem --ignore_unsigned_files
# → Verification succeeded

# 3. 验证自研技能（zephyr 公钥）
model_signing verify key skills-src/bamai \
  --public_key zephyr-signing-key.pub.pem \
  --signature skills-src/bamai/skill.oms.sig
# → Verification succeeded

# 4. 篡改一个字节后再验证 → Verification failed（Hash mismatch）
```

## 三、密钥管理纪律

- 私钥 `zephyr-signing-key.pem` **只在本机**，不进任何 git、不上传、不写入文档
- 任何自研技能文件改动后**必须重签**（命令见上，签完重跑验证）
- 公开仓只带公钥 + 签名文件 + 本说明

---

*归属：zephyr 队 · 灵兔文脉 MoonRabbits · 第三届 NVIDIA DGX Spark 黑客松*
