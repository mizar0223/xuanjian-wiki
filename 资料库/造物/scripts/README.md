# 造物子项目脚本目录

> 整合时间：2026-05-19。从 11 个零散脚本 + 10 个历史 diff 文件，整合为 4 个核心脚本 + 1 个公共模块。

## 设计原则

**多机协同安全**：所有脚本通过 `_paths.py` 推导路径，**零硬编码**：

1. 优先读取环境变量 `XJ_CAOWU_ROOT`
2. 否则使用 `Path(__file__).resolve().parent.parent`（即 `scripts/.. = 造物/`）

这意味着脚本可以在本地 Mac、CVM、云开发机等任何位置直接运行，无需修改路径。

## 当前脚本

```
scripts/
├── _paths.py              # 公共路径与目录映射（被所有脚本引用）
├── build_links.py         # 内链建设（A/B/C 三阶段，审阅模式）
├── link_audit.py          # 链接审计与修复（scan / diff / apply 三子命令）
├── generate_topic_pages.py # 体系专题页生成（00-体系/）
├── archive/               # 归档：一次性任务脚本（详见 archive/README.md）
└── README.md              # 本文件
```

## 用法速查

### 内链建设

```bash
# 审阅模式（生成 diff，不写入）
python3 scripts/build_links.py --phase all

# 仅 A 阶段（红链纠正）
python3 scripts/build_links.py --phase A

# 应用变更
python3 scripts/build_links.py --phase all --apply
```

### 红链审计与修复

```bash
# 扫描红链 → .workbuddy/red_links_report.md
python3 scripts/link_audit.py scan

# 生成 A1+A2 修复 diff 审阅 → .workbuddy/red_links_fix_diff.md
python3 scripts/link_audit.py diff

# 直接应用 A1 人物前缀修复（需 --confirm）
python3 scripts/link_audit.py apply --confirm
```

### 体系专题页生成

```bash
# 重新生成 pages/00-体系/ 下的品类专题页
python3 scripts/generate_topic_pages.py
```

## 跨机器迁移注意事项

### 默认情况

无需任何配置。脚本会自动定位到 `scripts/../` 作为造物根。
只要保持目录结构完整，在任何机器上都能直接运行。

### 自定义根目录

如需在非常规位置使用（如 CI、临时检出），可设置环境变量：

```bash
export XJ_CAOWU_ROOT=/path/to/资料库/造物
python3 scripts/build_links.py --phase all
```

### 目录依赖

| 脚本 | 必须存在的目录 |
|---|---|
| build_links.py | `资料库/造物/pages/`<br>`pages/人物与势力/`（主仓） |
| link_audit.py | `资料库/造物/pages/`<br>`pages/人物与势力/`（主仓，可选） |
| generate_topic_pages.py | `资料库/造物/pages/{各品类目录}/` |

## 16 类型目录映射（DIR_NS）

当前所有造物条目使用**无前缀**策略（线上 `造物-X` 重定向兜底）：

| 子目录 | 命名空间 | 用途 |
|---|---|---|
| 00-体系 | （无前缀） | 体系/专题页 |
| 01-灵气 ~ 14-待分类 | （无前缀） | 16 类型条目 |

> 历史变更：2026-05-12 之前使用 `造物-` 前缀，导致 454 对重复页面。整合后已统一为无前缀。

## 未来扩展指南

新增脚本时请遵循：

1. 第一行写 shebang `#!/usr/bin/env python3`，文件头加 docstring
2. **不要硬编码路径**，统一从 `_paths.py` 导入：
   ```python
   sys.path.insert(0, str(Path(__file__).resolve().parent))
   from _paths import PAGES_DIR, DIR_NS  # noqa: E402
   ```
3. 输出文件优先放 `_paths.WORKBUDDY_DIR`（即 `.workbuddy/`）
4. 临时产物（diff 快照等）放 `scripts/` 自身目录，但**及时清理**避免膨胀

## 与归档脚本的关系

`archive/` 中的 9 个旧脚本均含旧路径 `/data/workspace/rq0rlzeg/...`，且依赖的目录映射已过期。
**不要直接调用**，仅供考据查阅。如有需要复活，请参考 `archive/README.md` 的迁移提示。
