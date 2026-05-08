# 玄鉴仙族维基 (Xuanjian Wiki)

> MediaWiki 驱动的《玄鉴仙族》小说百科全书

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
| 首页设计 + 导航完善 | 🔲 待做 | - |
| 分类体系优化 | 🔲 待做 | - |
| 人物关系图可视化 | 🔲 待做 | - |
| 图片资源上传 | 🔲 待做 | - |
| SemanticMediaWiki 扩展 | 🔲 待做 | - |

## 目录结构

```
wiki/
├── README.md           # 本文件
├── config.yaml         # 项目配置（非敏感）
├── .env                # 敏感密码（不入版本控制）
├── .gitignore
├── scripts/            # 脚本工具
│   ├── generate_pages.py   # 数据源 → .wiki 文件生成器（654行）
│   ├── upload_pages.py     # .wiki 文件 → MW API 批量上传（151行）
│   ├── wiki_admin.py       # 管理工具（统计/查询/搜索/删除）
│   └── ssh_wiki.sh         # SSH 快捷连接脚本
├── pages/              # MediaWiki 源文件（按类型归档）
│   ├── 人物与势力/       # 人物/势力等正文页面
│   ├── 索引/             # 索引页
│   └── 仙基道统/         # 仙基、道统、神通独立页面
│       ├── 位业/
│       ├── 道统/
│       └── 神通/
├── data/               # 结构化数据（JSON/YAML）
├── backup/             # XML 导出备份
│   └── xuanjian_import.xml  # 完整 XML 导出（484K）
└── docs/               # 文档
    └── LESSONS.md      # 踩坑记录
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

# 上传所有页面到 wiki
python3 scripts/upload_pages.py

# dry-run（只预览不上传）
python3 scripts/upload_pages.py --dry-run
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

## 数据源

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
