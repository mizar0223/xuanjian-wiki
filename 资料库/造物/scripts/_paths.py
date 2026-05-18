#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
玄鉴仙族 Wiki · 造物子项目 · 公共路径与目录映射模块

设计原则
--------
- 所有路径基于 ``Path(__file__).resolve()`` 反向推导，**不硬编码**任何机器路径，
  以适配多机协同（本地 Mac、CVM、云开发机等）。
- 解析顺序：环境变量 ``XJ_CAOWU_ROOT`` > 脚本相对路径 > 报错。
- 提供 16 类型目录映射 ``DIR_NS``，所有脚本共享同一份。
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# 路径解析
# ---------------------------------------------------------------------------

#: 脚本目录（即 ``资料库/造物/scripts``）
SCRIPTS_DIR: Path = Path(__file__).resolve().parent

#: 造物子项目根目录
#:
#: 优先级：
#: 1. 环境变量 ``XJ_CAOWU_ROOT``（适合 CI / 多机定制）
#: 2. 相对脚本目录的上一级（即 ``scripts/.. = 造物/``）
def _resolve_caowu_root() -> Path:
    env = os.environ.get("XJ_CAOWU_ROOT")
    if env:
        p = Path(env).expanduser().resolve()
        if (p / "pages").is_dir():
            return p
        raise RuntimeError(
            f"XJ_CAOWU_ROOT 指向的目录无效（缺少 pages/ 子目录）: {p}"
        )
    p = SCRIPTS_DIR.parent
    if (p / "pages").is_dir():
        return p
    raise RuntimeError(
        f"无法定位造物根目录：{p} 不含 pages/。\n"
        f"请将脚本置于 资料库/造物/scripts/ 下，或设置环境变量 XJ_CAOWU_ROOT。"
    )


CAOWU_ROOT: Path = _resolve_caowu_root()

#: 造物 pages 根目录（16 类型目录所在）
PAGES_DIR: Path = CAOWU_ROOT / "pages"

#: workbuddy 工作目录（存放分析报告、状态文件）
WORKBUDDY_DIR: Path = CAOWU_ROOT / ".workbuddy"

#: 宽窗 context 数据目录
WIDE_WINDOW_DIR: Path = WORKBUDDY_DIR / "wide_window"

#: 主仓 wiki 根（造物 -> 资料库 -> wiki 根）
WIKI_ROOT: Path = CAOWU_ROOT.parent.parent

#: 主仓人物等其他维度 pages 目录
WIKI_PAGES_DIR: Path = WIKI_ROOT / "pages"

#: 主仓人物条目目录（含 ``人物-`` 前缀页面）
PEOPLE_DIR: Path = WIKI_PAGES_DIR / "人物与势力"

#: 主仓仙基道统条目目录
DAOTONG_DIR: Path = WIKI_PAGES_DIR / "仙基道统"


# ---------------------------------------------------------------------------
# 16 类型目录映射（造物 pages/ 子目录 → 命名空间前缀）
# ---------------------------------------------------------------------------
#
# 当前策略（2026-05-12 统一）：
#   - 造物维度全部 **无前缀**（线上保留 ``造物-X`` 重定向兜底，不破链）
#   - 人物维度仍使用 ``人物-`` 前缀（在主仓 pages/人物与势力/，不在本目录下）
#   - 故本字典中所有目录命名空间均为 ``""``（空字符串=无前缀）
#
# 历史变更记录：
#   - 2026-05-11 之前：使用 ``造物-`` 前缀，导致 454 对重复页面
#   - 2026-05-12：统一为无前缀，已清理 267 个 move 重定向

DIR_NS: dict[str, str] = {
    "00-体系": "",
    "01-灵气": "",
    "02-灵物": "",
    "03-灵资": "",
    "04-丹药": "",
    "05-法器": "",
    "06-灵器": "",
    "07-灵宝": "",
    "08-法宝": "",
    "09-位别": "",
    "10-仙器": "",
    "11-符箓": "",
    "12-材料": "",
    "13-法术秘法": "",
    "13-符箓": "",   # 兼容旧目录名（如有遗留）
    "14-待分类": "",
}


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def page_title(wiki_file: Path) -> str:
    """根据 .wiki 文件路径推断线上页面标题。

    规则：``资料库/造物/pages/<子目录>/<filename>.wiki`` →
    若该子目录在 ``DIR_NS`` 中且前缀非空，则返回 ``<前缀>-<filename>``，
    否则返回 ``<filename>``。

    注意：文件名中可能含 ``L1-/L2-/...`` 等品阶前缀，本函数 **不会** 自动剥离，
    调用方需自行处理（参考各脚本约定）。
    """
    rel = wiki_file.relative_to(PAGES_DIR)
    parts = rel.parts
    if len(parts) < 2:
        return wiki_file.stem
    ns = DIR_NS.get(parts[0], "")
    stem = wiki_file.stem
    return f"{ns}-{stem}" if ns else stem


def iter_pages():
    """遍历所有造物 .wiki 文件，按目录字典序、文件名字典序产出。

    Yields:
        Path: 每个 ``.wiki`` 文件的绝对路径。
    """
    for subdir in sorted(PAGES_DIR.iterdir()):
        if not subdir.is_dir():
            continue
        if subdir.name not in DIR_NS:
            continue
        for wiki in sorted(subdir.glob("*.wiki")):
            yield wiki


__all__ = [
    "SCRIPTS_DIR",
    "CAOWU_ROOT",
    "PAGES_DIR",
    "WORKBUDDY_DIR",
    "WIDE_WINDOW_DIR",
    "WIKI_ROOT",
    "WIKI_PAGES_DIR",
    "PEOPLE_DIR",
    "DAOTONG_DIR",
    "DIR_NS",
    "page_title",
    "iter_pages",
]
