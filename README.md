# 玄鉴仙族维基 (Xuanjian Wiki)

> MediaWiki 驱动的《玄鉴仙族》小说百科全书

## 代码仓库

- **工蜂**: https://git.woa.com/leoshixie/xuanjian-wiki

## 在线访问

- **Wiki 首页**: http://leoshixie.devcloud.woa.com/wiki/首页
- **API 端点**: http://leoshixie.devcloud.woa.com/api.php

## 项目进度

| 里程碑 | 状态 | 日期 |
|--------|------|------|
| 方案研究（6种方案对比） | ✅ 完成 | 2026-05-07 |
| MediaWiki Docker 部署 | ✅ 完成 | 2026-05-07 |
| Nginx 反代 + API 暴露 | ✅ 完成 | 2026-05-07 |
| 基础模板创建（角色 Infobox） | ✅ 完成 | 2026-05-07 |
| 354 角色/势力页面批量导入 | ✅ 完成 | 2026-05-07 |
| 仙基道统神通页面生成 | ✅ 完成 | 2026-05-08 |
| 神通资料库建设（OCR + 考据） | ✅ 完成 | 2026-05-08 |
| 五德位业体系结构化 | ✅ 完成 | 2026-05-08 |
| 参考权威资料归档与索引 | ✅ 完成 | 2026-05-09 |
| 首页设计 + 导航完善 | 🔲 待做 | - |
| 分类体系优化 | 🔲 待做 | - |
| 人物关系图可视化 | 🔲 待做 | - |
| 图片资源上传 | 🔲 待做 | - |
| SemanticMediaWiki 扩展 | 🔲 待做 | - |

## 目录结构

```
wiki/
├── README.md               # 本文件
├── config.yaml             # 项目配置（非敏感）
├── .env                    # 敏感密码（不入版本控制）
├── .gitignore
├── scripts/                # 脚本工具
│   ├── generate_pages.py       # 数据源 → .wiki 文件生成器
│   ├── generate_xianji_pages.py # 仙基道统神通页面生成器
│   ├── setup_smw_properties.py  # SemanticMW 属性配置
│   ├── upload_pages.py         # .wiki 文件 → MW API 批量上传
│   ├── upload_images.py        # 图片批量上传
│   ├── wiki_admin.py           # 管理工具（统计/查询/搜索/删除）
│   └── ssh_wiki.sh             # SSH 快捷连接脚本
├── pages/                  # MediaWiki 源文件（按类型归档）
│   ├── 人物与势力/           # 人物/势力等正文页面
│   ├── 索引/                 # 索引页
│   └── 仙基道统/             # 仙基、道统、神通独立页面
│       ├── 位业/
│       ├── 道统/
│       └── 神通/
├── 资料库 - 神通/           # 神通体系完整资料库
│   ├── 01_原始素材/          # 原始图片、百科全书 HTML
│   ├── 02_加工产出/          # OCR 转录、清洗文本
│   ├── 03_校对与核对/        # 核对报告、校正记录
│   └── 04_参考权威/          # 权威参考资料（已按资料族归档并建立索引）
│       ├── 00_索引与说明/    # 文件索引、CSV 索引、SOP、结构说明
│       ├── 01_神通仙基_外部来源与展示/
│       ├── 02_五德位业体系_主数据/
│       ├── 03_原文考据/
│       ├── 04_文化考据/
│       └── 99_历史备份_待核验/
├── data/                   # 结构化数据（JSON/YAML）
├── backup/                 # XML 导出备份
└── docs/                   # 文档
    ├── LESSONS.md              # 踩坑记录
    └── wiki_competitive_analysis.md  # 竞品分析
```

## 技术架构

```
┌─── 本地 ───────────────────────────┐     ┌─── CVM (21.214.75.44) ───────────┐
│                                     │     │                                    │
│  数据源 → generate_pages.py         │     │  Nginx (:80)                       │
│       ↓                             │     │    ├─ /wiki/  → MediaWiki(:8081)   │
│  pages/*.wiki                       │     │    ├─ /api.php → MediaWiki(:8081)  │
│       ↓                             │     │    └─ /load.php, /index.php ...    │
│  upload_pages.py ──── HTTP ─────────┼────→│                                    │
│                                     │     │  Docker: mediawiki:1.42            │
│  wiki_admin.py ──── HTTP ───────────┼────→│    └─ Apache + PHP 8.1            │
│                                     │     │                                    │
│  ssh_wiki.sh ──── SSH :36000 ───────┼────→│  Docker: mysql:8.0 (wikidb)       │
│                                     │     │                                    │
└─────────────────────────────────────┘     └────────────────────────────────────┘
```

