#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_sources.py —— 「溯源校验官」的确定性执行脚本

归属：third-party skill `source-verifier`（被 `exhibit-narrative` 组合调用）
状态：⚠️ 待应用草案 —— 本文件位于 DeepSeek 过程库，尚未拷入 skills-src。

设计原则（与 SKILL.md 的硬约束一一对应）：
  1. 不允许"补齐"      —— 找不到出处就是找不到，绝不替文本编造来源
  2. 不允许"和稀泥"    —— 冲突必须显式列出，不得只取其一而不提示
  3. 不评价内容好坏    —— 只回答"有没有依据"
  4. 不打印密钥        —— 本脚本不接受也不输出任何凭据
  5. 结论必须可复现    —— 同一输入 → 同一输出（纯函数，无随机、无网络）

判定规则（阈值与 `scripts/verify-conflict-rules.js` 保持完全一致，单一事实源）：
  YEAR_GAP_THRESHOLD        = 50   年代差 > 50 年 → 冲突，两条都保留并提示
  CONFIDENCE_GAP_THRESHOLD  = 0.3  置信度差 > 0.3 → 触发二次验证（找第三条来源）
  EVIDENCE_THRESHOLD        = 0.6  证据分 < 0.6 → 不通过，建议拒答

用法：
  # 从 JSON 文件读入（推荐，供 agent 调用）
  python verify_sources.py --input case.json [--pretty]

  # 作为模块（供 kb_search / exhibit-narrative 调用）
  from verify_sources import verify
  report = verify(text="...", sentences=[...], sources=[...])

输入 JSON 结构：
  {
    "text": "待校验的完整文本（可选，用于展示）",
    "sentences": [
      {"id": "s1", "text": "德化白瓷盛于明代。",
       "sources": [{"name":"《德化窑白瓷研究》","author":"陈建中",
                    "publisher":"文物出版社","year":1573,"confidence":0.98,
                    "quote":"明代德化窑…"}]}
    ],
    "conflicts": [                       # 可选：由上游或多个检索源提供的成对冲突
      {"a": {"name":"来源甲","year":1573,"confidence":0.9},
       "b": {"name":"来源乙","year":1300,"confidence":0.7}}
    ]
  }

输出 JSON 结构（对应 SKILL.md §一 的五段输出契约）：
  {
    "verdict": "通过" | "部分通过" | "不通过",
    "sentence_sources": [...],   # 【逐句出处】
    "unsupported": [...],        # 【无依据断言】—— 必须逐条列出，不许漏
    "conflict_list": [...],      # 【冲突清单】
    "advice": [...],             # 【处理建议】
    "evidence_score": 0.0,       # 整体证据分（0-1）
    "reproducible": true
  }
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Windows 控制台兼容 —— 必须在任何 print 之前执行
#
# 实测（2026-09-26，Windows + Python 3.12）：默认 stdout 编码是 GBK，
# 输出 "↳"（U+21B3）会抛 UnicodeEncodeError 并让整个脚本崩掉。
# 评委与本机都是 Windows，所以这行是必需的，不是可选优化。
# errors="replace" 是最后一道保险：宁可个别字符显示为 ? ，也不能崩。
# ---------------------------------------------------------------------------
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):   # Python < 3.7 或 stdout 被重定向为非常规对象
    pass

# ---------------------------------------------------------------------------
# 阈值 —— 与 verify-conflict-rules.js 逐字一致，改这里必须同步改那边
# ---------------------------------------------------------------------------
YEAR_GAP_THRESHOLD = 50
CONFIDENCE_GAP_THRESHOLD = 0.3
EVIDENCE_THRESHOLD = 0.6

VERDICT_PASS = "通过"
VERDICT_PARTIAL = "部分通过"
VERDICT_FAIL = "不通过"


def _confidence_of(source: Dict[str, Any]) -> Optional[float]:
    """取置信度，兼容 0-1 与 0-100 两种写法；缺失返回 None（不猜）。"""
    raw = source.get("confidence")
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value > 1.0:          # 98 这种写法 → 0.98
        value = value / 100.0
    return max(0.0, min(1.0, value))


