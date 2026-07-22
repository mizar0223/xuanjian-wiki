# 玄鉴仙族维基 (Xuanjian Wiki)

> MediaWiki 驱动的《玄鉴仙族》小说百科全书 · **1559 页** · **2 维度** · **14 种实体类型**

## 代码仓库

- **GitHub**: https://github.com/mizar0223/xuanjian-wiki

## 在线访问

- **Wiki 首页**: http://9433.com.cn/wiki/首页
- **API 端点**: http://9433.com.cn/api.php

---

## 项目概览

本项目是对起点中文网小说《玄鉴仙族》的系统化百科建设，覆盖 **造物** 与 **人物** 两大维度：

| 维度 | 页数 | 实体类型 | 状态 |
|------|------|----------|------|
| 造物（法宝/道具/灵资） | 460 | 13 类造物 + 1 类人物 | ✅ 已发布 |
| 人物与势力 | 1099 | 角色 / 势力 / 仙基 / 道统 / 神通 | ✅ 已发布 |

**造物维度**包含：灵气(14) / 灵物灵资(181) / 丹药(8) / 灵器(45) / 灵宝(69) / 古灵器(17) / 筑基法器(40) / 符箓(1) / 法宝(7) / 材料(32) / 法术秘法(2) / 其他(4) / 待分类(13) / 人物(16) + 消歧页等。

---

## 技术架构

```
┌─── 本地 ───────────────────────────┐     ┌─── 服务器 (114.132.222.8) ────────┐
│                                     │     │                                    │
│  数据源 → generate_pages.py         │     │  Nginx (:80)                       │
│       ↓                             │     │    ├─ /wiki/  → MediaWiki(:8081)   │
│  pages/*.wiki                       │     │    ├─ /api.php → MediaWiki(:8081)  │
│       ↓                             │     │    └─ /load.php, /index.php ...    │
│  upload_pages.py ──── HTTP ─────────┼────→│                                    │
│                                     │     │  Docker: mediawiki:1.42            │
│  wiki_admin.py ──── HTTP ───────────┼────→│    └─ Apache + PHP 8.1            │
│                                     │     │                                    │
│  ssh_wiki.sh ──── SSH :22 ──────────┼────→│  Docker: mysql:8.0 (wikidb)       │
│                                     │     │                                    │
└─────────────────────────────────────┘     └────────────────────────────────────┘
```

- **引擎**: MediaWiki 1.42.7 + Vector 2022 皮肤
- **后端**: Nginx (反向代理) + Apache 2.4 + PHP 8.1 (Docker)
- **数据库**: MySQL 8.0 (Docker)
- **扩展**: ParserFunctions / SemanticMediaWiki (规划中)
- **管线**: 数据源 → Python 生成器 → .wiki 文件 → API 批量上传

---

## 目录结构

```
wiki/
├── README.md                       # 本文件
├── config.yaml                     # 项目配置（非敏感）
├── .env                            # 敏感密码（不入版本控制）
├── scripts/                        # 脚本工具
│   ├── generate_pages.py               # 数据源 → .wiki 文件生成器（人物维度）
│   ├── generate_xianji_pages.py        # 仙基道统神通页面生成器
│   ├── parse_encyclopedia_html.py      # 百度百科 HTML 解析器
│   ├── upload_pages.py                 # .wiki → MW API 批量上传（含前缀映射）
│   ├── upload_images.py                # 图片批量上传
│   ├── wiki_admin.py                   # 管理工具（统计/查询/搜索/删除）
│   ├── setup_smw_properties.py         # SemanticMediaWiki 属性配置
│   ├── ssh_wiki.sh                     # SSH 快捷连接
│   ├── deploy-wiki.sh                  # 配置/资源发布 + docker restart（agent-friendly）
│   └── common/                         # 共享配置模块
├── pages/                          # 人物维度 MediaWiki 源文件（1099 页）
│   ├── 人物与势力/                      # 角色/势力正文页面
│   ├── 仙基道统/                        # 仙基/道统/神通/位业独立页面
│   │   ├── 道统/
│   │   ├── 神通/
│   │   └── 位业/
│   └── 索引/                            # 索引页
├── 资料库/                        # 统一资料库入口
│   ├── 神通/                      # 神通体系资料库
│   │   ├── 01_原始素材/                      # 原始图片、百科全书 HTML
│   │   ├── 02_加工产出/                      # OCR 转录、清洗文本
│   │   ├── 03_校对与核对/                    # 核对报告、校正记录
│   │   └── 04_参考权威/                      # 按资料族归档的权威参考
│   └── 造物/                      # 造物维度完整工程（460 页）
│       ├── README.md                        # 造物维度专用 README
│       ├── WORKFLOW.md                      # 造物维度工作流 SOP
│       ├── pages/                           # 460 页 wiki 产物（按 14 类型子目录）
│       ├── docs/                            # 写作规范（内链/分类/模板/品阶）
│       ├── archive/                         # 旧脚本/旧批次/历史快照
│       └── .workbuddy/                      # 工程内部（脚本/状态/AI 记忆）
├── data/                           # 结构化数据（JSON/YAML）
├── backup/                         # XML 导出备份
├── output/                         # 中间产出（gitignore，不入版本控制）
└── docs/                           # 项目文档
    ├── LESSONS.md                       # 踩坑记录
    └── wiki_competitive_analysis.md     # 竞品分析
```

