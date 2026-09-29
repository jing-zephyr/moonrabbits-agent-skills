#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kb_search.py —— 「展品叙事官」的知识库检索脚本（只从库取事实）

归属：skill `exhibit-narrative`（原 artifact-narrative）
状态：⚠️ 待应用草案 —— 位于 DeepSeek 过程库，尚未拷入 skills-src。

这个脚本存在的意义，是让 SKILL.md 里那句硬约束**可执行**：
    硬约束 1：每一句必须有出处；检索不到 → 明确说「知识库未找到」，绝不编造（fail-closed）

所以它的设计目标不是"尽量返回点什么"，而是**在证据不足时干净地返回空**，
把"要不要编"这个决定权，从模型手里拿走。

设计原则：
  1. **只读**：不写入、不修改、不删除知识库任何内容
  2. **fail-closed**：证据分低于阈值就返回 found=false，绝不"凑数"
  3. **可降级**：ChromaDB 不可用时返回明确错误，不静默返回空（静默空会被误读为"库里没有"）
  4. **不打印密钥**：不输出任何连接串、token、绝对路径以外的环境信息
  5. **确定性**：同一查询同一排序（按 score 降序，score 相同按 id 升序）

依赖（仅检索时需要，本文件 import 时不强制）：
  pip install chromadb sentence-transformers
  嵌入模型：BAAI/bge-large-zh-v1.5（1024 维）
  ⚠️ 查询必须用与入库**同一个**嵌入模型，否则检索整体失效（见 03-项目脉络）

用法：
  # CLI
  python kb_search.py --query "德化白瓷 何朝宗" [--top-k 5] [--min-score 0.6] [--json]

  # 作为模块
  from kb_search import search
  result = search("德化白瓷 何朝宗", top_k=5, min_score=0.6)
  if not result["found"]:
      ...  # 走 fail-closed 拒答分支，绝不编造
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

# --- Windows 控制台兼容（与 verify_sources.py 同一处理，理由见该文件注释）---
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

# ---------------------------------------------------------------------------
# 默认配置 —— 与 03-项目脉络.md 记录的实际部署保持一致
# ---------------------------------------------------------------------------
DEFAULT_COLLECTION = os.environ.get("KB_COLLECTION", "moon_rabbits_kb")
DEFAULT_EMBED_MODEL = os.environ.get("KB_EMBED_MODEL", "BAAI/bge-large-zh-v1.5")
DEFAULT_PERSIST_DIR = os.environ.get("KB_PERSIST_DIR", "").strip()
DEFAULT_TOP_K = 5
DEFAULT_MIN_SCORE = 0.6          # 与 verify_sources.py 的 EVIDENCE_THRESHOLD 同源

# 已知的库规模基线（用于自检：条数对不上说明连错了库）
EXPECTED_ENTRY_COUNT = 45225


class KnowledgeBaseUnavailable(RuntimeError):
    """
    知识库不可用。

    单独定义异常类型，是为了让调用方**能区分两种情况**：
      · 库里确实没有这条 → search() 返回 found=False（正常的 fail-closed）
      · 库压根连不上     → 抛这个异常（环境故障，必须显式暴露）
    这两件事被混淆，是"静默幻觉"最常见的来源。
    """


def _load_backend(persist_dir: Optional[str]):
    """惰性加载 ChromaDB；不可用时抛 KnowledgeBaseUnavailable（不静默降级）。"""
    try:
        import chromadb  # type: ignore
    except ImportError as exc:
        raise KnowledgeBaseUnavailable(
            "未安装 chromadb。检索需要：pip install chromadb sentence-transformers"
        ) from exc

    try:
        if persist_dir:
            client = chromadb.PersistentClient(path=persist_dir)
        else:
            client = chromadb.PersistentClient()
        return client
    except Exception as exc:                      # noqa: BLE001 — 需要把原始原因透出
        raise KnowledgeBaseUnavailable(
            "无法打开 ChromaDB（persist_dir=%r）：%s" % (persist_dir, exc)
        ) from exc


def _embed_query(query: str, model_name: str) -> List[float]:
    """用与入库相同的模型编码查询。绝不复用其他模型的向量。"""
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
    except ImportError as exc:
        raise KnowledgeBaseUnavailable(
            "未安装 sentence-transformers，无法编码查询。"
            "注意：查询必须用与入库同一个嵌入模型（%s）。" % model_name
        ) from exc

    try:
        model = SentenceTransformer(model_name)
        vector = model.encode([query], normalize_embeddings=True)[0]
        return [float(x) for x in vector]
    except Exception as exc:                      # noqa: BLE001
        raise KnowledgeBaseUnavailable(
            "嵌入模型 %s 加载或编码失败：%s" % (model_name, exc)
        ) from exc