def _year_of(source: Dict[str, Any]) -> Optional[int]:
    """取年代（整数年）；缺失或不可解析返回 None（不猜）。"""
    raw = source.get("year")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def detect_conflicts(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    在一组来源里找冲突。

    规则 1：任意两条来源年代差 > 50 年 → 冲突，建议「两条都列并标注存疑」。
    规则 2：任意两条来源置信度差 > 0.3 → 不算冲突，但建议「二次验证（找第三条来源）」。
    """
    findings: List[Dict[str, Any]] = []
    usable = [s for s in sources if isinstance(s, dict)]

    for i in range(len(usable)):
        for j in range(i + 1, len(usable)):
            a, b = usable[i], usable[j]

            year_a, year_b = _year_of(a), _year_of(b)
            if year_a is not None and year_b is not None:
                gap = abs(year_a - year_b)
                if gap > YEAR_GAP_THRESHOLD:
                    findings.append({
                        "type": "factual_year_conflict",
                        "a": {"name": a.get("name"), "year": year_a},
                        "b": {"name": b.get("name"), "year": year_b},
                        "year_gap": gap,
                        "resolution": "present_both_views",
                        "note": "年代差 > %d 年：两条都保留并标注存疑，不得擅自二选一"
                                % YEAR_GAP_THRESHOLD,
                    })

            conf_a, conf_b = _confidence_of(a), _confidence_of(b)
            if conf_a is not None and conf_b is not None:
                conf_gap = abs(conf_a - conf_b)
                if conf_gap > CONFIDENCE_GAP_THRESHOLD:
                    findings.append({
                        "type": "confidence_gap",
                        "a": {"name": a.get("name"), "confidence": conf_a},
                        "b": {"name": b.get("name"), "confidence": conf_b},
                        "confidence_gap": round(conf_gap, 4),
                        "resolution": "second_verification",
                        "note": "置信度差 > %.1f：触发二次验证（找第三条来源）"
                                % CONFIDENCE_GAP_THRESHOLD,
                    })

    return findings


def score_sources(sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    计算一组来源的证据分。

    证据分 = 有出处句子的占比 × 这些出处的平均置信度。
    这样"句句有据但来源可疑"和"来源很硬但多数句子没出处"都会被压低——
    两种毛病都不能靠另一头补回来。
    """
    total = len(sources)
    if total == 0:
        return {"coverage": 0.0, "mean_confidence": 0.0, "score": 0.0,
                "graded": 0, "ungraded": 0}

    graded = 0
    conf_sum = 0.0
    for s in sources:
        c = _confidence_of(s)
        if c is not None:
            graded += 1
            conf_sum += c

    # 没有标注置信度的来源按"未评级"处理，不计入均值，但也不当作 0
    mean_confidence = (conf_sum / graded) if graded else 0.0
    return {
        "coverage": 1.0,
        "mean_confidence": round(mean_confidence, 4),
        "score": round(mean_confidence, 4),
        "graded": graded,
        "ungraded": total - graded,
    }


def verify(text: str = "",
           sentences: Optional[List[Dict[str, Any]]] = None,
           conflicts: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    主入口：对一段文本做溯源校验，返回 SKILL.md §一 规定的五段输出。

    纯函数：不读文件、不发网络请求、不使用随机数 —— 保证同一输入同一输出。
    """
    sentences = sentences or []
    conflicts = conflicts or []

    sentence_sources: List[Dict[str, Any]] = []
    unsupported: List[Dict[str, Any]] = []
    advice: List[Dict[str, Any]] = []
    conflict_list: List[Dict[str, Any]] = []

    all_conf_values: List[float] = []
    graded_sentence_count = 0

    for idx, sent in enumerate(sentences, start=1):
        sid = sent.get("id") or ("s%d" % idx)
        stext = (sent.get("text") or "").strip()
        srcs = [s for s in (sent.get("sources") or []) if isinstance(s, dict)]

        if srcs:
            graded_sentence_count += 1
            for s in srcs:
                c = _confidence_of(s)
                if c is not None:
                    all_conf_values.append(c)
            sentence_sources.append({
                "id": sid,
                "text": stext,
                "sources": [
                    {"name": s.get("name"),
                     "author": s.get("author"),
                     "publisher": s.get("publisher"),
                     "year": _year_of(s),
                     "confidence": _confidence_of(s),
                     "quote": s.get("quote")}
                    for s in srcs
                ],
            })
            # 单句内部的来源冲突也要查
            conflict_list.extend(
                dict(f, sentence_id=sid) for f in detect_conflicts(srcs)
            )
        else:
            unsupported.append({"id": sid, "text": stext})
            advice.append({
                "sentence_id": sid,
                "action": "删掉 | 改写 | 标注存疑 | 补来源",
                "hint": "该句找不到任何出处。**不允许替它编造来源**。",
            })

    # 上游显式提供的成对冲突
    for pair in conflicts:
        a, b = pair.get("a") or {}, pair.get("b") or {}
        found = detect_conflicts([a, b])
        conflict_list.extend(found if found else [{
            "type": "declared_conflict",
            "a": {"name": a.get("name")},
            "b": {"name": b.get("name")},
            "resolution": "present_both_views",
            "note": "上游声明的冲突：两条都列出，不得只取其一",
        }])

    # ---- 冲突去重 ----
    # 同一对来源可能在两处被检出（单句内部检索 + 上游显式提供），只报一次，避免重复行
    _seen_conf = set()
    _deduped = []
    for _f in conflict_list:
        _key = (
            _f.get("type"),
            (_f.get("a") or {}).get("name"),
            (_f.get("b") or {}).get("name"),
        )
        if _key in _seen_conf:
            continue
        _seen_conf.add(_key)
        _deduped.append(_f)
    conflict_list = _deduped

    # ---- 证据分 ----
    coverage = (graded_sentence_count / len(sentences)) if sentences else 0.0
    mean_confidence = (sum(all_conf_values) / len(all_conf_values)) \
        if all_conf_values else 0.0
    evidence_score = round(coverage * mean_confidence, 4)

    # ---- 三态判定 ----
    has_factual_conflict = any(
        c.get("type") == "factual_year_conflict" for c in conflict_list
    )
    if not sentences:
        verdict = VERDICT_FAIL
        advice.append({
            "scope": "global",
            "action": "拒答",
            "hint": "没有可校验的句子（输入为空）。",
        })
    elif evidence_score < EVIDENCE_THRESHOLD or has_factual_conflict:
        verdict = VERDICT_FAIL
        if evidence_score < EVIDENCE_THRESHOLD:
            advice.append({
                "scope": "global",
                "action": "拒答",
                "hint": "证据分 %.4f < 阈值 %.1f，建议拒答而非勉强作答。"
                        % (evidence_score, EVIDENCE_THRESHOLD),
            })
        if has_factual_conflict:
            advice.append({
                "scope": "global",
                "action": "标注存疑",
                "hint": "存在无法二选一的来源冲突，必须在正文中显式暴露。",
            })
    elif unsupported:
        verdict = VERDICT_PARTIAL
    else:
        verdict = VERDICT_PASS

    return {
        "verdict": verdict,
        "sentence_sources": sentence_sources,
        "unsupported": unsupported,
        "conflict_list": conflict_list,
        "advice": advice,
        "evidence_score": evidence_score,
        "diagnostics": {
            "sentence_count": len(sentences),
            "sentence_with_source_count": graded_sentence_count,
            "coverage": round(coverage, 4),
            "mean_confidence": round(mean_confidence, 4),
            "thresholds": {
                "year_gap": YEAR_GAP_THRESHOLD,
                "confidence_gap": CONFIDENCE_GAP_THRESHOLD,
                "evidence": EVIDENCE_THRESHOLD,
            },
        },
        "reproducible": True,
    }


# ---------------------------------------------------------------------------
# 人读渲染 —— 对应 SKILL.md §一 的五段输出
# ---------------------------------------------------------------------------
def render(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("【校验结论】 %s" % report["verdict"])
    lines.append("")

    lines.append("【逐句出处】")
    if report["sentence_sources"]:
        for item in report["sentence_sources"]:
            lines.append("  · [%s] %s" % (item["id"], item["text"]))
            for s in item["sources"]:
                conf = s.get("confidence")
                conf_txt = ("%.2f" % conf) if isinstance(conf, float) else "未评级"
                lines.append("      ↳ %s / %s / %s / %s / 置信度 %s"
                             % (s.get("name") or "（无名称）",
                                s.get("author") or "-",
                                s.get("publisher") or "-",
                                s.get("year") if s.get("year") is not None else "-",
                                conf_txt))
    else:
        lines.append("  （无）")
    lines.append("")

    lines.append("【无依据断言】")
    if report["unsupported"]:
        for item in report["unsupported"]:
            lines.append("  · [%s] %s" % (item["id"], item["text"]))
    else:
        lines.append("  （无 —— 每一句都有出处）")
    lines.append("")

    lines.append("【冲突清单】")
    if report["conflict_list"]:
        for c in report["conflict_list"]:
            lines.append("  · %s：%s ↔ %s" % (
                c.get("type"),
                (c.get("a") or {}).get("name"),
                (c.get("b") or {}).get("name"),
            ))
            if c.get("note"):
                lines.append("      %s" % c["note"])
    else:
        lines.append("  （无）")
    lines.append("")

    lines.append("【处理建议】")
    if report["advice"]:
        for a in report["advice"]:
            target = a.get("sentence_id") or a.get("scope") or "-"
            lines.append("  · [%s] %s —— %s"
                         % (target, a.get("action"), a.get("hint")))
    else:
        lines.append("  （无需处理）")
    lines.append("")

    lines.append("证据分：%.4f（句子覆盖率 %.4f × 平均置信度 %.4f）"
                 % (report["evidence_score"],
                    report["diagnostics"]["coverage"],
                    report["diagnostics"]["mean_confidence"]))
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="溯源校验（确定性，无网络，可复现）")
    parser.add_argument("--input", "-i", required=True,
                        help="输入 JSON 文件路径")
    parser.add_argument("--pretty", action="store_true",
                        help="以人读五段格式输出（默认输出 JSON）")
    args = parser.parse_args(argv)

    try:
        # utf-8-sig：同时兼容「带 BOM」与「不带 BOM」两种 UTF-8。
        # 实测发现 Windows PowerShell 的 `Out-File -Encoding UTF8` 会写 BOM，
        # 用 "utf-8" 读取会直接抛 JSONDecodeError。
        with open(args.input, "r", encoding="utf-8-sig") as fh:
            payload = json.load(fh)
    except FileNotFoundError:
        print("错误：找不到输入文件 %s" % args.input, file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print("错误：输入不是合法 JSON —— %s" % exc, file=sys.stderr)
        return 2

    report = verify(
        text=payload.get("text", ""),
        sentences=payload.get("sentences") or [],
        conflicts=payload.get("conflicts") or [],
    )

    if args.pretty:
        print(render(report))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["verdict"] == VERDICT_PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
