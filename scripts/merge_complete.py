#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FTM 完善轮（2026-09-12）八线检索结果合并脚本。

输入:
  基线: FTM_终极清单.json（156 条，2026-09-12 定稿）
  批次: ftm_完善_20260912/raw/w1..w8_*.json（8 个并行 worker 产出）

处理:
  1. 基线全部保留；
  2. 批次条目按 canonical 键去重（与 merge_final.py 相同口径）；
  3. 与基线 domain 集合比对 → 已存在则跳过（记 dup），新条目并入（known=false）；
  4. MTF 黑名单兜底过滤（worker 漏剔的）；
  5. 输出全量清单 + 完善报告。

输出（ftm_完善_20260912/）:
  ftm_complete.json  ftm_complete.md  ftm_complete.html  _完善报告.md
"""
import json
import os
import re
from collections import OrderedDict, Counter
from urllib.parse import urlparse

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUB = os.path.join(BASE, "ftm_完善_20260912")
RAW = os.path.join(SUB, "raw")

BASE_LIST = json.load(open(os.path.join(BASE, "FTM_终极清单.json"), encoding="utf-8"))

MTF_HOSTS = {
    "mtf.wiki", "vocal.mtf.wiki", "tfsci.mtf.wiki", "mtf.party", "mtf.report",
    "mtf.name", "luluv.wiki", "hrtyaku.com", "luoaowoo.cn",
    "kitsumio.github.io", "mtf-world.com", "transfemscience.org",
}
MTF_REPO_SUBSTR = [
    "project-trans/mtf-wiki", "project-trans/transfeminine-science",
    "trans-archive/jyosei-guide", "bbleae/hrt-book", "kitsumio/miomtfwiki",
    "next-mtf-wiki", "femboy-skill",
]
LOCALE_SEGS = {"zh", "zh-cn", "zh-hans", "zh-hant", "zh-tw", "cn", "en", "en-us", "ja", "ko"}

CAT_ORDER = ["知识库", "开源项目", "社区论坛", "社区组织", "医疗用药", "手术",
             "嗓音", "束胸假体", "工具", "个人站点", "导航", "其他"]
ZH_ORDER = ["原生中文", "中文版路径", "多语言含中文", "无中文", "未核实"]


def norm_host(url):
    try:
        h = urlparse(url).netloc.lower()
    except Exception:
        return ""
    return h[4:] if h.startswith("www.") else h


def norm_key(url):
    url = (url or "").strip()
    if "github.com" in url:
        m = re.search(r"github\.com/([^/]+)/([^/#?]+)", url)
        if m:
            return "gh:" + (m.group(1) + "/" + m.group(2)).lower()
    host = norm_host(url)
    path = urlparse(url).path.rstrip("/")
    segs = [s for s in path.split("/") if s]
    seg = ""
    for s in segs:
        if s.lower() not in LOCALE_SEGS:
            seg = s
            break
    return "web:" + host + ("/" + seg if seg else "")


def is_mtf(e):
    url = (e.get("url") or "").lower()
    if norm_host(e.get("url", "")) in MTF_HOSTS:
        return True
    return any(k in url for k in MTF_REPO_SUBSTR)


def zh_rank(z):
    return ZH_ORDER.index(z) if z in ZH_ORDER else len(ZH_ORDER)


def main():
    # 基线 156 条 → known 键集合
    base_keys = {norm_key(s["url"]) for s in BASE_LIST}
    base_doms = {s["domain"].lower() for s in BASE_LIST}

    merged = OrderedDict()
    for s in BASE_LIST:  # 基线全保留
        s = dict(s)
        s["known"] = True
        s["src"] = s.get("src", "基线")
        merged[norm_key(s["url"])] = s

    stat = []   # (file, n, dup, new, mtf)
    for fn in sorted(os.listdir(RAW)):
        if not fn.endswith(".json"):
            continue
        rows = json.load(open(os.path.join(RAW, fn), encoding="utf-8"))
        if isinstance(rows, dict):
            rows = rows.get("results") or rows.get("items") or []
        n = dup = new = mtf = 0
        for e in rows:
            if not isinstance(e, dict) or not e.get("url"):
                continue
            n += 1
            if is_mtf(e):
                mtf += 1
                continue
            k = norm_key(e["url"])
            if k in base_keys or k in merged:
                dup += 1
                continue
            dom = k.replace("gh:", "github.com/").replace("web:", "")
            if dom.lower() in base_doms:
                dup += 1
                continue
            rec = {
                "domain": dom,
                "url": e.get("url", "").strip(),
                "title": (e.get("title") or "").strip(),
                "category": e.get("category") or "其他",
                "zh": e.get("zh_support") if e.get("zh_support") in ZH_ORDER else "未核实",
                "zh_evidence": e.get("zh_evidence", ""),
                "status": e.get("status") or "待复核",
                "quality": e.get("quality") or "中",
                "lang": "",
                "summary": (e.get("summary") or "").strip(),
                "known": bool(e.get("known")),
                "src": "八线检索轮·" + fn.replace(".json", "").split("_", 1)[0],
            }
            merged[k] = rec
            new += 1
        stat.append((fn, n, dup, new, mtf))
        print("%-28s 输入 %d | 重复 %d | 新增 %d | MTF剔除 %d" % (fn, n, dup, new, mtf))

    sites = list(merged.values())
    # host 级去重：同一 host 多条（GitHub 除外，仓库按 owner/repo 区分）保留更优一条
    host_map = {}
    host_dup = 0
    for s in sites:
        if "github.com" in s["url"]:
            continue
        k = "host:" + norm_host(s["url"])
        if k not in host_map:
            host_map[k] = s
        else:
            old = host_map[k]

            def better(a, b):
                if zh_rank(a["zh"]) != zh_rank(b["zh"]):
                    return zh_rank(a["zh"]) < zh_rank(b["zh"])
                if (a.get("zh_evidence") or "") and not (b.get("zh_evidence") or ""):
                    return True
                if len(a.get("summary") or "") != len(b.get("summary") or ""):
                    return len(a["summary"]) > len(b["summary"])
                return len(a["url"]) >= len(b["url"])

            host_dup += 1
            if better(s, old):
                host_map[k] = s
    sites = [s for s in sites if "github.com" in s["url"] or s is host_map["host:" + norm_host(s["url"])]]
    print("host 级去重合并 %d 条" % host_dup)
    sites.sort(key=lambda x: (CAT_ORDER.index(x["category"]) if x["category"] in CAT_ORDER else 99,
                              ["在线", "待复核", "失效"].index(x["status"]) if x["status"] in ("在线", "待复核", "失效") else 1,
                              zh_rank(x["zh"])))

    n_new = sum(1 for s in sites if not s.get("known"))
    n_online = sum(1 for s in sites if s["status"] == "在线")
    n_zh = sum(1 for s in sites if s["zh"] in ("原生中文", "中文版路径", "多语言含中文"))
    n_pend = sum(1 for s in sites if s["status"] == "待复核")
    n_dead = sum(1 for s in sites if s["status"] == "失效")

    json.dump(sites, open(os.path.join(SUB, "ftm_complete.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    # ---- MD ----
    md = ["# FTM（跨性别男性）项目与网站 · 完善版清单\n",
          "> 定稿 2026-09-12（八线检索完善轮）｜ 共 **%d** 条（基线 156 + 新增 %d ｜ 在线 %d / 待复核 %d / 失效 %d ｜ 含中文 %d）\n"
          % (len(sites), n_new, n_online, n_pend, n_dead, n_zh),
          "> 口径：剔除 MTF 专属；8 个并行 worker 用 bing_search 分维度检索（知识库/开源/社区/医疗/手术/嗓音/束胸/中文专项），"
          "每个候选先找出来、再逐站复查中文支持（HTTP 实测 + CJK 占比）后由主进程合并去重。\n",
          "> 数据文件：`ftm_complete.json` ｜ 各 worker 批次：`raw/w1..w8_*.json`\n"]
    by_cat = {}
    for s in sites:
        by_cat.setdefault(s["category"], []).append(s)
    for cat in CAT_ORDER:
        items = by_cat.get(cat)
        if not items:
            continue
        md.append("\n## %s（%d）\n" % (cat, len(items)))
        for s in items:
            newtag = " 🆕" if not s.get("known") else ""
            flag = {"在线": "", "待复核": " ⚠️待复核", "失效": " ❌失效"}.get(s["status"], "")
            md.append("- [%s](%s) — **%s** ｜ `%s` ｜ %s%s%s"
                      % (s["title"], s["url"], s["zh"], s["quality"], s["src"], newtag, flag))
            if s["summary"]:
                md.append("  %s" % s["summary"])
            if s["zh_evidence"]:
                md.append("  中文实测：%s" % s["zh_evidence"])
    md.append("\n---\n## 本轮新增（known=false）%d 条\n" % n_new)
    for s in sites:
        if not s.get("known"):
            md.append("- [%s](%s) — %s ｜ %s ｜ %s ｜ %s"
                      % (s["title"], s["url"], s["category"], s["zh"], s["status"], s["quality"]))
    open(os.path.join(SUB, "ftm_complete.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")

    # ---- HTML（沿用终极清单样式）----
    def esc(t):
        return (t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    rows = []
    for s in sites:
        zh = s["zh"]
        cls = {"原生中文": "zh1", "中文版路径": "zh2", "多语言含中文": "zh3",
               "无中文": "zh4", "未核实": "zh5"}.get(zh, "zh5")
        st = s["status"]
        stcls = "ok" if st == "在线" else ("dead" if st == "失效" else "pend")
        newtag = '<span class="new">新增</span>' if not s.get("known") else ""
        rows.append(
            '<tr><td class="t"><a href="%s" target="_blank" rel="noopener">%s</a>%s</td>'
            '<td>%s</td><td><span class="cat">%s</span></td>'
            '<td><span class="zh %s">%s</span></td>'
            '<td class="ev">%s</td>'
            '<td><span class="src">%s</span></td>'
            '<td><span class="st %s">%s</span></td></tr>'
            % (esc(s["url"]), esc(s["title"]), newtag, esc(s["summary"]), esc(s["category"]),
               cls, zh, esc(s["zh_evidence"]), esc(s["src"]), stcls, st))
    css = """
