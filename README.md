# FTM / MTF 跨性别资源索引

面向中文读者的跨性别网络资源调研索引，分 **MTF（跨性别女性）** 与 **FTM（跨性别男性）** 两条线整理。2026-09-11 起经多轮检索、逐站实测与口径筛选，全部条目均记录核验状态与中文支持证据。

## 数据概览

| 数据集 | 条数 | 口径 | 入口 |
| --- | --- | --- | --- |
| FTM 终极清单 | 156 | 三套数据集合并定稿（09-12） | [lists/FTM_终极清单.md](lists/FTM_终极清单.md) / [.html](lists/FTM_终极清单.html) |
| FTM 完善全集 | 257 | 完善轮八线检索并集，最全 | [lists/ftm_complete.md](lists/ftm_complete.md) / [.html](lists/ftm_complete.html) |
| FTM 网友自建精选 | 84 | 仅个人/社群/开源自建，剔除机构商业 | [lists/ftm_网友自建清单.md](lists/ftm_网友自建清单.md) / [.html](lists/ftm_网友自建清单.html) |
| MTF 网友自制精选 | 70 | 网友自制 + 可读性高 + 中文优先 | [lists/MTF_清单_网友自制精选.html](lists/MTF_清单_网友自制精选.html) |

## 目录结构

```
├── data/       结构化数据（JSON），字段含 domain/url/category/status/zh_evidence/verified_at 等
├── lists/      人类可读清单（Markdown + 自包含 HTML，直接双击打开）
├── docs/       调研报告与专项文档
└── scripts/    生成脚本（合并/筛选/渲染）
```

## 数据文件说明

| 文件 | 内容 |
| --- | --- |
| `data/FTM_终极清单.json` | 156 条定稿版，分类：知识库 28 / 医疗用药 42 / 社区组织 26 / 开源项目 19 / 工具 14 / 社区论坛 8 / 嗓音 6 / 导航 6 / 束胸假体 4 / 手术 2 / 个人站点 1 |
| `data/ftm_complete.json` | 257 条完善全集（在线 226 / 待复核 22 / 失效 9，含中文 64） |
| `data/ftm_网友自建清单.json` | 84 条精选子集（在线 82，含中文 39） |
| `data/mtf_sources.json` | 70 条 MTF 精选主表，含中文实测证据字段 |

## 主要发现

- 中文跨性别资源在「知识整合」层较完善（Project Trans 一整套站点），MTF 侧 HRT 资料已有多个新站补充。
- **FTM 侧三大缺口**：睾酮 HRT 男性化用药、嗓音男性化训练、手术资料——中文独立站均为 0，仅英文源可用；束胸/假体品类英文生态厚、中文为 0。
- 中文跨性别内容主要沉淀于微信公众号、开源仓库/Wiki 与注册 NGO，「个人自建独立网站」形态几乎没有存活样本。

## 调研方法

1. 多通道检索：搜索引擎 + GitHub API + 枢纽站外链挖掘，多 worker 分维度并行。
2. 逐站实测：HTTP 状态分级判定（区分域名失效 / WAF 拦截 / 网络层不可达），中文支持以页面 CJK 字符占比实测为准。
3. 口径筛选：「网友自建」按「谁做的」判定；语言路径归一化去重（`/zh-cn` 等变体合并）。
4. 歧义排除：FTM ≠ Fantom 代币 / Follow The Money / 车辆工程研究所；MTF ≠ 光学调制传递函数 / 多时间框架。

## scripts 说明

脚本为调研过程留档，内含原始工作区的绝对路径，如需复跑请先修改路径常量：

- `merge_final.py`：三套 FTM 数据集 → 终极清单（156）
- `merge_complete.py`：FTM 完善轮 raw 批次 → 全集（257）
- `filter_grassroots.py`：FTM 全集 → 网友自建精选（84）+ 剔除归档
- `merge_mtf.py` / `filter_selected.py`：MTF raw 合并 → 243 → 精选 70
- `gen_mtf_html.py` / `gen_mtf_sources_md.py`：主表 → HTML / Markdown 清单

## 时效声明

条目有效性为收录时（2026-09-11 ~ 09-13）实测状态，链接与内容可能随时间变化。本仓库仅索引第三方公开站点，不托管其内容，亦不构成医疗建议；就医请咨询专业医疗机构。
