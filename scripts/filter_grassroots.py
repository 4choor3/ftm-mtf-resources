#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按用户口径过滤 FTM 完善清单：只保留网友自制、可读性高的；剔除官方/机构/商业。

口径（2026-09-12 用户指令 + 历史判定原则）：
  看「谁做的」而非「内容是什么」——个人站长、网友团体、开源社区志愿者 = 保留；
  注册机构、协会、医院、高校、政府文件、商业公司 = 剔除。
  剔除条目不删除，归档到 ftm_剔除归档.json。

输入: ftm_完善_20260912/ftm_complete.json
输出: ftm_完善_20260912/ftm_网友自建清单.{json,md,html} + ftm_剔除归档.json
"""
import json
import os
import re
from collections import Counter
from urllib.parse import urlparse

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUB = os.path.join(BASE, "ftm_完善_20260912")
SRC = json.load(open(os.path.join(SUB, "ftm_complete.json"), encoding="utf-8"))

# ---- 剔除名单（domain 前缀匹配）----
DROP = {
    # 医院 / 医学院 / 官方卫生机构
    "puh3.net.cn", "callen-lorde.org", "fenwayhealth.org", "howardbrown.org",
    "mazzonicenter.org", "nhs.uk", "ohsu.edu", "rainbowhealthontario.ca",
    "transcare.ucsf.edu", "transhub.org.au", "phsa.ca", "bumc.bu.edu",
    "mayoclinic.org", "msdmanuals.com", "msdmanuals.cn", "dartmouth-hitchcock.org",
    "ummhealth.org", "healthcare.utah.edu", "med.umich.edu", "dayi.org.cn",
    # 协会 / 学会 / 国际组织 / 学术
    "wpath.org", "endocrine.org", "acog.org", "ncbi.nlm.nih.gov",
    "williamsinstitute.law.ucla.edu", "gutmacher.org", "thegalap.org",
    "digitaltransgenderarchive.net", "apa.org",
    # 注册 NGO / 慈善 / 权益组织 / 热线
    "thetrevorproject.org", "chuse8.com", "tgr.org.hk", "glaad.org",
    "mermaidsuk.org.uk", "pflag.org", "transacademic.org", "transequality.org",
    "transactual.org.uk", "transstudent.org", "genderspectrum.org",
    "translifeline.org", "lambdalegal.org", "nclrights.org", "srlp.org",
    "transgenderlawcenter.org", "pointofpride.org", "transgender.tapcpr.org",
    "transmann.de", "genderedintelligence.co.uk", "transunite.co.uk",
    "transvisie.nl", "transgendernetwerk.nl", "actionfortranshealth.org.uk",
    "dcats.org", "the519.org", "mhanational.org", "hotline.org.tw",
    "community.lalgbtcenter.org", "stcpride.org",
    # 商业医疗 / 诊所 / 医疗旅游
    "folxhealth.com", "genderconfirmation.com", "gendergp.com", "getplume.co",
    "plume.health", "compassftm.org", "queerdoc.com", "imgender.com",
    "nedatransgendersurgery.com", "vjtransgenderclinics.com",
    "hannagendercenter.com", "us-uk.bookimed.com", "rememore.com",
    "drwoncosmeticsurgery.com", "gdtgendersurgery.com",
    "connectedspeechpathology.com", "mtavspeechtherapy.com",
    # 商业品牌 / 厂商 / 零售
    "gc2b.co", "spectrumoutfitters.co.uk", "transthetics.com", "underworks.com",
    "tomscout.com", "transessentials.com", "emisil.com", "ftmessentials.com",
    "transguysupply.com", "axolom.com", "axolom.cn", "banabuddy.com",
    "amorsensory.com", "shapeshifters.co", "reelmagik.com", "transtape.life",
    "bothandapparel.com", "sockdrawerheroes.com", "forthem.com",
    # 官方文件（中文翻译）/ 机构项目
    "project-trans.org/soc-8", "github.com/project-trans/soc-8",
    "github.com/project-trans/china-legal", "github.com/project-trans/legal-spec",
    # 主题不符（非跨性别语境站） / 无法确认运营方 / MTF 向机构
    "cairs.hk", "lgbtq-plus.jp", "github.com/mtfreport-team",
}

# ---- 第二轮删除（2026-09-12 用户指令"进一步删去非我要求的网站"）----
# 口径：FTM 专属项目/网站 + 中文网友自制核心；大平台页面、MTF 向、英文通用站剔除
DROP2 = {
    # 大平台板块 / 单篇文章 / 百科词条（不是独立网站/项目）
    "zh.wikipedia.org", "en.wikipedia.org", "zh.wikihow.com",
    "lgbtqia.fandom.com", "trans-resource.fandom.com", "bilibili.com/opus",
    "ptt.cc", "dcard.tw", "tieba.baidu.com", "reddit.com/r",
    "lemmy.blahaj.zone", "discordservers.com", "discord.do", "disboard.org",
    # MTF 女性化向 / 方向不明的嗓音类
    "transvoicelessons.com", "voice.hydev.org",
    "github.com/tastycode/transpeak", "github.com/terraboops/transtone",
    "github.com/kavex/vocaltuner", "github.com/emilymoonstone/voxa",
    "github.com/kushiemoon-dev/voice-lab", "github.com/theforeveriris/simple-voice-tools",
    "acousticgender.space", "github.com/sumianvoice/transvoice-wiki",
    # 英文通用跨性别 / LGBTQ 站（非 FTM 专属）
    "lgbtqia.wiki", "nonbinary.wiki", "transadvice.org", "transgenderzone.com",
    "transgenderheaven.com", "tgguide.com", "forum.emptyclosets.com", "susans.org",
    "transgenderpulse.com", "transgenderteensurvivalguide.com", "trans.chat",
    "genderkit.org.uk", "transreads.org", "t-vox.org", "trans-health.com",
    "thhq.org", "transineigenhand.nl", "wikitrans.co", "transchinese.org",
    "transdb.de", "refugerestrooms.org", "transhealthcare.org", "hrt.coffee",
    "transgendermap.com", "antidysphoria.carrd.co", "transcompass.org",
    "trans.lgbt", "ftmmagazine.com",
    # 通用英文 GitHub 项目（非 FTM 专属）
    "github.com/cvyl/awesome-transgender", "github.com/skurhse/trans-hotlines",
    "github.com/ryderdamen/lgbtq_technology_resources", "github.com/namesakefyi/namesake",
    "github.com/translunar/f64", "github.com/cytoshell/hrt-tracker",
    "github.com/remixmb/gauage-it-right", "github.com/transdb-de/website",
    "github.com/refugerestrooms/refugerestrooms", "github.com/kydecker/genderswap.fm",
}

CAT_ORDER = ["知识库", "开源项目", "社区论坛", "社区组织", "医疗用药", "手术",
             "嗓音", "束胸假体", "工具", "个人站点", "导航", "其他"]
ZH_ORDER = ["原生中文", "中文版路径", "多语言含中文", "无中文", "未核实"]


def norm_host(url):
    try:
        h = urlparse(url).netloc.lower()
    except Exception:
        return ""
    return h[4:] if h.startswith("www.") else h


def is_dropped(s):
    dom = s["domain"].lower()
    if any(d == dom or dom.startswith(d + "/") for d in DROP):
        return True
    if any(d == dom or dom.startswith(d + "/") for d in DROP2):
        return True
    if s.get("status") == "失效":  # 失效条目不再保留（可读性优先）
        return True
    return False


def zh_rank(z):
    return ZH_ORDER.index(z) if z in ZH_ORDER else len(ZH_ORDER)


def main():
    keep, drop = [], []
    for s in SRC:
        (drop if is_dropped(s) else keep).append(s)
    keep.sort(key=lambda x: (CAT_ORDER.index(x["category"]) if x["category"] in CAT_ORDER else 99,
                             ["在线", "待复核", "失效"].index(x["status"]) if x["status"] in ("在线", "待复核", "失效") else 1,
                             zh_rank(x["zh"])))
    n_online = sum(1 for s in keep if s["status"] == "在线")
    n_pend = sum(1 for s in keep if s["status"] == "待复核")
    n_zh = sum(1 for s in keep if s["zh"] in ("原生中文", "中文版路径", "多语言含中文"))
    n_new = sum(1 for s in keep if not s.get("known"))

    json.dump(keep, open(os.path.join(SUB, "ftm_网友自建清单.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump(drop, open(os.path.join(SUB, "ftm_剔除归档.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    # ---- MD ----
    md = ["# FTM（跨性别男性）网友自制资源清单\n",
          "> 定稿 2026-09-12 ｜ 共 **%d** 条（在线 %d / 待复核 %d ｜ 含中文 %d）\n"
          % (len(keep), n_online, n_pend, n_zh),
          "> 口径：只看「谁做的」——个人站长、网友团体、开源社区志愿者收录；医院/学会/注册机构/政府文件/商业公司剔除"
          "（剔除条目不删除，归档于 `ftm_剔除归档.json`）。\n",
          "> 数据文件：`ftm_网友自建清单.json`\n"]
    by_cat = {}
    for s in keep:
        by_cat.setdefault(s["category"], []).append(s)
    for cat in CAT_ORDER:
        items = by_cat.get(cat)
        if not items:
            continue
        md.append("\n## %s（%d）\n" % (cat, len(items)))
        for s in items:
            newtag = " 🆕" if not s.get("known") else ""
            flag = {"在线": "", "待复核": " ⚠️待复核", "失效": " ❌失效"}.get(s["status"], "")
            md.append("- [%s](%s) — **%s** ｜ `%s`%s%s"
                      % (s["title"], s["url"], s["zh"], s["quality"], newtag, flag))
            if s["summary"]:
                md.append("  %s" % s["summary"])
            if s["zh_evidence"]:
                md.append("  中文实测：%s" % s["zh_evidence"])
    open(os.path.join(SUB, "ftm_网友自建清单.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")

    # ---- HTML ----
    def esc(t):
        return (t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    rows = []
    for s in keep:
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
            '<td><span class="st %s">%s</span></td></tr>'
            % (esc(s["url"]), esc(s["title"]), newtag, esc(s["summary"]), esc(s["category"]),
               cls, zh, esc(s["zh_evidence"]), stcls, st))
    css = """