---

## 快速开始

### 前置条件

- Python 3.6+ / requests / PyYAML
- SSH 客户端
- `.env` 文件（含 WIKI_USER / WIKI_PASS，不随仓库分发）

### 常用操作

**SSH 连接服务器**
```bash
./scripts/ssh_wiki.sh
# 或手动：ssh -i /Users/leoshi/WorkBuddy/2026-05-15-task-13/forAI.pem root@114.132.222.8
```

**Wiki 管理**
```bash
python3 scripts/wiki_admin.py stats          # 查看统计
python3 scripts/wiki_admin.py search "李承晦" # 搜索
python3 scripts/wiki_admin.py get "李绛迁"    # 查看页面源码
python3 scripts/wiki_admin.py categories      # 列出所有分类
```

**批量上传**
```bash
# 上传人物维度所有页面
python3 scripts/upload_pages.py

# 仅上传指定目录
python3 scripts/upload_pages.py --only pages/仙基道统/道统

# 上传造物维度
python3 scripts/upload_pages.py --only "资料库/造物/pages"

# 预览不上传
python3 scripts/upload_pages.py --dry-run
```

**Docker 维护（在 CVM 上）**
```bash
docker ps | grep mediawiki               # 容器状态
docker logs mediawiki --tail 50          # 查看日志
docker exec -it mediawiki vi /var/www/html/LocalSettings.php  # 编辑配置
docker restart mediawiki                 # 重启
nginx -t && nginx -s reload              # 重载 Nginx
```

**配置/资源发布（推荐，agent-friendly）**
```bash
# 推送 LocalSettings.php / .htaccess / apache-wiki-alias.conf / resources-assets/
# 到 /opt/mediawiki/，然后 docker compose restart mediawiki
./scripts/deploy-wiki.sh --dry-run       # 预览
./scripts/deploy-wiki.sh                 # 实际部署 + 健康检查
./scripts/deploy-wiki.sh --no-restart    # 只推文件不重启
./scripts/deploy-wiki.sh --include-images  # 含 mw_images（88M+，慎用）
```

> 依赖：仓库根目录下需有 `opt/mediawiki/` 作为本地源（含 `LocalSettings.php` 等）。
> 当前仓库未追踪该目录，首次使用前先用 `ssh_wiki.sh` 上去 `scp` 一份到本地，或在初始化时建空目录。

---

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

### `{{造物}}` Infobox

支持字段: 名称 / 品阶 / 道统 / 类型 / 持有者 / 相关人物 / 出现章节

---

## 核心规范

### 品阶三同步铁律

每页必须三处品阶一致：info 表 / 首句 / Category。详见 [造物维度 WORKFLOW](资料库/造物/WORKFLOW.md)。

### 内链规范

- 造物页使用 `[[造物-实体名]]` 格式
- 人物页使用 `[[人物-实体名]]` 格式
- 保留书名号《》用于功法/经文名称
- 详见 [内链规范](资料库/造物/docs/内链规范.md)

### 文件命名规则（造物维度）

```
pages/{NN-类型}/L{1-6}-{实体名}.wiki

L1 = 高频核心（88-49 次）  L2 = 中高频（49-20 次）
L3 = 中频（19-15 次）      L4 = 中低频（9-5 次）
L5 = 低频（4-2 次）        L6 = 仅 1 次
```

L 前缀仅用于文件名，上传脚本自动生成不带 L 的线上标题。

---

## 项目里程碑