:root{--bg:#f6f7f5;--card:#fff;--ink:#1b1f1a;--sub:#5c665c;--line:#e2e6e0;--acc:#4E9A4E;--new:#c2410c}
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
td.ev{color:var(--sub);font-size:12.5px;max-width:330px}
.cat{background:#eef1ec;border-radius:5px;padding:1px 7px;font-size:12px;color:#42503f;white-space:nowrap}
.zh{padding:1px 7px;border-radius:5px;font-size:12px;white-space:nowrap}
.zh1{background:#e3f2e3;color:#1e5c1e}
.zh2{background:#e8f0fa;color:#1e4a78}
.zh3{background:#f2ecfa;color:#523178}
.zh4{background:#f2f3f1;color:#6b736a}
.zh5{background:#fdf1e3;color:#8a5a12}
.src{background:#fff3d6;border-radius:5px;padding:1px 6px;font-size:11px;color:#7a5c10;white-space:nowrap}
.new{display:inline-block;margin-left:6px;font-size:10.5px;background:#fff1e7;color:var(--new);
  border:1px solid #f4c9ae;border-radius:5px;padding:0 5px;vertical-align:1px}
.st{font-size:12px}
.st.ok{color:var(--acc)}.st.dead{color:#b3261e}.st.pend{color:#8a5a12}
"""
    html = ("<!DOCTYPE html>\n<html lang=\"zh-CN\"><head><meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
            "<title>FTM 项目与网站 · 完善版清单</title>\n<style>" + css +
            "</style></head><body><div class=\"wrap\">\n"
            "<h1>FTM（跨性别男性）项目与网站 · 完善版清单</h1>\n"
            '<div class="meta">定稿 2026-09-12 ｜ 8 个并行 worker 用 bing_search 分维度检索，先找候选再逐站复查中文支持（HTTP 实测 + CJK 占比），主进程合并去重</div>\n'
            '<div class="stats">\n'
            '<div class="stat"><b>' + str(len(sites)) + '</b><span>收录总数</span></div>\n'
            '<div class="stat"><b>' + str(n_new) + '</b><span>本轮新增</span></div>\n'
            '<div class="stat"><b>' + str(n_online) + '</b><span>在线</span></div>\n'
            '<div class="stat"><b>' + str(n_pend) + '</b><span>待复核</span></div>\n'
            '<div class="stat"><b>' + str(n_dead) + '</b><span>失效</span></div>\n'
            '<div class="stat"><b>' + str(n_zh) + '</b><span>含中文</span></div>\n'
            '</div>\n'
            '<table><thead><tr><th>站点 / 项目</th><th>简介</th><th>分类</th><th>中文支持</th><th>中文实测证据</th><th>来源</th><th>状态</th></tr></thead>\n'
            "<tbody>" + "\n".join(rows) + "</tbody></table>\n"
            '</div></body></html>\n')
    open(os.path.join(SUB, "ftm_complete.html"), "w", encoding="utf-8").write(html)

    # ---- 报告 ----
    rep = ["# FTM 完善轮 · 合并报告（2026-09-12）\n",
           "\n基线：FTM_终极清单.json %d 条\n" % len(BASE_LIST),
           "\n## 各 worker 输入统计\n",
           "| 批次 | 输入 | 重复 | 新增 | MTF剔除 |\n| --- | --- | --- | --- | --- |\n"]
    for fn, n, dup, new, mtf in stat:
        rep.append("| %s | %d | %d | %d | %d |\n" % (fn, n, dup, new, mtf))
    rep.append("\n## 合并结果\n")
    rep.append("- 全量 %d 条（基线 %d + 新增 %d）\n" % (len(sites), len(BASE_LIST), n_new))
    rep.append("- 状态：在线 %d / 待复核 %d / 失效 %d\n" % (n_online, n_pend, n_dead))
    rep.append("- 含中文 %d 条\n" % n_zh)
    cat = Counter(s["category"] for s in sites if not s.get("known"))
    rep.append("- 新增分类分布：%s\n" % dict(cat))
    rep.append("- 新增中文分布：%s\n"
               % dict(Counter(s["zh"] for s in sites if not s.get("known"))))
    open(os.path.join(SUB, "_完善报告.md"), "w", encoding="utf-8").write("\n".join(rep) + "\n")

    print("\n=== 合计 %d 条（基线 %d + 新增 %d）在线 %d / 待复核 %d / 失效 %d / 含中文 %d ==="
          % (len(sites), len(BASE_LIST), n_new, n_online, n_pend, n_dead, n_zh))


if __name__ == "__main__":
    main()