:root{--bg:#f6f7f5;--card:#fff;--ink:#1b1f1a;--sub:#5c665c;--line:#e2e6e0;--acc:#4E9A4E;--new:#c2410c}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.65 -apple-system,"PingFang SC","Helvetica Neue",sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:32px 20px 64px}
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
.new{display:inline-block;margin-left:6px;font-size:10.5px;background:#fff1e7;color:var(--new);
  border:1px solid #f4c9ae;border-radius:5px;padding:0 5px;vertical-align:1px}
.st{font-size:12px}
.st.ok{color:var(--acc)}.st.dead{color:#b3261e}.st.pend{color:#8a5a12}
"""
    html = ("<!DOCTYPE html>\n<html lang=\"zh-CN\"><head><meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
            "<title>FTM 网友自制资源清单</title>\n<style>" + css +
            "</style></head><body><div class=\"wrap\">\n"
            "<h1>FTM（跨性别男性）网友自制资源清单</h1>\n"
            '<div class="meta">定稿 2026-09-12 ｜ 口径：个人站长 / 网友团体 / 开源社区志愿者收录；医院 / 学会 / 注册机构 / 政府文件 / 商业公司剔除（归档于 ftm_剔除归档.json）</div>\n'
            '<div class="stats">\n'
            '<div class="stat"><b>' + str(len(keep)) + '</b><span>收录总数</span></div>\n'
            '<div class="stat"><b>' + str(n_online) + '</b><span>在线</span></div>\n'
            '<div class="stat"><b>' + str(n_pend) + '</b><span>待复核</span></div>\n'
            '<div class="stat"><b>' + str(n_zh) + '</b><span>含中文</span></div>\n'
            '<div class="stat"><b>' + str(n_new) + '</b><span>本轮新增</span></div>\n'
            '</div>\n'
            '<table><thead><tr><th>站点 / 项目</th><th>简介</th><th>分类</th><th>中文支持</th><th>中文实测证据</th><th>状态</th></tr></thead>\n'
            "<tbody>" + "\n".join(rows) + "</tbody></table>\n"
            '</div></body></html>\n')
    open(os.path.join(SUB, "ftm_网友自建清单.html"), "w", encoding="utf-8").write(html)

    print("保留 %d 条（在线 %d / 待复核 %d / 含中文 %d / 新增 %d）" % (len(keep), n_online, n_pend, n_zh, n_new))
    print("剔除 %d 条（含失效 %d）" % (len(drop), sum(1 for s in drop if s["status"] == "失效")))
    print("保留分类：", dict(Counter(s["category"] for s in keep)))
    print("保留中文：", dict(Counter(s["zh"] for s in keep)))


if __name__ == "__main__":
    main()