def search(query: str,
           top_k: int = DEFAULT_TOP_K,
           min_score: float = DEFAULT_MIN_SCORE,
           collection: str = DEFAULT_COLLECTION,
           persist_dir: Optional[str] = DEFAULT_PERSIST_DIR or None,
           embed_model: str = DEFAULT_EMBED_MODEL) -> Dict[str, Any]:
    """
    在知识库里检索与 query 相关的条目。

    返回（无论命中与否，结构一致 —— 便于上游统一处理）：
      {
        "found": bool,               # False 时上游必须走 fail-closed 分支
        "query": str,
        "hits": [ {id, text, score, metadata}, ... ],
        "max_score": float,
        "reason": str,               # found=False 时说明为什么
        "thresholds": {"min_score":..., "top_k":...},
        "backend": {"collection":..., "embed_model":..., "persist_dir":...}
      }

    ⚠️ found=False 是**正常结果**，不是错误。
       上游拿到 found=False 时的正确反应是「明确说知识库未找到」，
       **不是**换一种问法反复搜，**更不是**凭记忆作答。
    """
    query = (query or "").strip()
    backend_info = {
        "collection": collection,
        "embed_model": embed_model,
        "persist_dir": persist_dir or "(default)",
    }

    if not query:
        return {
            "found": False, "query": query, "hits": [], "max_score": 0.0,
            "reason": "查询为空", "thresholds": {"min_score": min_score, "top_k": top_k},
            "backend": backend_info,
        }

    client = _load_backend(persist_dir)
    try:
        col = client.get_collection(name=collection)
    except Exception as exc:                      # noqa: BLE001
        raise KnowledgeBaseUnavailable(
            "集合 %r 不存在或无法打开：%s" % (collection, exc)
        ) from exc

    vector = _embed_query(query, embed_model)

    try:
        raw = col.query(query_embeddings=[vector],
                        n_results=max(1, int(top_k)),
                        include=["documents", "metadatas", "distances"])
    except Exception as exc:                      # noqa: BLE001
        raise KnowledgeBaseUnavailable("检索失败：%s" % exc) from exc

    ids = (raw.get("ids") or [[]])[0]
    docs = (raw.get("documents") or [[]])[0]
    metas = (raw.get("metadatas") or [[]])[0]
    dists = (raw.get("distances") or [[]])[0]

    hits: List[Dict[str, Any]] = []
    for i, doc_id in enumerate(ids):
        distance = dists[i] if i < len(dists) else None
        # 归一化向量 + 默认 l2 距离时，score = 1 - distance/2 落在 [0,1]。
        # 若库侧用的是 cosine 距离，则 score = 1 - distance。两者都做兜底。
        score = 0.0
        if isinstance(distance, (int, float)):
            score = 1.0 - (distance / 2.0) if distance > 1.0 else 1.0 - distance
            score = max(0.0, min(1.0, score))

        hits.append({
            "id": doc_id,
            "text": docs[i] if i < len(docs) else "",
            "score": round(score, 4),
            "metadata": metas[i] if i < len(metas) else {},
        })

    # 确定性排序：score 降序，同分按 id 升序
    hits.sort(key=lambda h: (-h["score"], str(h["id"])))

    kept = [h for h in hits if h["score"] >= min_score]
    max_score = max([h["score"] for h in hits], default=0.0)

    if kept:
        return {
            "found": True, "query": query, "hits": kept, "max_score": max_score,
            "reason": "命中 %d 条（阈值 %.2f）" % (len(kept), min_score),
            "thresholds": {"min_score": min_score, "top_k": top_k},
            "backend": backend_info,
        }

    return {
        "found": False, "query": query, "hits": [], "max_score": max_score,
        "reason": ("未命中：最高分 %.4f 低于阈值 %.2f —— "
                   "**必须明确告知「知识库未找到」，绝不编造**"
                   % (max_score, min_score)),
        "thresholds": {"min_score": min_score, "top_k": top_k},
        "backend": backend_info,
    }


