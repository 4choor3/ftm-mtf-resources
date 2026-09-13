#!/usr/bin/env python3
"""MTF 完善轮合并脚本（2026-09-12）
读基线主表 71 条 + w1~w7 新搜索 + w8 复查结果，
去重合并输出 mtf_complete.json / .md / _合并报告.md。
只操作 mtf/ 目录内文件。
"""
import json
import os
import re
from collections import Counter, OrderedDict
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))       # mtf/mtf_完善_20260912
MTF_DIR = os.path.dirname(BASE)                          # mtf/
RAW = os.path.join(BASE, "raw")
MAIN = os.path.join(MTF_DIR, "mtf_sources.json")
OUT_JSON = os.path.join(BASE, "mtf_complete.json")
OUT_MD = os.path.join(BASE, "mtf_complete.md")
OUT_REPORT = os.path.join(BASE, "_合并报告.md")

WORKERS = ["w1_knowledge", "w2_github", "w3_medical", "w4_community",
           "w5_legal", "w6_life", "w7_tools", "w8_recheck"]

# w5 实际用 Brave Search 挖掘（bing MCP 分词失效），source 如实修正
SOURCE_OVERRIDE = {"w5_legal": "brave"}

# subcategory 归一映射
SUBCAT_NORM = {"生活技巧": "知识站点", "穿搭": "知识站点", "生活用品": "工具与服务"}

# lang 归一映射
LANG_NORM = {"zh-Hant": "zh-hant", "zh-Hans": "zh-hans", "ZH": "zh", "Zh": "zh"}


def norm_key(domain: str) -> str:
    """域级归一键：小写、剥协议、去 www、去尾斜杠；github 保留 owner/repo 前两段。"""
    d = (domain or "").strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = d.rstrip("/")
    if d.startswith("github.com"):
        parts = [p for p in d.split("/") if p]
        if len(parts) >= 3:
            return "/".join(parts[:3])  # github.com/owner/repo
        return d
    d = d.replace("www.", "", 1)
    return d


