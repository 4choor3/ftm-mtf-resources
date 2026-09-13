#!/usr/bin/env python3
"""MTF 精选轮（2026-09-12）：从 243 条全量中过滤出「网友自制 + 可读性高」条目。
口径：剔除官方机构（政府/学术/行业协会/大型NGO/商业医院诊所/商店/通用百科）；
保留社区自建 wiki、个人博客、论坛、GitHub 内容/用户工具类项目、草根社群组织。
语言：中文（zh 系）优先；英文仅保留圈内高价值网友自制资源。
只操作 mtf/ 目录内文件。
"""
import json
import os
from collections import Counter

BASE = os.path.dirname(os.path.abspath(__file__))     # mtf/mtf_完善_20260912
MTF_DIR = os.path.dirname(BASE)                        # mtf/
FULL = os.path.join(BASE, "mtf_complete.json")       # 243 全量存档（过滤源，永不覆盖）
OUT_SELECTED = os.path.join(BASE, "mtf_selected.json") # 精选集存档
OUT_MAIN = os.path.join(MTF_DIR, "mtf_sources.json")   # 主表（覆盖为精选集）

# 明确剔除的 domain（精确匹配；github 条目为 github.com/owner/repo 前缀匹配）
REMOVE_EXACT = {
    # —— 基线：官方机构 / 协会 / 政府 / 学术 ——
    "endocrine.org", "famplan.org.hk", "fenwayhealth.org", "gendergp.com",
    "gires.org.uk", "glma.org", "medlineplus.gov", "msdmanuals.cn", "nhs.uk",
    "plannedparenthood.org", "sandyford.org", "webmd.com", "wpath.org",
    "crisistextline.org", "aclu.org", "gov.uk", "hrc.org", "lambdalegal.org",
    "nclrights.org", "tgeu.org", "transequality.org", "transgenderlawcenter.org",
    "transrespect.org", "yogyakartaprinciples.org", "guttmacher.org",
    "mypronouns.org", "plato.stanford.edu", "transhub.org.au",
    "williamsinstitute.law.ucla.edu", "familyequality.org", "gendercentre.org.au",
    "genderedintelligence.co.uk", "genderspectrum.org", "gid.jp", "glaad.org",
    "glsen.org", "mermaidsuk.org.uk", "pflag.org", "stonewall.org.uk",
    "thetrevorproject.org", "transactual.org.uk", "transanta.org",
    "transgenderpulse.com", "transstudent.org",
    # —— 通用百科 ——
    "baike.baidu.com", "zh.wikipedia.org",
    # —— 英文通用 wiki / 小众英文个人站 ——
    "transwiki.co", "lgbtqia.wiki", "crossdreamers.com", "transsexual.org",
    # —— 医疗：商业医院 / 诊所 / 机构 ——
    "kamolhospital.com", "lgbtqhealthcaredirectory.org", "facialteam.eu",
    "supornclinic.com", "grsmontreal.com", "drkanit.com",
    "bangkokplasticsurgery.com", "pai.co.th", "gendercare.co.uk",
    "thelondontransgenderclinic.uk", "callen-lorde.org", "howardbrown.org",
    "folxhealth.com", "getplume.co", "queerdoc.com", "transcarebc.ca",
    "rainbowhealthontario.ca", "undeadvoicelab.com", "seattlevoicelab.com",
    "christellaantoni.co.uk",
    # —— 社区：英文论坛 / 机构 / 失效 ——
    "transgenderzone.com", "hannahmcknight.org", "translifeline.org",
    "pointofpride.org", "transfamilysos.org", "transunite.co.uk",
    "transcentralpa.org", "disboard.org", "transgenderheaven.com",
    "translives.net", "mtf.moe",
    # —— 法律：政府 / 国际组织 / 律所 / 机构 ——
    "eoc.org.hk", "lgbt.gov.taipei", "ohchr.org", "unfe.org", "amnesty.org",
    "hanshenglaw.cn", "zhenrogy.org", "transgender.taipei", "glad.org",
    "lgbtmap.org", "ilga.org", "ilgaasia.org", "outrightinternational.org",
    "transyouthequality.org", "tgguide.com", "bettzedek.org",
    "translegalaidtx.com", "equalityohio.org", "lalgbtcenter.org",
    "texaslawhelp.org", "selfhelp.courts.ca.gov", "calcivilrights.ca.gov",
    "ag.ny.gov", "hrhub.law.hku.hk",
    # —— 生活/商店：商业品牌 / 商店 ——
    "unclockable.com", "enfemmestyle.com", "fit4usolutions.com",
    "thebreastformstore.com", "glamourboutique.com", "janetscloset.com",
    "origamicustoms.com",
    # —— 工具：机构 ——
    "transhealthproject.org",
}