def flat_search(query: str,
                flat_source: str,
                top_k: int = DEFAULT_TOP_K,
                min_score: float = DEFAULT_MIN_SCORE) -> Dict[str, Any]:
    """
    平面关键词检索（降级模式）：不依赖 chromadb / 向量模型，纯标准库流式读 jsonl。
    质量低于向量检索，仅用于环境降级与快速自检；结果里显式标注 mode。
    铁律：不 dump 条目原始元数据（知识库配置曾有过明文密钥的教训），
          只返回 text 与 entry_index。
    """
    query = (query or "").strip()
    backend_info = {
        "mode": "flat-keyword",
        "source": os.path.basename(flat_source),
        "embed_model": "(none)",
        "note": "平面关键词检索为降级模式：得分与向量得分不可直接比较；正式检索应使用向量后端。",
    }
    if not query:
        return {"found": False, "query": query, "hits": [], "max_score": 0.0,
                "reason": "查询为空",
                "thresholds": {"min_score": min_score, "top_k": top_k},
                "backend": backend_info}
    if not os.path.exists(flat_source):
        raise KnowledgeBaseUnavailable(
            "平面语料不存在：%s" % os.path.basename(flat_source))

    # 词元：空格分词 + 中文双字窗口，去重保序
    tokens = [t for t in re.split(r"\s+", query) if t]
    bigrams = sorted({query[i:i + 2] for i in range(len(query) - 1)})
    terms = list(dict.fromkeys(tokens + bigrams))

    scored: List[Dict[str, Any]] = []
    try:
        with open(flat_source, "r", encoding="utf-8-sig", errors="replace") as fh:
            for idx, line in enumerate(fh):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                text = ""
                if isinstance(obj, dict):
                    text = (obj.get("text") or obj.get("content")
                            or obj.get("document") or "")
                    if not text:
                        text = " ".join(str(v) for v in obj.values()
                                        if isinstance(v, (str, int, float)))[:2000]
                else:
                    text = str(obj)
                if not text:
                    continue
                score = sum(1.0 for t in terms if t and t in text) / max(1, len(terms))
                if score > 0:
                    scored.append({
                        "id": str(idx),
                        "text": text[:500],
                        "score": round(score, 4),
                        "metadata": {"entry_index": idx},
                    })
    except OSError as exc:
        raise KnowledgeBaseUnavailable("读取平面语料失败：%s" % exc) from exc

    scored.sort(key=lambda h: (-h["score"], int(h["id"]), h["text"]))
    kept = [h for h in scored if h["score"] >= min_score][:max(1, int(top_k))]
    max_score = max([h["score"] for h in scored], default=0.0)

    if kept:
        return {
            "found": True, "query": query, "hits": kept, "max_score": max_score,
            "reason": "平面检索命中 %d 条（阈值 %.2f，降级模式）" % (len(kept), min_score),
            "thresholds": {"min_score": min_score, "top_k": top_k},
            "backend": backend_info,
        }
    return {
        "found": False, "query": query, "hits": [], "max_score": max_score,
        "reason": ("未命中：最高分 %.4f 低于阈值 %.2f —— "
                   "**必须明确告知「知识库未找到」，绝不编造**"
                   % (max_score, min_score)),
        "thresholds": {"min_score": min_score, "top_k": top_k},
        "backend": backend_info,
    }


def self_check(persist_dir: Optional[str] = None,
               collection: str = DEFAULT_COLLECTION) -> Dict[str, Any]:
    """
    自检：确认连上的是**正确的那个库**。

    只报告条数是否落在预期基线附近，不 dump 任何条目内容、不打印任何密钥。
    """
    result: Dict[str, Any] = {
        "collection": collection,
        "expected_entries": EXPECTED_ENTRY_COUNT,
        "ok": False,
    }
    try:
        client = _load_backend(persist_dir)
        col = client.get_collection(name=collection)
        count = col.count()
        result["entries"] = count
        result["within_10pct_of_expected"] = (
            abs(count - EXPECTED_ENTRY_COUNT) <= EXPECTED_ENTRY_COUNT * 0.10
        )
        result["ok"] = bool(result["within_10pct_of_expected"])
        if not result["ok"]:
            result["warning"] = (
                "条数与基线 %d 相差超过 10%% —— 可能连错了库，请先确认。"
                % EXPECTED_ENTRY_COUNT
            )
    except KnowledgeBaseUnavailable as exc:
        result["error"] = str(exc)
    return result


def _main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="知识库检索（只读 / fail-closed / 可降级）")
    parser.add_argument("--query", "-q", help="查询文本")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--min-score", type=float, default=DEFAULT_MIN_SCORE)
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument("--persist-dir", default=DEFAULT_PERSIST_DIR or None)
    parser.add_argument("--embed-model", default=DEFAULT_EMBED_MODEL)
    parser.add_argument("--flat-source", default=None,
                        help="平面 jsonl 语料路径（降级模式，不依赖 chromadb/向量模型）")
    parser.add_argument("--json", action="store_true", help="输出原始 JSON")
    parser.add_argument("--self-check", action="store_true",
                        help="只做连通性与规模自检，不检索")
    args = parser.parse_args(argv)

    try:
        if args.self_check:
            report = self_check(args.persist_dir, args.collection)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report.get("ok") else 1

        if not args.query:
            parser.error("需要 --query，或使用 --self-check")

        if args.flat_source:
            result = flat_search(args.query, args.flat_source,
                                 top_k=args.top_k, min_score=args.min_score)
        else:
            result = search(args.query,
                            top_k=args.top_k,
                            min_score=args.min_score,
                            collection=args.collection,
                            persist_dir=args.persist_dir,
                            embed_model=args.embed_model)
    except KnowledgeBaseUnavailable as exc:
        # 环境故障必须显式暴露，绝不伪装成"库里没有"
        print("知识库不可用：%s" % exc, file=sys.stderr)
        return 3

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result["found"]:
            print("命中 %d 条（最高分 %.4f）" % (len(result["hits"]), result["max_score"]))
            for h in result["hits"]:
                print("  · [%.4f] %s  %s"
                      % (h["score"], h["id"], (h["text"] or "")[:80].replace("\n", " ")))
        else:
            print("知识库未找到。")
            print("  %s" % result["reason"])
    return 0 if result["found"] else 1


if __name__ == "__main__":
    raise SystemExit(_main())
