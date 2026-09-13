#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合并三套 FTM 数据集 → 终极清单（2026-09-12 定稿）。

口径（用户最终指令）：
  1. 只要 FTM（跨性别男性），MTF 专属条目剔除；
  2. 三套数据集（主表 85 / Bing 检索轮 89 / 中文自建 57）按 canonical 键合并去重；
  3. 状态以 2026-09-12 最新实测裁决为准（冲突域名逐站重测过）。

输入:
  ftm/ftm_sources.json                    主表 85 条
  ftm/ftm_bing_20260911/ftm_sites.json    Bing 检索轮 89 条
  ftm/_backup_ftm/_misc/ftm_zh_final.json 中文自建 57 条

输出（工作区根目录）:
  FTM_终极清单.json  FTM_终极清单.md  FTM_终极清单.html
"""
import json
import os
import re
from collections import OrderedDict
from urllib.parse import urlparse

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERDICT_DATE = "2026-09-12"

MAIN = json.load(open(os.path.join(BASE, "ftm", "ftm_sources.json"), encoding="utf-8"))
BING = json.load(open(os.path.join(BASE, "ftm", "ftm_bing_20260911", "ftm_sites.json"), encoding="utf-8"))
ZHF = json.load(open(os.path.join(BASE, "ftm", "_backup_ftm", "_misc", "ftm_zh_final.json"), encoding="utf-8"))

# ---- MTF 剔除黑名单（沿用 Bing 轮 merge.py，并补齐 zh_final 中已知 MTF 条目）----
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

# ---- 状态裁决表：2026-09-12 实测（curl 直连 + 代理 7897 + DNS 三源）----
VERDICT = {
    "underworks.com": "在线",        # 200（curl 复活属实）
    "2345.lgbt": "在线",             # 根 404，/zh-cn/ 200 → 入口改 /zh-cn/
    "ftm-guide.com": "在线",         # 200
    "transcare.ucsf.edu": "在线",    # 代理下 403 = Akamai WAF 拦截，站点存活
    "transchinese.org": "待复核",    # 双通道 000，DNS 有 A 记录
    "ftmmagazine.com": "待复核",     # 双通道 000，DNS 有 A 记录
    "docs.hrt.guide": "失效",        # 000 + DNS 无记录
    "teamhk.org": "失效",            # 526 SSL 证书失效复现
    "ftmi.org": "失效",              # 000 + DNS 空（SERVFAIL）
    "agender.org.au": "失效",        # 历史三源 DNS 定案 NXDOMAIN
    "radremedy.org": "失效",         # 历史无 A 记录
    "hrt.guide": "失效",             # 历史：已变 ExpiredDomains 停放页
}
VERDICT_URL = {"2345.lgbt": "https://2345.lgbt/zh-cn/"}

# ---- 语言路径归一化（与 Bing 轮 merge.py 一致）----
LOCALE_SEGS = {"zh", "zh-cn", "zh-hans", "zh-hant", "zh-tw", "cn", "en", "en-us", "ja", "ko"}


def norm_host(url):
    try:
        h = urlparse(url).netloc.lower()
    except Exception:
        return ""
    return h[4:] if h.startswith("www.") else h


def norm_key(url):
    """canonical 去重键：github 用 owner/repo，否则 host+首个非语言路径段。"""
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
    host = norm_host(e.get("url", ""))
    if host in MTF_HOSTS:
        return True
    if any(k in url for k in MTF_REPO_SUBSTR):
        return True
    return False


# ---- 分类映射：主表/zh_final 的体系 → Bing 12 类体系 ----
CAT_MAP = {
    "医疗与政策": "医疗用药", "医疗与用药": "医疗用药",
    "知识站点": "知识库",
    "社区与组织": "社区组织",
    "开源项目": "开源项目",
    "工具与服务": "工具", "工具": "工具",
    "性别认同": "知识库",
    "已失效": "其他",
}
CAT_ORDER = ["知识库", "开源项目", "社区论坛", "社区组织", "医疗用药", "手术",
             "嗓音", "束胸假体", "工具", "个人站点", "导航", "其他"]
# domain 级分类归位（合并后仍落"其他"的少数条目）
CAT_OVERRIDE = {
    "genderswap.fm": "工具",
    "kydecker/genderswap.fm": "工具",
    "fanshan.org": "社区组织",
    "trans.lgbt": "导航",
    "docs.transonline.org.cn": "知识库",
}
ZH_ORDER = ["原生中文", "中文版路径", "多语言含中文", "无中文", "未核实"]


def zh_of(e, src):
    if src == "Bing检索轮":
        z = e.get("zh_support")
        return z if z in ZH_ORDER else "未核实"
    lang = (e.get("lang") or "").lower()
    if lang in ("zh", "zh-hant", "zh-hans", "zh-tw"):
        return "原生中文"
    if src == "中文自建":
        return "中文版路径" if e.get("note") or lang in ("en",) else "原生中文"
    return "无中文" if lang else "未核实"


def zh_rank(z):
    return ZH_ORDER.index(z) if z in ZH_ORDER else len(ZH_ORDER)


def score(rec):
    s = 0
    if rec.get("zh_evidence"):
        s += 6
    if rec.get("summary"):
        s += 2
    s += len(ZH_ORDER) - zh_rank(rec["zh"])
    # 来源优先级：主表（含机构核对）≥ Bing（最新实测）> 中文自建
    if "主表" in rec["src"]:
        s += 3
    if "Bing" in rec["src"]:
        s += 2
    q = {"高": 3, "中": 2, "低": 1}.get(rec.get("quality"), 0)
    s += q
    return s


def ingest(rows, src, merged, dropped):
    for e in rows:
        if not isinstance(e, dict) or not e.get("url"):
            continue
        if is_mtf(e):
            dropped["MTF剔除"].append((e.get("domain") or norm_host(e.get("url", "")), src))
            continue
        url = e.get("url", "").strip()
        k = norm_key(url)
        host = norm_host(url)
        if host in VERDICT_URL:
            url = VERDICT_URL[host]
        zh = zh_of(e, src)
        rec = {
            "domain": k.replace("gh:", "github.com/").replace("web:", ""),
            "url": url,
            "title": (e.get("title") or "").strip(),
            "category": CAT_MAP.get(e.get("subcategory") or e.get("category") or "其他",
                                    e.get("subcategory") or e.get("category") or "其他"),
            "zh": zh,
            "zh_evidence": e.get("zh_evidence", ""),
            "status": VERDICT.get(host, e.get("status") or "在线"),
            "quality": e.get("quality") or "中",
            "lang": e.get("lang") or "",
            "summary": (e.get("summary") or "").strip(),
            "src": {src},
        }
        if k in merged:
            old = merged[k]
            old["src"] |= rec["src"]
            old["zh_evidence"] = old.get("zh_evidence") or rec["zh_evidence"]
            old["summary"] = old["summary"] or rec["summary"]
            if host in VERDICT:
                old["status"] = VERDICT[host]
                old["url"] = VERDICT_URL.get(host, old["url"])
            if score(rec) > score(old):
                for f in ("title", "category", "zh", "quality", "lang"):
                    old[f] = rec[f]
        else:
            merged[k] = rec
    return merged


def main():
    merged, dropped = OrderedDict(), {"MTF剔除": []}
    ingest(MAIN, "主表", merged, dropped)
    ingest(BING, "Bing检索轮", merged, dropped)
    ingest(ZHF, "中文自建", merged, dropped)

    sites = list(merged.values())
    for s in sites:
        dom = norm_host(s["url"])
        if dom == "github.com":
            m = re.search(r"github\.com/([^/]+/[^/#?]+)", s["url"])
            ghkey = m.group(1).lower() if m else ""
            dom = ghkey or dom
        if dom in CAT_OVERRIDE:
            s["category"] = CAT_OVERRIDE[dom]
        if norm_host(s["url"]) == "2345.lgbt":
            s["zh"] = "原生中文"
            s["zh_evidence"] = s.get("zh_evidence") or "根路径 404，/zh-cn/ 实测 200（2026-09-12）"
        s["src"] = "、".join(sorted(s["src"], key=lambda x: ["主表", "Bing检索轮", "中文自建"].index(x)))
        if s["category"] not in CAT_ORDER:
            s["category"] = "其他"
    sites.sort(key=lambda x: (CAT_ORDER.index(x["category"]),
                              ["在线", "待复核", "失效"].index(x["status"]) if x["status"] in ("在线", "待复核", "失效") else 1,
                              zh_rank(x["zh"])))

    # ---- 输出 ----
    out = os.path.join(BASE, "FTM_终极清单.json")
    json.dump(sites, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    n_online = sum(1 for s in sites if s["status"] == "在线")
    n_zh = sum(1 for s in sites if s["zh"] in ("原生中文", "中文版路径", "多语言含中文"))
    n_pend = sum(1 for s in sites if s["status"] == "待复核")
    n_dead = sum(1 for s in sites if s["status"] == "失效")

    md = ["# FTM（跨性别男性）项目与网站 · 终极清单\n",
          "> 定稿 %s ｜ 共 **%d** 条（在线 %d / 待复核 %d / 失效 %d ｜ 含中文 %d）\n"
          % (VERDICT_DATE, len(sites), n_online, n_pend, n_dead, n_zh),
          "> 口径：剔除 MTF 专属；三套数据集合并去重（主表 85 + Bing 检索轮 89 + 中文自建 57）；"
          "4 个状态冲突域名已于 %s 逐站重测裁决。\n" % VERDICT_DATE,
          "> 数据文件：`FTM_终极清单.json`\n"]
    by_cat = {}
    for s in sites:
        by_cat.setdefault(s["category"], []).append(s)
    for cat in CAT_ORDER:
        items = by_cat.get(cat)
        if not items:
            continue
        md.append("\n## %s（%d）\n" % (cat, len(items)))
        for s in items:
            flag = {"在线": "", "待复核": " ⚠️待复核", "失效": " ❌失效"}.get(s["status"], "")
            md.append("- [%s](%s) — **%s** ｜ `%s` ｜ %s%s"
                      % (s["title"], s["url"], s["zh"], s["quality"], s["src"], flag))
            if s["summary"]:
                md.append("  %s" % s["summary"])
            if s["zh_evidence"]:
                md.append("  中文实测：%s" % s["zh_evidence"])
    md.append("\n---\n")
    md.append("## 附录：本轮 MTF 剔除 %d 条\n" % len(dropped["MTF剔除"]))
    for d, src in dropped["MTF剔除"]:
        md.append("- %s（%s）" % (d, src))
    open(os.path.join(BASE, "FTM_终极清单.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")

    # ---- HTML 卡片式（复用 Bing 轮样式）----
    def esc(t):
        return (t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    rows = []
    for s in sites:
        zh = s["zh"]
        cls = {"原生中文": "zh1", "中文版路径": "zh2", "多语言含中文": "zh3",
               "无中文": "zh4", "未核实": "zh5"}.get(zh, "zh5")
        st = s["status"]
        stcls = "ok" if st == "在线" else ("dead" if st == "失效" else "pend")
        rows.append(
            '<tr><td class="t"><a href="%s" target="_blank" rel="noopener">%s</a></td>'
            '<td>%s</td><td><span class="cat">%s</span></td>'
            '<td><span class="zh %s">%s</span></td>'
            '<td class="ev">%s</td>'
            '<td><span class="src">%s</span></td>'
            '<td><span class="st %s">%s</span></td></tr>'
            % (esc(s["url"]), esc(s["title"]), esc(s["summary"]), esc(s["category"]),
               cls, zh, esc(s["zh_evidence"]), esc(s["src"]), stcls, st))
    css = """
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
td.ev{color:var(--sub);font-size:12.5px;max-width:330px}
.cat{background:#eef1ec;border-radius:5px;padding:1px 7px;font-size:12px;color:#42503f;white-space:nowrap}
.zh{padding:1px 7px;border-radius:5px;font-size:12px;white-space:nowrap}
.zh1{background:#e3f2e3;color:#1e5c1e}
.zh2{background:#e8f0fa;color:#1e4a78}
.zh3{background:#f2ecfa;color:#523178}
.zh4{background:#f2f3f1;color:#6b736a}
.zh5{background:#fdf1e3;color:#8a5a12}
.src{background:#fff3d6;border-radius:5px;padding:1px 6px;font-size:11px;color:#7a5c10;white-space:nowrap}
.st{font-size:12px}
.st.ok{color:var(--acc)}.st.dead{color:#b3261e}.st.pend{color:#8a5a12}
"""
    html = ("<!DOCTYPE html>\n<html lang=\"zh-CN\"><head><meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
            "<title>FTM 项目与网站 · 终极清单</title>\n<style>" + css + "</style></head><body><div class=\"wrap\">\n"
            "<h1>FTM（跨性别男性）项目与网站 · 终极清单</h1>\n"
            '<div class="meta">定稿 ' + VERDICT_DATE + " ｜ 剔除 MTF 专属，三套数据集（主表 85 + Bing 检索轮 89 + 中文自建 57）合并去重 ｜ 冲突域名逐站重测裁决</div>\n"
            '<div class="stats">\n'
            '<div class="stat"><b>' + str(len(sites)) + '</b><span>收录总数</span></div>\n'
            '<div class="stat"><b>' + str(n_online) + '</b><span>在线</span></div>\n'
            '<div class="stat"><b>' + str(n_pend) + '</b><span>待复核</span></div>\n'
            '<div class="stat"><b>' + str(n_dead) + '</b><span>失效</span></div>\n'
            '<div class="stat"><b>' + str(n_zh) + '</b><span>含中文</span></div>\n'
            '</div>\n'
            '<table><thead><tr><th>站点 / 项目</th><th>简介</th><th>分类</th><th>中文支持</th><th>中文实测证据</th><th>来源</th><th>状态</th></tr></thead>\n'
            "<tbody>" + "\n".join(rows) + "</tbody></table>\n"
            '</div></body></html>\n')
    open(os.path.join(BASE, "FTM_终极清单.html"), "w", encoding="utf-8").write(html)


    print("总计 %d 条（在线 %d / 待复核 %d / 失效 %d / 含中文 %d）" % (len(sites), n_online, n_pend, n_dead, n_zh))
    cat = {}
    for s in sites:
        cat[s["category"]] = cat.get(s["category"], 0) + 1
    print("分类：", cat)
    print("MTF 剔除：%d 条" % len(dropped["MTF剔除"]))
    for d, src in dropped["MTF剔除"]:
        print("  -", d, "(%s)" % src)


if __name__ == "__main__":
    main()
