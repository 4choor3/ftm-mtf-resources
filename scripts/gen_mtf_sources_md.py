#!/usr/bin/env python3
"""从 mtf_complete.json 生成新版 mtf_sources.md 与 MTF_站点清单_超链接版.md
（2026-09-12 完善轮；覆盖 mtf/ 根目录两个 md，json 主表由 merge_mtf.py 产物复制）
只操作 mtf/ 目录内文件。
"""
import json
import os
from collections import Counter, OrderedDict
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))          # mtf/mtf_完善_20260912
MTF_DIR = os.path.dirname(BASE)                             # mtf/
COMPLETE = os.path.join(MTF_DIR, "mtf_sources.json")       # 当前主表（精选版）
OUT_MD = os.path.join(MTF_DIR, "mtf_sources.md")
OUT_LINK = os.path.join(MTF_DIR, "MTF_站点清单_超链接版.md")

ORDER = ["知识站点", "医疗与政策", "社区与组织", "法律权益", "开源项目", "工具与服务"]

def main():
    rows = json.load(open(COMPLETE, encoding="utf-8"))
    today = datetime.now().strftime("%Y-%m-%d")
    zh_n = sum(1 for r in rows if r.get("zh"))
    zh_new_n = sum(1 for r in rows if r.get("zh") and r.get("source") in ("bing", "github_api", "brave"))

    by_sub = OrderedDict()
    for sub in ORDER:
        by_sub[sub] = [r for r in rows if r.get("subcategory") == sub]
    by_sub["其他"] = [r for r in rows if r.get("subcategory") not in ORDER]

    def lang_stats():
        c = Counter((r.get("lang") or "").replace("zh-Hant", "zh-hant").replace("zh-Hans", "zh-hans")
                    for r in rows)
        parts = []
        for k, v in sorted(c.items(), key=lambda kv: -kv[1]):
            name = {"zh": "中文", "zh-hans": "简体中文", "zh-hant": "繁體中文",
                    "en": "英文", "ja": "日文"}.get(k, k)
            parts.append(f"{name} {v}")
        return "、".join(parts)

    # ---- mtf_sources.md ----
    lines = [
        f"# MTF（跨性别女性）站点清单 · 网友自制精选版",
        "",
        f"> 共 **{len(rows)}** 条 · 语种 {lang_stats()}",
        f"> 支持中文 **{zh_n}** 条；状态：在线 {sum(1 for r in rows if r.get('status')=='在线')} / 待复核 {sum(1 for r in rows if r.get('status')=='待复核')} / 失效 {sum(1 for r in rows if r.get('status')=='失效')}",
        f"> 更新日期 {today}；从 243 条全量中精选：剔除官方机构（政府/学术/协会/大型NGO/商业医院诊所/商店/通用百科），只保留网友自制与社区自建——wiki、个人博客、论坛、GitHub 项目、草根社群组织。",
        f"> 中文判定 = 主页或 /zh 路径正文 CJK 占比实测（证据见 mtf_完善_20260912/mtf_complete.json 的 zh_evidence 字段）。",
        "",
    ]
    for sub, items in by_sub.items():
        if not items:
            continue
        lines += [f"## {sub}（{len(items)}）", "",
                  "| 域名 | 标题 | URL | 语种 | 中文 | 质量 | 状态 | 价值说明 |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- |"]
        for r in items:
            zh_mark = "✅" if r.get("zh") else "—"
            title = str(r.get("title", "")).replace("|", "\\|").replace("\n", " ")
            summ = str(r.get("summary", "")).replace("|", "\\|").replace("\n", " ")
            lines.append(
                f"| {r.get('domain','')} | {title} | {r.get('url','')} | {r.get('lang','')} "
                f"| {zh_mark} | {r.get('quality','')} | {r.get('status','')} | {summ} |"
            )
        lines.append("")
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"已写 {OUT_MD}")

    # ---- 超链接版 ----
    toc = []
    for sub, items in by_sub.items():
        if items:
            toc.append(f"- [{sub}（{len(items)}）](#{sub}{len(items)})")
    l2 = [
        f"# MTF（跨性别女性） 站点清单 · 超链接版（网友自制精选）",
        "",
        f"**共 {len(rows)} 个条目**　|　更新日期 {today}　|　支持中文 {zh_n} 条",
        "",
        f"语种分布：{lang_stats()}",
        "",
        "> 收录标准：网友自制与社区自建（wiki、个人博客、论坛、GitHub 项目、草根社群组织）；官方机构、商业医院诊所、商店、通用百科已剔除。全部条目经 curl 实测，中文支持按主页/本地化路径 CJK 占比实测判定。",
        "> 数据来源：bing_search MCP、GitHub API、Brave Search；全量 243 条存档于 mtf_完善_20260912/mtf_complete.json。",
        "",
        "## 目录",
        "",
    ] + toc + [""]
    for sub, items in by_sub.items():
        if not items:
            continue
        l2 += [f"## {sub}（{len(items)}）", ""]
        for r in items:
            zh_tag = " **中文**" if r.get("zh") else ""
            status = "" if r.get("status") == "在线" else f" ｜ ⚠️{r.get('status')}"
            title = str(r.get("title", "")).replace("\n", " ")
            l2.append(f"- [{title}]({r.get('url')}) — `{r.get('domain')}`{zh_tag} ｜ {r.get('lang')} ｜ {r.get('quality')}{status}")
            summ = str(r.get("summary", "")).strip()
            if summ:
                l2.append(f"  {summ}")
        l2.append("")
    with open(OUT_LINK, "w", encoding="utf-8") as f:
        f.write("\n".join(l2) + "\n")
    print(f"已写 {OUT_LINK}")


if __name__ == "__main__":
    main()
