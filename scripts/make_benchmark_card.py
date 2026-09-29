#!/usr/bin/env python3
# make_benchmark_card.py —— 从 Tier-3 实测 JSON 生成跑分卡 HTML（零依赖，纯标准库）
# 用法: python make_benchmark_card.py --input results.json --out evidence/benchmark_card.html
# 铁律: 数据必须来自实测（BENCHMARK.md 同源）。缺字段即拒绝渲染（exit 2），禁止预填。

import argparse
import html
import json
import sys
from datetime import datetime, timezone, timedelta


def fail(msg):
    print("[refuse-to-render] %s" % msg, file=sys.stderr)
    sys.exit(2)


def load(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


REQUIRED = [
    "title", "subtitle", "date", "agent", "model_local", "model_cloud",
    "dims",  # {Security: {baseline, with_skill}, ...}
    "verdict",  # PASS / FAIL / 部分未跑
    "headline",  # [{label, value, note} x <=4]
    "honesty",  # [str] 已知局限与未跑项
]

DIM_CN = {
    "Security": "安全",
    "Correctness": "正确性",
    "Discoverability": "可发现性",
    "Effectiveness": "有效性",
    "Efficiency": "效率",
}


def esc(s):
    return html.escape(str(s))


def render(data):
    dims = data["dims"]
    rows = ""
    for k, cn in DIM_CN.items():
        if k not in dims:
            fail("缺少维度 %s" % k)
        d = dims[k]
        for col in ("baseline", "with_skill"):
            if col not in d or d[col] in (None, "", "待跑", "未跑"):
                fail("维度 %s 的 %s 缺实测值，禁止预填" % (k, col))
        diff = d.get("diff", "")
        rows += (
            "<tr><td>%s</td><td>%s</td><td>%s</td><td class='diff'>%s</td></tr>"
            % (esc(cn), esc(d["baseline"]), esc(d["with_skill"]), esc(diff))
        )
    heads = "".join(
        "<div class='metric'><div class='num'>%s</div><div class='lbl'>%s</div>"
        "<div class='note'>%s</div></div>"
        % (esc(h["value"]), esc(h["label"]), esc(h.get("note", "")))
        for h in data["headline"]
    )
    honesty = "".join("<li>%s</li>" % esc(x) for x in data["honesty"])
    return """<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"><title>%s</title>
<style>
body{margin:0;background:#f5efe2;color:#3a2e1f;font-family:"Microsoft YaHei",sans-serif;}
.card{width:1280px;margin:0 auto;padding:48px 64px;box-sizing:border-box;background:#f5efe2;}
.title{font-size:40px;font-weight:700;letter-spacing:2px;}
.sub{font-size:20px;color:#8a6d3b;margin-top:8px;}
.metrics{display:flex;gap:24px;margin:28px 0;}
.metric{flex:1;background:#fffdf7;border:1px solid #d9c9a8;border-radius:12px;padding:20px;text-align:center;}
.metric .num{font-size:44px;font-weight:700;color:#7a5c1e;}
.metric .lbl{font-size:18px;margin-top:6px;}
.metric .note{font-size:13px;color:#9a8a6a;margin-top:4px;}
table{width:100%%;border-collapse:collapse;background:#fffdf7;border-radius:12px;overflow:hidden;}
th,td{border:1px solid #d9c9a8;padding:12px 16px;font-size:18px;text-align:center;}
th{background:#e8dcc2;}
td.diff{font-weight:700;color:#1a6b4f;}
.verdict{font-size:22px;margin-top:20px;}
.verdict b{color:#1a6b4f;}
.honesty{margin-top:16px;font-size:14px;color:#6b5d44;padding-left:20px;}
.foot{margin-top:24px;font-size:13px;color:#9a8a6a;}
</style></head><body><div class="card">
<div class="title">%s</div>
<div class="sub">%s</div>
<div class="metrics">%s</div>
<table><tr><th>维度</th><th>baseline（不带 skill）</th><th>with skill</th><th>差值</th></tr>%s</table>
<div class="verdict">总体结论：<b>%s</b></div>
<ul class="honesty">%s</ul>
<div class="foot">本卡由 scripts/make_benchmark_card.py 从 results.json 生成 · 评测日期 %s · Agent %s · 模型：本地 %s / 云端 %s · 数据同源 BENCHMARK.md，未经手改。</div>
</div></body></html>""" % (
        esc(data["title"]), esc(data["title"]), esc(data["subtitle"]), heads, rows,
        esc(data["verdict"]), honesty, esc(data["date"]), esc(data["agent"]),
        esc(data["model_local"]), esc(data["model_cloud"]),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", "-i", required=True)
    ap.add_argument("--out", "-o", default="evidence/benchmark_card.html")
    args = ap.parse_args()
    data = load(args.input)
    for k in REQUIRED:
        if k not in data:
            fail("缺少字段 %s" % k)
    if data["verdict"] in ("", "待跑", None):
        fail("verdict 未跑，禁止预填")
    html_out = render(data)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html_out)
    print("OK -> %s" % args.out)


if __name__ == "__main__":
    main()