## 常用操作

### SSH 连接 CVM

```bash
# 端口是 36000，不是 22！
./scripts/ssh_wiki.sh
# 或手动：
ssh -p 36000 root@21.214.75.44
```

### Wiki 管理

```bash
# 查看统计
python3 scripts/wiki_admin.py stats

# 列出页面
python3 scripts/wiki_admin.py list

# 搜索
python3 scripts/wiki_admin.py search "李承晦"

# 查看页面源码
python3 scripts/wiki_admin.py get "李绛迁"

# 列出所有分类
python3 scripts/wiki_admin.py categories
```

### 批量操作

```bash
# 重新生成所有页面（从数据源）
python3 scripts/generate_pages.py

# 生成仙基道统神通页面
python3 scripts/generate_xianji_pages.py

# 上传所有页面到 wiki（递归扫描 pages/）
python3 scripts/upload_pages.py

# dry-run（只预览不上传）
python3 scripts/upload_pages.py --dry-run

# 只上传指定目录（可重复 --only）
python3 scripts/upload_pages.py \
  --only pages/仙基道统/道统 \
  --only pages/仙基道统/神通

# 只上传单个页面文件
python3 scripts/upload_pages.py --only pages/仙基道统/神通/神通-君蹈危.wiki
```

### Docker 维护（在 CVM 上）

```bash
# 查看 MW 容器状态
docker ps | grep mediawiki

# 查看 MW 日志
docker logs mediawiki --tail 50

# 编辑 LocalSettings.php
docker exec -it mediawiki vi /var/www/html/LocalSettings.php

# 重启 MW
docker restart mediawiki

# 重载 Nginx
nginx -t && nginx -s reload
```

## 资料库说明

### 神通资料库 (`资料库 - 神通/`)

完整的神通体系资料加工流水线：

| 阶段 | 目录 | 内容 |
|------|------|------|
| 原始素材 | `01_原始素材/` | 神通图片（9张）、中文百科全书 HTML、释修体系图片 |
| 加工产出 | `02_加工产出/` | OCR 转录文本、百科全书清洗版 |
| 校对核对 | `03_校对与核对/` | 核对报告、本地对照、清洗总结 |
| 参考权威 | `04_参考权威/` | 按资料族归档的五德位业、神通仙基、原文考据、文化考据；索引见 `04_参考权威/00_索引与说明/文件索引.md` |

### 数据源

| 源文件 | 条目数 | 内容 |
|--------|--------|------|
| `characters/人物年鉴进度.json` | 41 | 核心角色基本信息 |
| `characters/望月李氏家谱.md` | 72 | 李氏家谱世系 |
| `characters/*/content/*_NotebookLM素材.md` | 23 | 深度角色分析 |
| `玄鉴图册/角色.md` | 30 | 非李族角色设定 |
| `玄鉴图册/出场群像.md` | 303 | 群众演员信息 |

数据源位于: `/Users/leoshi/WorkBuddy/20260323190937/`

## 模板系统

### `{{角色}}` Infobox

支持字段: 姓名 / 字辈 / 族系 / 世代 / 修为 / 道统 / 仙基 / 身份 / 师承 / 父亲 / 母亲 / 配偶 / 子嗣 / 首次出场 / 状态

```wiki
{{角色
|姓名=李绛迁
|字辈=绛阙辈
|族系=望月李氏
|修为=筑基初期
|仙基=大离书
|父亲=李周巍
}}
```

## 账号信息

| 项目 | 值 |
|------|-----|
| Wiki 管理员 | WikiAdmin |
| anydev 环境 ID | evnIns-6h90vw7jeohg |
| CVM IP | 21.214.75.44 |
| SSH 端口 | 36000 |
| MW 容器端口 | 8081→80 |

密码见 `.env` 文件（不入版本控制）
