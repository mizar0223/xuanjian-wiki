# 归档脚本（archive/）

本目录存放历史一次性任务脚本，**不再调用，仅为留存可读**。整合发生于 2026-05-19。

## 文件清单

### 已合并（功能整合到 ../link_audit.py）

| 旧脚本 | 新位置 | 子命令 |
|---|---|---|
| `scan_red_links.py` | `link_audit.py` | `scan` |
| `generate_fix_diff.py` | `link_audit.py` | `diff` |
| `apply_a1_fix.py` | `link_audit.py` | `apply` |

### 已废弃（一次性任务，已完成）

| 脚本 | 用途 |
|---|---|
| `analyze_entities.py` | 早期实体扫描 |
| `scan_and_analyze.py` | 缺失页面 + 低频实体密度分析 |
| `density_analyzer.py` | 上下文密度分析 + 新页面提取 |
| `run_tasks.py` | 双任务执行 v1 |
| `run_final_tasks.py` | 双任务执行 final 版 |
| `generate_wiki_templates.py` | 9 新页 + 47 高密度低频实体底版生成 |

## 已知问题（如要复活）

1. **路径硬编码**：所有归档脚本均含 `/data/workspace/rq0rlzeg/...` 旧路径，复活前需替换为引用 `../_paths.py`。
2. **目录映射过期**：A 簇脚本依赖的 `02-灵物-灵资 / 03-丹药 / 04-灵器 / ...` 目录已不存在；当前结构为 16 类型目录（`02-灵物 / 03-灵资 / 05-法器 / 06-灵器 / ...`）。
3. **数据依赖**：A 簇脚本依赖 `.workbuddy/wide_window/workstate.json` 与 `entity_ranking.json`，使用前请确认数据未失效。

如确实需要再跑一遍，建议优先复活 `run_final_tasks.py`（最新版本，覆盖 run_tasks 与 analyze_entities）。