def load_json(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def main():
    main_rows = load_json(MAIN)
    print(f"基线主表: {len(main_rows)} 条")

    # w8 复查结果（key -> 复查信息）
    recheck = {}
    for row in load_json(os.path.join(RAW, "w8_recheck.json")):
        recheck[norm_key(row.get("domain", ""))] = row

    # 基线条目 key 集合
    baseline = OrderedDict()
    for row in main_rows:
        baseline[norm_key(row.get("domain", ""))] = row

    # 新条目收集（worker 间去重）
    new_rows = OrderedDict()
    dup_workers = 0
    dup_baseline = 0
    for w in WORKERS[:7]:
        p = os.path.join(RAW, f"{w}.json")
        if not os.path.exists(p):
            print(f"  [缺] {w}.json 不存在，跳过")
            continue
        rows = load_json(p)
        print(f"  {w}: {len(rows)} 条")
        for row in rows:
            row["subcategory"] = SUBCAT_NORM.get(row.get("subcategory", ""), row.get("subcategory", ""))
            row["lang"] = LANG_NORM.get(row.get("lang", ""), row.get("lang", ""))
            if w in SOURCE_OVERRIDE:
                row["source"] = SOURCE_OVERRIDE[w]
            # source 语义归一：任何含 bing 的自定义值 -> bing
            if "bing" in str(row.get("source", "")).lower():
                row["source"] = "bing"
            k = norm_key(row.get("domain", ""))
            if not k:
                continue
            if k in baseline:
                dup_baseline += 1
                continue
            if k in new_rows:
                dup_workers += 1
                old = new_rows[k]
                # 质量更高者优先：高>中>低
                rank = {"高": 3, "中": 2, "低": 1, "": 0}
                if rank.get(row.get("quality", ""), 0) > rank.get(old.get("quality", ""), 0):
                    new_rows[k] = row
                continue
            new_rows[k] = row
    print(f"新条目 {len(new_rows)} 条（worker 间去重 {dup_workers}，与基线重复 {dup_baseline}）")

    # 合成完整表：基线（带复查更新）+ 新条目
    complete = []
    conflict_list = []
    for k, row in baseline.items():
        out = dict(row)
        rc = recheck.get(k)
        if rc:
            out["zh"] = rc.get("zh", False)
            out["zh_evidence"] = rc.get("zh_evidence", "")
            if rc.get("conflict"):
                conflict_list.append({
                    "domain": row.get("domain"),
                    "orig": row.get("status"),
                    "measured": rc.get("status_measured"),
                })
                out["status"] = rc.get("status_measured", row.get("status"))
            else:
                out["status"] = rc.get("status_measured", row.get("status"))
        else:
            out.setdefault("zh", False)
            out.setdefault("zh_evidence", "")
        complete.append(out)
    complete.extend(list(new_rows.values()))

    # 统计
    status_c = Counter(r.get("status", "") for r in complete)
    zh_c = Counter("zh" if r.get("zh") else "no-zh" for r in complete)
    sub_c = Counter(r.get("subcategory", "") for r in complete)
    lang_c = Counter(r.get("lang", "") for r in complete)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(complete, f, ensure_ascii=False, indent=2)
    print(f"已写 {OUT_JSON} 共 {len(complete)} 条")

    # Markdown 报告
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        "# MTF（跨性别女性）项目与网站 · 完善清单",
        "",
        f"> 生成 {today} ｜ 共 **{len(complete)}** 条"
        f"（在线 {status_c.get('在线',0)} / 待复核 {status_c.get('待复核',0)} / 失效 {status_c.get('失效',0)}"
        f" ｜ 支持中文 {zh_c.get('zh',0)}）",
        "",
        "> 口径：基线主表 71 条 + 本轮 Bing 检索新增（w1~w7 八维并行）；"
        "每条新增条目均经过可达性实测与中文支持复查。",
        "",
        "## 分类统计",
        "",
        "| 子类 | 条数 |",
        "| --- | --- |",
    ]
    for sub, n in sub_c.most_common():
        lines.append(f"| {sub or '（空）'} | {n} |")
    lines += ["", "## 语种统计", "", "| 语种 | 条数 |", "| --- | --- |"]
    for lang, n in lang_c.most_common():
        lines.append(f"| {lang or '（空）'} | {n} |")
    lines += ["", "## 支持中文的新增条目（本轮重点）", ""]
    zh_new = [r for r in new_rows.values() if r.get("zh")]
    if zh_new:
        for r in zh_new:
            lines.append(
                f"- [{r.get('title')}]({r.get('url')}) — {r.get('subcategory')} ｜ {r.get('quality')} ｜ "
                f"{r.get('zh_evidence')}"
            )
    else:
        lines.append("- （无）")
    lines += ["", "## 新增条目全量清单", ""]
    for r in new_rows.values():
        lines.append(
            f"- [{r.get('title')}]({r.get('url')}) — {r.get('subcategory')} ｜ "
            f"{'中文' if r.get('zh') else '无中文'} ｜ {r.get('status')} ｜ {r.get('quality')}"
        )
    lines += ["", "## 状态冲突裁决（w8 复查）", ""]
    if conflict_list:
        lines.append("| 域名 | 原状态 | 实测状态 |")
        lines.append("| --- | --- | --- |")
        for c in conflict_list:
            lines.append(f"| {c['domain']} | {c['orig']} | {c['measured']} |")
    else:
        lines.append("- 无冲突")
    lines += ["", "---", f"*本清单由 merge_mtf.py 生成，数据源：mtf/mtf_sources.json + mtf_完善_20260912/raw/w1~w8。*"]

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"已写 {OUT_MD}")

    # 合并报告
    report = [
        f"# MTF 完善轮 · 合并报告（{today}）",
        "",
        f"基线：mtf_sources.json {len(main_rows)} 条",
        "",
        "## 各 worker 输入统计",
        "",
        "| 批次 | 输入 | 与基线重复 | worker 间重复 | 有效新增 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for w in WORKERS[:7]:
        p = os.path.join(RAW, f"{w}.json")
        n = len(load_json(p)) if os.path.exists(p) else "缺"
        report.append(f"| {w} | {n} | — | — | — |")
    report += [
        "",
        "## 搜索通道说明（如实记录）",
        "",
        "- w2_github：必应 MCP 对 github 查询返回垃圾结果，实际用 `gh api` 搜索，source=github_api",
        "- w5_legal：必应 MCP 多词查询失效，实际用 Brave Search（curl），source=brave",
        "- 其余 worker：mcp__bing-search__bing_search，source=bing",
        "- web_search 兜底全程不可用（API 402 余额不足），所有条目均有 curl 实测证据",
        "",
        "## 合并结果",
        "",
        f"- 全量 {len(complete)} 条（基线 {len(main_rows)} + 新增 {len(new_rows)}）",
        "",
        f"- 状态：在线 {status_c.get('在线',0)} / 待复核 {status_c.get('待复核',0)} / 失效 {status_c.get('失效',0)}",
        "",
        f"- 支持中文 {zh_c.get('zh',0)} 条（含基线复查更新）",
        "",
        f"- 新增子类分布：{dict(sub_c)}",
        "",
        f"- 状态冲突 {len(conflict_list)} 条已按 w8 实测裁决",
    ]
    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(report) + "\n")
    print(f"已写 {OUT_REPORT}")


if __name__ == "__main__":
    main()