# 第二轮删除（2026-09-13）：进一步收紧到「MTF 社群中文资源」口径
REMOVE_EXACT_2 = {
    # 泛 LGBTQ 组织 / 协会 / 泛性教育（非 MTF 社群专属）
    "aibai.com", "chuse8.com", "hotline.org.tw", "tgeea.org.tw", "tapcpr.org",
    "tehk.org.hk", "twgra.org", "tgr.org.hk", "post.knowsex.net",
    # 英文个人站 / 网志 / 教学（对中文读者不可读）
    "genderanalysis.net", "juliaserano.com", "transgendermap.com",
    "robynwithawhy.com", "scinguistics.com", "transvoicelessons.com",
    "genderkit.org.uk",
    # 英文数据 / 目录站
    "diyhrt.wiki", "hrt.cafe", "transfemscience.org", "transhealthcare.org",
    "equaldex.com", "reddit.com",
    # 交友站 / 商业 App 官网
    "transnation.asia", "asterismlabs.io",
}

REMOVE_GH_PREFIX_2 = {
    # 英文工具 / 列表
    "github.com/cvyl/awesome-transgender",
    "github.com/soapingtime/diyhrt",
    "github.com/refugerestrooms/refugerestrooms",
    "github.com/skurhse/trans-hotlines",
    "github.com/whsah/estrannaise.js",
    "github.com/trans-archive/trans-parents",
    # 弱相关 / 纯代码仓库
    "github.com/kurosawageeker/femboy-skill",
    "github.com/cdtsf-library/cdts-fiction-archive",
    "github.com/one-among-us/web",
    "github.com/viva-la-vita/viva-la-vita.github.io",
    "github.com/viva-la-vita/bbs",
    "github.com/transcircle/transcircle",
    "github.com/znvtbw/trans-overview-cn",
}

# 剔除的 GitHub 仓库（纯基础设施代码 / 备份脚本 / 镜像 / 低价值英文工具）
REMOVE_GH_PREFIX = {
    "github.com/one-among-us/backend",            # 后端代码
    "github.com/one-among-us/tg-blog",            # 备份工具
    "github.com/one-among-us/TelegramBackup",     # 备份工具
    "github.com/one-among-us/TwitterBackup",      # 备份工具
    "github.com/trans-archive/transky-raw",       # 与 transky 重复的原稿
    "github.com/diyhrt2/diyhrt2.github.io",       # diyhrt.wiki 镜像
    "github.com/DigitalTransgenderArchive/dta",   # 机构代码库
    "github.com/LaoZhong-Mihari/HRT-Recorder-PKcom",  # 纯组件库
    "github.com/hypothete/e2-patch-simulator",    # 低质量英文工具
    "github.com/NAKlama/HormoneLevels",           # 低质量英文工具
    "github.com/Jana-Marie/hlcc",                 # 低质量英文工具
    "github.com/PersephoneKarnstein/ha-estrannaise",  # 低质量英文工具
    "github.com/Harmony-Within-Us/hrt.info",      # 低质量英文工具
    "github.com/yufun-meow/yuE2logger",           # 低质量英文工具
    "github.com/Kavex/VocalTuner",                # 低质量英文工具
    "github.com/terraboops/transtone",            # 低质量英文工具
    "github.com/j0lol/transvoice_party",          # 低质量英文工具
    "github.com/LuaCascade/voicefemguide",        # 低质量英文工具
    "github.com/cutthroat78/Trans-Voice-Notes",   # 低质量英文工具
    "github.com/Transgender-Resource-Wiki/Transgender-Resource-Wiki.github.io",  # 低质量
    "github.com/dongguacute/TransTalk",           # 低质量英文站
    "github.com/AwantedRaccoon/mtfunmanual-app",  # 低质量工具
    "github.com/KokoroLyase/HRT-Monitor",         # 低质量工具
}


def should_remove(domain: str) -> bool:
    d = (domain or "").strip().lower().replace("www.", "")
    if d in REMOVE_EXACT or d in REMOVE_EXACT_2:
        return True
    for p in list(REMOVE_GH_PREFIX) + list(REMOVE_GH_PREFIX_2):
        if d.startswith(p.lower()):
            return True
    return False


def main():
    rows = json.load(open(FULL, encoding="utf-8"))
    removed, kept = [], []
    for r in rows:
        (removed if should_remove(r.get("domain", "")) else kept).append(r)

    zh_n = sum(1 for r in kept if r.get("zh"))
    print(f"输入 {len(rows)} 条 -> 剔除 {len(removed)} 条 -> 保留 {len(kept)} 条（zh {zh_n}）")
    print("子类:", dict(Counter(r.get("subcategory") for r in kept)))
    print("状态:", dict(Counter(r.get("status") for r in kept)))
    print("语种:", dict(Counter(r.get("lang") for r in kept)))

    json.dump(kept, open(OUT_SELECTED, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(kept, open(OUT_MAIN, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(removed, open(os.path.join(BASE, "mtf_removed.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"已写 {OUT_MAIN}（主表已覆盖为精选集）")
    print(f"已写 {OUT_SELECTED}、{BASE}/mtf_removed.json")


if __name__ == "__main__":
    main()
