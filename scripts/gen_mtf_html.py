#!/usr/bin/env python3
"""从 mtf/mtf_sources.json（精选主表）生成自包含单文件 HTML 清单。
风格对齐 FTM_终极清单.html：绿色主题 + 统计卡片 + 分类表格 + 中文标签。
只操作 mtf/ 目录内文件。
"""
import html
import json
import os
from collections import Counter
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))     # mtf/mtf_完善_20260912
MTF_DIR = os.path.dirname(BASE)                        # mtf/
MAIN = os.path.join(MTF_DIR, "mtf_sources.json")
OUT = os.path.join(MTF_DIR, "MTF_清单_网友自制精选.html")

CSS = """
:root{--bg:#f6f7f5;--card:#fff;--ink:#1b1f1a;--sub:#5c665c;--line:#e2e6e0;--acc:#4E9A4E}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.65 -apple-system,"PingFang SC","Helvetica Neue",sans-serif}
.wrap{max-width:1280px;margin:0 auto;padding:32px 20px 64px}
h1{font-size:24px;margin:0 0 6px}
.meta{color:var(--sub);font-size:13px;margin-bottom:20px}
.stats{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:22px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 16px}
.stat b{display:block;font-size:20px;color:var(--acc)}
.stat span{font-size:12px;color:var(--sub)}
table{width:100%;border-collapse:collapse;background:var(--card);
  border:1px solid var(--line);border-radius:12px;overflow:hidden}
th,td{padding:11px 12px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line);font-size:13.5px}
th{background:#eef1ec;font-weight:600;font-size:12.5px;color:#374237;position:sticky;top:0}
tr:last-child td{border-bottom:none}
td.t{min-width:190px;font-weight:600}
td.t a{color:#1a4d1a;text-decoration:none;border-bottom:1px solid #cfe0cf}
td.t a:hover{color:var(--acc)}
td.d{max-width:400px}
td.ev{color:var(--sub);font-size:12.5px;max-width:330px}
.cat{background:#eef1ec;border-radius:5px;padding:1px 7px;font-size:12px;color:#42503f;white-space:nowrap}
.zh{padding:1px 7px;border-radius:5px;font-size:12px;white-space:nowrap}
.zh1{background:#e3f2e3;color:#1e5c1e}
.zh2{background:#e8f0fa;color:#1e4a78}
.zh4{background:#f2f3f1;color:#6b736a}
.q{font-size:12px}
.q.h{color:var(--acc);font-weight:600}
.q.m{color:#8a5a12}
.q.l{color:#6b736a}
.st{font-size:12px}
.st.ok{color:var(--acc)}.st.dead{color:#b3261e}.st.pend{color:#8a5a12}
.src{background:#fff3d6;border-radius:5px;padding:1px 6px;font-size:11px;color:#7a5c10;white-space:nowrap}
"""

SRC_NAME = {"bing": "必应检索", "github_api": "GitHub 挖掘", "brave": "Brave 检索"}
SUBCAT_ORDER = ["知识站点", "医疗与政策", "社区与组织", "法律权益", "开源项目", "工具与服务"]


def esc(s):
    return html.escape(str(s or ""), quote=True)


def zh_badge(r):
    zh, lang = r.get("zh"), (r.get("lang") or "").lower()
    if zh and lang.startswith("zh"):
        return '<span class="zh zh1">原生中文</span>'
    if zh:
        return '<span class="zh zh2">中文可用</span>'
    return '<span class="zh zh4">无中文</span>'


def q_badge(r):
    q = r.get("quality", "")
    cls = {"高": "h", "中": "m", "低": "l"}.get(q, "l")
    return f'<span class="q {cls}">{esc(q)}</span>'


def st_badge(r):
    s = r.get("status", "")
    cls = {"在线": "ok", "失效": "dead"}.get(s, "pend")
    return f'<span class="st {cls}">{esc(s)}</span>'


def main():
    rows = json.load(open(MAIN, encoding="utf-8"))
    today = datetime.now().strftime("%Y-%m-%d")
    zh_n = sum(1 for r in rows if r.get("zh"))
    online = sum(1 for r in rows if r.get("status") == "在线")
    pend = sum(1 for r in rows if r.get("status") == "待复核")

    # 分组排序
    groups = {}
    for sub in SUBCAT_ORDER:
        groups[sub] = [r for r in rows if r.get("subcategory") == sub]
    groups["其他"] = [r for r in rows if r.get("subcategory") not in SUBCAT_ORDER]

    trs = []
    for sub, items in groups.items():
        if not items:
            continue
        for r in items:
            src = SRC_NAME.get(r.get("source", ""), esc(r.get("source", "")))
            ev = r.get("zh_evidence") or ""
            trs.append(
                f'<tr><td class="t"><a href="{esc(r.get("url"))}" target="_blank" rel="noopener">'
                f'{esc(r.get("title"))}</a><br><span style="font-weight:400;font-size:12px;color:#8a938a">'
                f'{esc(r.get("domain"))}</span></td>'
                f'<td class="d">{esc(r.get("summary"))}</td>'
                f'<td><span class="cat">{esc(sub)}</span></td>'
                f'<td>{zh_badge(r)}</td>'
                f'<td>{q_badge(r)}</td>'
                f'<td class="ev">{esc(ev)}</td>'
                f'<td>{st_badge(r)}</td></tr>'
            )

    page = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MTF 项目与网站 · 网友自制精选清单</title>
<style>{CSS}</style></head><body><div class="wrap">
<h1>MTF（跨性别女性）项目与网站 · 网友自制精选清单</h1>
<div class="meta">更新 {today} ｜ 从 243 条全量两轮精选：仅保留网友自制/社区自建、支持中文、可读性高的 MTF 项目与站点（wiki、博客、论坛、GitHub 项目）；官方机构、商业医院、商店、百科与英文站已全部剔除 ｜ 中文判定为 curl 实测 CJK 占比</div>
<div class="stats">
<div class="stat"><b>{len(rows)}</b><span>收录总数</span></div>
<div class="stat"><b>{online}</b><span>在线</span></div>
<div class="stat"><b>{pend}</b><span>待复核</span></div>
<div class="stat"><b>{zh_n}</b><span>支持中文</span></div>
</div>
<table><thead><tr><th>站点 / 项目</th><th>简介</th><th>分类</th><th>中文支持</th><th>质量</th><th>中文实测证据</th><th>状态</th></tr></thead>
<tbody>{''.join(trs)}</tbody></table>
</div></body></html>
"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"已写 {OUT} 共 {len(rows)} 条，{len(page)} 字节")


if __name__ == "__main__":
    main()
