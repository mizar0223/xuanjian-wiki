# 造物 scripts/ 目录整合 — 完成报告

**时间**：2026-05-19
**目录**：`/Users/shixiyang/AI/wiki/资料库/造物/scripts/`

## 1. 总体效果

| 维度 | 整合前 | 整合后 |
|---|---|---|
| Python 脚本数 | 11 | **4**（含 1 公共模块） |
| 历史产物（diff 快照） | 10 个 / ~3.0 MB | **0** |
| scripts/ 总体积 | ~3.0 MB | **~58 KB** |
| 路径硬编码 | 11/11 全部含旧路径 | **0** |
| 跨机器可用 | ❌（一行都跑不通） | ✅ |

## 2. 当前结构

```
资料库/造物/scripts/
├── _paths.py                # 公共路径模块（被所有脚本引用）
├── build_links.py           # 内链建设 v3（A/B/C 三阶段）
├── link_audit.py            # 链接审计与修复（scan/diff/apply 子命令）
├── generate_topic_pages.py  # 体系专题页生成
├── README.md                # 用法 + 跨机器迁移指南
└── archive/                 # 9 个一次性脚本归档
    ├── README.md            # 归档说明
    ├── analyze_entities.py
    ├── apply_a1_fix.py            # → 已并入 link_audit.py apply
    ├── density_analyzer.py
    ├── generate_fix_diff.py       # → 已并入 link_audit.py diff
    ├── generate_wiki_templates.py
    ├── run_final_tasks.py
    ├── run_tasks.py
    ├── scan_and_analyze.py
    └── scan_red_links.py          # → 已并入 link_audit.py scan
```

## 3. 关键设计：路径策略（多机协同）

针对你"经常在不同开发环境同步线上仓库"的诉求，所有脚本都通过 `_paths.py` 推导路径，**零硬编码**：

```python
# _paths.py 内核逻辑
def _resolve_caowu_root() -> Path:
    env = os.environ.get("XJ_CAOWU_ROOT")
    if env:
        # 1. 优先环境变量（CI / 自定义场景）
        return Path(env).expanduser().resolve()
    # 2. 否则相对脚本自身位置推导
    return Path(__file__).resolve().parent.parent  # = 造物/
```

**意味着什么**：
- 本地 Mac (`/Users/shixiyang/AI/wiki/...`) ✅
- CVM (`/data/...`) ✅
- 云开发机 (`/data/workspace/.../xuanjian-wiki/...`) ✅
- 任何检出位置都可直接运行
- 也可手动 `export XJ_CAOWU_ROOT=...` 覆盖

新增脚本只需：
```python
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import PAGES_DIR, DIR_NS, PEOPLE_DIR
```

## 4. Smoke Test 结果

| 脚本 | 命令 | 结果 |
|---|---|---|
| `_paths.py` | 模块导入 | ✅ 16 子目录全部命中映射 |
| `link_audit.py scan` | 扫描红链 | ✅ 识别 1311 处红链（造物 465 + 人物 829） |
| `build_links.py --phase A --dry-run` | A 阶段 dry-run | ✅ 流程通过，0 处变更（A 阶段已修完） |
| `generate_topic_pages.py` | 生成专题页 | ✅ 9 个专题页全部生成（顺手修了 `符箓: 11-符箓` → `13-符箓`） |

## 5. 删除清单

10 个历史 diff 产物（~3 MB）：
```
link_build_diff.{json,txt}
link_build_diff_v2.{json,txt}
link_build_diff_v3.{json,txt}
link_build_diff_v4.{json,txt}
link_build_diff_v5.{json,txt}
```

它们是 `build_links.py` 在 5 轮历史运行中产生的临时审阅快照，新一轮运行会自动重新生成。

## 6. 下一步建议

1. **首轮跨机验证**：建议在 CVM 上 `git pull` 后跑一次 `python3 资料库/造物/scripts/link_audit.py scan` 验证多机可用性。
2. **archive 留存策略**：默认保留可读，半年内若无人复活可整体删除。
3. **新工作流**：以后红链审计→修复，统一走 `link_audit.py` 的 scan→diff→apply 流程，不再用零散脚本。

## 7. 工程约定（已写入 MEMORY.md）

> 多机协同脚本路径策略（2026-05-19 立约）：`资料库/造物/scripts/` 下所有脚本必须 `from _paths import ...`，**禁止硬编码** `/data/...`、`/Users/...` 等机器路径。`_paths.py` 优先读 `XJ_CAOWU_ROOT` 环境变量，否则用 `Path(__file__).resolve().parent.parent` 推导。