| 里程碑 | 状态 | 日期 |
|--------|------|------|
| 方案研究（6 种方案对比） | ✅ 完成 | 2026-05-07 |
| MediaWiki Docker 部署 | ✅ 完成 | 2026-05-07 |
| Nginx 反代 + API 暴露 | ✅ 完成 | 2026-05-07 |
| 基础模板创建（角色 Infobox） | ✅ 完成 | 2026-05-07 |
| 354 角色/势力页面批量导入 | ✅ 完成 | 2026-05-07 |
| 仙基道统神通页面生成 | ✅ 完成 | 2026-05-08 |
| 神通资料库建设（OCR + 考据） | ✅ 完成 | 2026-05-08 |
| 五德位业体系结构化 | ✅ 完成 | 2026-05-08 |
| 参考权威资料归档与索引 | ✅ 完成 | 2026-05-09 |
| 造物维度 449 页全量产出 | ✅ 完成 | 2026-05-10 |
| 造物维度重构（频次→类型目录） | ✅ 完成 | 2026-05-10 |
| 跨命名空间消歧页（7 个） | ✅ 完成 | 2026-05-10 |
| 首页设计 + 导航完善 | 🔲 待做 | - |
| 分类体系优化 | 🔲 待做 | - |
| 人物关系图可视化 | 🔲 待做 | - |
| 图片资源上传 | 🔲 待做 | - |
| SemanticMediaWiki 扩展 | ✅ 完成 | 2026-07-22 |

---

## SemanticMediaWiki（2026-07-22 上线）

### 版本与组成

| 项 | 值 |
|----|-----|
| SMW 版本 | `mediawiki/semantic-media-wiki ~5.0.2`（兼容 MW 1.39–1.43.1 / PHP 8.1–8.4） |
| 安装方式 | composer（容器内 `php /tmp/composer update --no-dev --no-security-blocking --optimize-autoloader`） |
| 持久化 | `volumes/vendor` + `volumes/extensions` 整体挂载（composer 产物不随容器重建丢失） |
| 声明文件 | `composer.local.json`（`require` SMW，git 跟踪） |
| 加载配置 | `LocalSettings.php`：`wfLoadExtension('SemanticMediaWiki'); enableSemantics('9433.com.cn');` |
| 命名空间 | 属性(102) / 概念(108) / 语义表单(106) 等 |

### 运维命令（容器内执行）

```bash
# 数据库结构升级（装/升 SMW 后必跑；站点会停在 SMW 维护页直到跑完）
docker exec mw-app php maintenance/run.php update.php --quick

# 全量语义数据重建（约 3784 页 / 数分钟；页面批量导入后跑）
docker exec -d mw-app bash -c "php extensions/SemanticMediaWiki/maintenance/rebuildData.php -d 50 -v > /tmp/rebuild.log 2>&1"
```

### 排障要点（2026-07-22 实战记录）

1. **容器重建即丢**：`/tmp/*`、apt 装的包、容器内 composer.json 修改全部失效——vendor/extensions 已挂载持久，其余都别依赖。
2. **composer 装包前置**：容器内先 `mkdir -p /var/lib/apt/lists/partial && apt-get update && apt-get install -y unzip`（ composer 解压依赖 unzip；容器 apt 缓存为空时 install 会静默失败）。
3. **镜像自带 composer.json 的坑**：`require-dev`（phpunit 等）触发安全公告阻塞 → 需删除 require-dev 段；再加 `--no-security-blocking`（或 config 写 `policy.advisories.block=false`）。
4. **内存**：`mem_limit` 已从 512m 提至 1900m（2G 机器）。composer update 期间单容器峰值可超 1.5G，OOM(137) 就降并发分开跑。
5. **deploy-wiki.sh 本地渲染凭据可能过期**：正确姿势 = scp 占位符版 → 服务器上用 `/opt/mediawiki/.env` 真值 sed 渲染（见脚本 RENDER_PLACEHOLDERS）。
6. **SMW 维护页（503）**：扩展加载但未跑 update.php 时全站 503 + SMW 升级页，跑完 update.php 自动恢复。

### #ask 查询示例

```
# 紫府人物一览（自动表格）
{{#ask:[[属性:修为::~*紫府*]]|?修为|?道统|?所属势力|mainlabel=人物|limit=500|class=wikitable sortable}}

# 计数
{{#ask:[[属性:修为::~*紫府*]]|format=count}}
```

成品页：`wiki/紫府人物`（pages/索引/紫府人物.wiki）

---

## 账号信息

| 项目 | 值 |
|------|-----|
| Wiki 管理员 | WikiAdmin |
| 服务器域名 | 9433.com.cn |
| 服务器 IP | 114.132.222.8 |
| SSH 端口 | 22 |
| SSH 用户 | root |
| SSH 密钥 | forAI.pem |
| MW 容器端口 | 8081→80 |

密码见 `.env` 文件（不入版本控制）
