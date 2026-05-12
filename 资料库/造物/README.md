# 玄鉴仙族 · 法宝/道具/灵资 Wiki

> **总页数**：449 · **类型分类**：14 类（13 造物 + 1 人物）· **状态**：✅ MediaWiki 已发布
>
> 最近更新：2026-05-10

---

## 快速入口

| 资源 | 路径 | 说明 |
|---|---|---|
| 📄 **wiki 产物**（唯一权威） | [`pages/`](./pages/) | 449 页，按 14 类型子目录组织 |
| 🛠 **工作流 SOP** | [`WORKFLOW.md`](./WORKFLOW.md) | 上传/Rescue/品阶/3-Agent 协作 |
| 📐 **写作规范** | [`docs/`](./docs/) | 内链规范 / 分类判定 / wiki 模板 |
| 🗂 **归档** | [`archive/`](./archive/) | 旧脚本/旧批次/历史快照 zip |
| 🔧 **工程核心** | [`.workbuddy/wide_window/`](./.workbuddy/wide_window/) | 脚本+context+workstate |
| 📚 **长期记忆**（AI 用） | [`.workbuddy/memory/MEMORY.md`](./.workbuddy/memory/MEMORY.md) | 项目目标/架构/铁律 |
| 📝 **每日日志**（AI 用） | [`.workbuddy/memory/`](./.workbuddy/memory/) | 按日期记录 |

---

## 14 类型目录索引

| 子目录 | 容纳品阶 | 页数 | 代表实体 |
|---|---|---|---|
| [`pages/01-灵气/`](./pages/01-灵气/) | 灵气/极品灵气/紫府灵火/灵水 | 14 | 太阴月华、金阳煌元、天一淳元 |
| [`pages/02-灵物-灵资/`](./pages/02-灵物-灵资/) | 灵物/紫府灵物/筑基灵物/灵资/宝药 | 181 | 颈下羽、明方天石、宛陵花 |
| [`pages/03-丹药/`](./pages/03-丹药/) | 紫府灵丹/丹药/散剂 | 8 | 明真合神丹、麟光照一丹 |
| [`pages/04-灵器/`](./pages/04-灵器/) | 灵器/紫府灵器/中品法器 | 45 | 赶山赴海虎、止戈、申白 |
| [`pages/05-灵宝/`](./pages/05-灵宝/) | 灵宝/衡祝灵宝/戊土灵宝/邪宝 | 69 | 华阳王钺、重火两明仪、玄珩敕丹 |
| [`pages/06-古灵器/`](./pages/06-古灵器/) | 古灵器/古法器/极品古法器 | 17 | — |
| [`pages/07-筑基法器/`](./pages/07-筑基法器/) | 筑基法器/筑基法剑/凡器 | 40 | 寒廪、湛蓝刃、万昱剑 |
| [`pages/08-符箓/`](./pages/08-符箓/) | 符箓 | 1 | — |
| [`pages/09-法宝/`](./pages/09-法宝/) | 法宝/位别/仙器 | 7 | 大衍天素书、渌台醒心剑 |
| [`pages/10-材料/`](./pages/10-材料/) | 材料 | 32 | — |
| [`pages/11-法术秘法/`](./pages/11-法术秘法/) | 法术/秘法/灵宝神妙 | 2 | — |
| [`pages/12-其他/`](./pages/12-其他/) | 紫府修士等杂项 | 4 | — |
| [`pages/13-待分类/`](./pages/13-待分类/) | 待分类/特殊 | 13 | — |
| [`pages/20-人物/`](./pages/20-人物/) | 李家世系+外族 | 16 | 李曦明、李阙宛、李玄锋 |

---

## 文件命名规则

```
pages/{NN-类型}/L{1-6}-{实体名}.wiki

L1 = 高频核心（88-49 次）
L2 = 中高频（49-20 次）
L3 = 中频（19-15 次）
L4 = 中低频（9-5 次）
L5 = 低频（4-2 次）
L6 = 仅 1 次
```

**示例**：`pages/01-灵气/L1-太阴月华.wiki` = 灵气类 · 高频核心 · 太阴月华

线上页面标题由上传脚本自动加前缀：`造物-XX` / `人物-XX`。L 前缀仅文件名，不进标题。

---

## 上传到 MediaWiki

```bash
cd /Users/leoshi/AIBOOK/xuanjian/wiki
set -a && source .env && set +a
python3 scripts/upload_pages.py --only "资料库/造物/pages" --summary "xxx"
```

详见 [`WORKFLOW.md`](./WORKFLOW.md)。

---

## 项目结构

```
资料库/造物/
├── README.md                  你正在看的文件
├── WORKFLOW.md                工作流 SOP（生产/上传/QA/协作）
├── pages/                     ⭐ 449 页 wiki 产物（唯一权威源）
├── docs/                      📐 写作规范
│   ├── 内链规范.md
│   ├── 分类判定规则.md
│   └── wiki模板_造物.wiki
├── archive/                   旧脚本/旧批次/历史快照 zip（只读归档）
└── .workbuddy/                工程内部目录（脚本/状态/AI 记忆）
    ├── memory/
    │   ├── MEMORY.md          长期记忆（AI 维护，项目目标/架构/铁律）
    │   └── YYYY-MM-DD.md      每日工作日志
    ├── wide_window/           工程核心
    │   ├── context/           375 实体的原文 context（7.1M）
    │   ├── workstate.json     全局状态机
    │   ├── batch_extractor.py
    │   ├── batch_wiki_generator.py
    │   ├── qa_check.py        道统白名单校验
    │   ├── workflow.md        旧版工作流（参考）
    │   └── entity_ranking.json
    ├── phase0_*               启动期分类规则/数据
    └── Rescue3-质量抽查报告.md 最新 QA 报告
```

---

## 重构历史（2026-05-10）

- **频次目录 → 类型目录**：从 19 个 B 目录（频次分类）重构为 14 个类型目录
- **页数提升**：375 → 403 → 449
- **L 前缀清理**：所有线上页面标题已脱 L 前缀，433 个旧 L 前缀页已从 wiki 删除
- **裸名重复清理**：449 个裸名重复页面已删除（pageid 2300~2731）
- **品阶修正**：B11-B19/L6 共修正 65 处品阶/道统
- **P0 实体审计**：60 项审计 → 新增 28 页（含太阴月华深页 23.3KB）
- **历史快照**：`archive/历史快照_20260510.zip` 含旧 backup/ + pages_backup_freq_20260510/ + output_wiki/
