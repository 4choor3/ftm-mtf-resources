#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一清单渲染器：为 FTM/MTF 数据集生成结构一致的 Markdown 与自包含 HTML 清单。

用法:
    python3 render_lists.py data.json "页面标题" "口径说明" lists/out.md lists/out.html

两侧字段差异自动兼容:
- 分类: MTF 侧真分类在 subcategory（category 为取向标签），FTM 侧在 category
- 中文支持: zh 布尔字段 / zh_evidence / lang 前缀，逐级回退
"""
import json
import sys
from collections import OrderedDict
from html import escape

PSEUDO_CATEGORIES = {"跨性别男性", "跨性别女性", "跨性别"}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def bucket(item):
    """返回条目的真实分类名。"""
    sub = (item.get("subcategory") or "").strip()
    cat = (item.get("category") or "").strip()
    if sub:
        return sub
    if cat and cat not in PSEUDO_CATEGORIES:
        return cat
    return "其他"


def zh_state(item):
    """返回 (含中文?, 证据)。"""
    zh = item.get("zh")
    lang = (item.get("lang") or "").strip().lower()
    if zh is True:
        return True, item.get("zh_evidence") or ""
    if zh is False:
        return False, item.get("zh_evidence") or ""
    if lang.startswith("zh"):
        return True, "条目语种为中文"
    return False, ""


def status_of(item):
    return (item.get("status") or "未知").strip()


def stats(items):
    st = {"在线": 0, "待复核": 0, "失效": 0, "未知": 0}
    zh_cnt = 0
    for it in items:
        s = status_of(it)
        st[s if s in st else "未知"] += 1
        if zh_state(it)[0]:
            zh_cnt += 1
    return st, zh_cnt


def group(items):
    g = OrderedDict()
    for it in items:
        g.setdefault(bucket(it), []).append(it)
    return g


def render_md(items, title, note):
    st, zh_cnt = stats(items)
    lines = [
        f"# {title}",
        "",
        f"> 共 **{len(items)}** 条 ｜ 在线 {st['在线']} ｜ 待复核 {st['待复核']} ｜ 失效 {st['失效']} ｜ 含中文 {zh_cnt}",
        "",
    ]
    if note:
        lines += [f"> 口径：{note}", ""]
    for cat, lst in group(items).items():
        lines.append(f"## {cat}（{len(lst)}）")
        lines.append("")
        for it in lst:
            title_ = (it.get("title") or it.get("domain") or "未命名").replace("[", "（").replace("]", "）")
            url = it.get("url") or f"https://{it.get('domain','')}"
            dom = it.get("domain") or ""
            mark = "含中文" if zh_state(it)[0] else ""
            line = f"- [{title_}]({url}) `{dom}` ｜ {status_of(it)}"
            if mark:
                line += f" ｜ {mark}"
            lines.append(line)
            summary = (it.get("summary") or "").strip()
            if summary:
                lines.append(f"  - {summary}")
        lines.append("")
    return "\n".join(lines)


CSS = """body{font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;max-width:1080px;margin:0 auto;padding:32px 24px;color:#24292f;background:#fff;line-height:1.6}
h1{font-size:26px;border-bottom:2px solid #2f6f3f;padding-bottom:10px}
.meta{display:flex;gap:12px;flex-wrap:wrap;margin:16px 0}
.meta span{background:#eef5ee;border:1px solid #cfe3cf;border-radius:6px;padding:4px 12px;font-size:14px}
.note{color:#57606a;font-size:14px;margin-bottom:20px}
h2{font-size:19px;margin:28px 0 10px;color:#2f6f3f}
table{width:100%;border-collapse:collapse;font-size:14px}
th{background:#f3f7f3;text-align:left;padding:8px 10px;border:1px solid #dde5dd;white-space:nowrap}
td{padding:8px 10px;border:1px solid #e6ebe6;vertical-align:top}
td a{color:#1a5c2a;text-decoration:none;font-weight:600}
td a:hover{text-decoration:underline}
.dom{color:#8b949e;font-size:12px;white-space:nowrap}
.st{white-space:nowrap;font-size:13px}
.zh{white-space:nowrap;font-size:13px;color:#1a5c2a;font-weight:600}
.sum{color:#57606a;font-size:13px}
footer{margin-top:28px;color:#8b949e;font-size:12px}"""


def render_html(items, title, note):
    st, zh_cnt = stats(items)
    parts = [
        "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        f"<title>{escape(title)}</title><style>{CSS}</style></head><body>",
        f"<h1>{escape(title)}</h1>",
        "<div class='meta'>",
        f"<span>共 {len(items)} 条</span><span>在线 {st['在线']}</span><span>待复核 {st['待复核']}</span>"
        f"<span>失效 {st['失效']}</span><span>含中文 {zh_cnt}</span>",
        "</div>",
        f"<p class='note'>{escape(note)}</p>",
    ]
    for cat, lst in group(items).items():
        parts.append(f"<h2>{escape(cat)}（{len(lst)}）</h2><table><tr><th>#</th><th>站点</th><th>域名</th><th>状态</th><th>中文</th><th>摘要</th></tr>")
        for i, it in enumerate(lst, 1):
            title_ = escape(it.get("title") or it.get("domain") or "未命名")
            url = escape(it.get("url") or f"https://{it.get('domain','')}", quote=True)
            dom = escape(it.get("domain") or "")
            s = escape(status_of(it))
            has_zh, _ = zh_state(it)
            zh_s = "含中文" if has_zh else "—"
            summary = escape((it.get("summary") or "").strip()[:120])
            parts.append(
                f"<tr><td>{i}</td><td class='st'><a href='{url}' target='_blank' rel='noopener'>{title_}</a></td>"
                f"<td class='dom'>{dom}</td><td class='st'>{s}</td><td class='zh'>{zh_s}</td><td class='sum'>{summary}</td></tr>"
            )
        parts.append("</table>")
    parts.append("<footer>有效性为收录时（2026-09）实测状态，仅索引第三方公开站点，不构成医疗建议。</footer></body></html>")
    return "\n".join(parts)


def main():
    if len(sys.argv) != 6:
        print(__doc__)
        sys.exit(1)
    data_path, title, note, md_path, html_path = sys.argv[1:6]
    items = load(data_path)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_md(items, title, note))
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(render_html(items, title, note))
    print(f"{data_path}: {len(items)} 条 -> {md_path}, {html_path}")


if __name__ == "__main__":
    main()
