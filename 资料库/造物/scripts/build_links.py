#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
玄鉴仙族 Wiki · 内链建设脚本 v3
========================================

三阶段内链建设：

* **Phase A**：纠正命名空间错误的红链（旧 ``[[造物-X]]`` → 新 ``[[X]]`` 等）
* **Phase B**：造物互链（在条目正文为其它造物名添加首次提及链接）
* **Phase C**：人物链（为正文中提到的人物添加 ``[[人物-X]]`` 链接）

工作模式：审阅模式（生成 diff，确认后用 ``--apply`` 应用）。
保留原文书名号、info 表、Category 等保护区域。

路径策略：基于 ``_paths.py``，零硬编码，多机器协同安全。
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import (  # noqa: E402
    PAGES_DIR,
    PEOPLE_DIR,
    DIR_NS,
    SCRIPTS_DIR,
)

# ============================================================
# Phase A: 必须纠正的红链
# ============================================================
# (旧前缀, 新前缀)
PHASE_A_CORRECTIONS: dict[str, tuple[str, str]] = {
    "月华元府": ("造物", "势力"),
    "望月湖": ("造物", "地点"),
    "鉴中天地": ("造物", "地点"),
    "洞华天": ("造物", "地点"),
    "帝岐光": ("造物", "神通"),
    "大离赤熙光": ("造物", "神通"),
    "月桂衍化玄光": ("造物", "神通"),
}

# 文件名通常为 ``L{1-6}-实体名.wiki``，需要剥离前缀
L_PREFIX_PAT = re.compile(r"^L\d+-")


# ============================================================
# 实体索引构建
# ============================================================

def _strip_l_prefix(stem: str) -> str:
    """剥离文件名中的 ``L1-/L2-/...`` 品阶前缀。"""
    return L_PREFIX_PAT.sub("", stem)


def build_entity_index() -> dict[str, tuple[str, str, Path]]:
    """扫描造物 pages 目录，建立造物实体索引。

    Returns:
        ``{实体名: (命名空间前缀, 子目录名, 路径)}``。命名空间为空字符串表示无前缀。
    """
    index: dict[str, tuple[str, str, Path]] = {}
    for subdir in PAGES_DIR.iterdir():
        if not subdir.is_dir():
            continue
        if subdir.name not in DIR_NS:
            continue
        ns = DIR_NS[subdir.name]
        for fpath in subdir.glob("*.wiki"):
            entity = _strip_l_prefix(fpath.stem)
            index[entity] = (ns, subdir.name, fpath)
    return index


def build_people_index() -> dict[str, tuple[str, Path]]:
    """扫描主仓人物目录，建立人物索引。

    Returns:
        ``{人物名: ("人物", 路径)}``。
    """
    index: dict[str, tuple[str, Path]] = {}
    if not PEOPLE_DIR.is_dir():
        return index
    for fpath in PEOPLE_DIR.glob("*.wiki"):
        entity = fpath.stem
        index[entity] = ("人物", fpath)
    return index


# ============================================================
# 文本处理工具
# ============================================================

LINK_PAT = re.compile(r'\[\[([^\]|]+)(?:\|([^\]]*))?\]\]')


def extract_existing_links(text: str):
    """提取文本中所有 ``[[...]]`` 链接的位置。

    Yields:
        ``(full_match, target, display, start, end)``
    """
    results = []
    for m in LINK_PAT.finditer(text):
        target = m.group(1).strip()
        display = m.group(2).strip() if m.group(2) else target
        results.append((m.group(0), target, display, m.start(), m.end()))
    return results


def find_protected_spans(text: str):
    """识别需要跳过的文本区间（不在这些区间内做替换）。"""
    spans = []

    # 1. 原文引用区
    for m in re.finditer(r'== 原文引用 ==', text):
        start = m.start()
        next_title = re.search(r'\n== ', text[start + len(m.group(0)):])
        end = start + len(m.group(0)) + next_title.start() if next_title else len(text)
        spans.append((start, end, "原文引用区"))

    # 2. info 表
    for m in re.finditer(r'\{\|', text):
        start = m.start()
        end_match = re.search(r'\|\}', text[start:])
        if end_match:
            spans.append((start, start + end_match.end(), "info表"))

    # 3. Category 行
    for m in re.finditer(r'\[\[Category:[^\]]+\]\]', text):
        spans.append((m.start(), m.end(), "Category"))

    # 4. 章节标题
    for m in re.finditer(r'\n==+ [^=]+ ==+', text):
        spans.append((m.start(), m.end(), "章节标题"))

    # 5. 所属道统区
    for m in re.finditer(r'== 所属道统 ==', text):
        start = m.start()
        next_title = re.search(r'\n== ', text[start + len(m.group(0)):])
        end = start + len(m.group(0)) + next_title.start() if next_title else len(text)
        spans.append((start, end, "所属道统区"))

    return spans


def is_in_protected(pos: int, spans) -> bool:
    return any(start <= pos < end for start, end, _ in spans)


def is_inside_existing_link(pos: int, links) -> bool:
    return any(start <= pos < end for _, _, _, start, end in links)


def find_unlinked_mentions(
    text: str,
    entity: str,
    namespace: str,
    existing_links,
    protected_spans,
    self_entity: str,
):
    """在文本中查找某实体的首次未链接提及。

    Returns:
        ``(start, end, matched_text, replacement)`` 或 ``None``。
    """
    if entity == self_entity:
        return None

    # 优先匹配带书名号的【entity】，再匹配 [entity]，最后裸 entity（仅 ≥3 字）
    patterns = [
        (re.compile(re.escape(f'【{entity}】')), f'【{entity}】', True),
        (re.compile(re.escape(f'[{entity}]')), f'[{entity}]', True),
    ]
    if len(entity) >= 3:
        patterns.append((re.compile(re.escape(entity)), entity, False))

    for pattern, matched_text, _ in patterns:
        for m in pattern.finditer(text):
            start, end = m.start(), m.end()
            if is_in_protected(start, protected_spans):
                continue
            if is_inside_existing_link(start, existing_links):
                continue

            # 单方括号 [entity]：去掉括号显示
            if matched_text.startswith('[') and matched_text.endswith(']'):
                display = entity
            else:
                display = matched_text

            target = f'{namespace}-{entity}' if namespace else entity
            replacement = f'[[{target}|{display}]]'
            return (start, end, matched_text, replacement)

    return None


# ============================================================
# Phase A: 红链纠正
# ============================================================

def phase_a_fix_redlinks(text: str, fpath_str: str):
    """Phase A: 纠正命名空间错误的红链。"""
    changes = []
    new_text = text
    offset = 0

    for entity, (old_ns, new_ns) in PHASE_A_CORRECTIONS.items():
        old_link_prefix = f'[[{old_ns}-{entity}'
        for m in re.finditer(re.escape(old_link_prefix), text):
            start = m.start()
            end = m.end()
            following = text[end:end + 10]
            if not (following.startswith('|') or following.startswith(']]')):
                continue

            link_end = text.find(']]', end)
            if link_end == -1:
                continue
            full_old = text[start:link_end + 2]

            pipe_pos = full_old.find('|')
            display = full_old[pipe_pos + 1:-2] if pipe_pos != -1 else entity

            full_new = f'[[{new_ns}-{entity}|{display}]]'
            adj_start = start + offset
            adj_end = link_end + 2 + offset

            changes.append({
                'phase': 'A',
                'file': fpath_str,
                'old': full_old,
                'new': full_new,
                'reason': f'{old_ns}-{entity} → {new_ns}-{entity}'
            })
            new_text = new_text[:adj_start] + full_new + new_text[adj_end:]
            offset += len(full_new) - len(full_old)

    return new_text, changes


# ============================================================
# Phase B / C: 实体链接
# ============================================================

def _phase_link(
    text: str,
    fpath: Path,
    entity_index,
    self_entity: str,
    phase_label: str,
    reason_prefix: str,
    max_links: int,
):
    """通用阶段：从给定实体集合中为正文添加首次提及链接。"""
    changes = []
    new_text = text
    linked_in_page: set[str] = set()

    # 长名优先，避免子串误匹配
    entities = sorted(entity_index.items(), key=lambda kv: len(kv[0]), reverse=True)

    for entity, info in entities:
        if len(linked_in_page) >= max_links:
            break
        if entity in linked_in_page:
            continue
        ns = info[0]

        existing_links = extract_existing_links(new_text)
        protected_spans = find_protected_spans(new_text)
        result = find_unlinked_mentions(
            new_text, entity, ns, existing_links, protected_spans, self_entity
        )
        if result:
            start, end, matched_text, replacement = result
            changes.append({
                'phase': phase_label,
                'file': str(fpath),
                'old': matched_text,
                'new': replacement,
                'reason': f'{reason_prefix}: {entity}',
            })
            new_text = new_text[:start] + replacement + new_text[end:]
            linked_in_page.add(entity)

    return new_text, changes


def phase_b_creation_links(text, fpath, entity_index, self_entity, max_links=5):
    """Phase B: 造物互链。"""
    return _phase_link(text, fpath, entity_index, self_entity,
                       'B', '造物互链', max_links)


def phase_c_character_links(text, fpath, character_index, self_entity, max_links=5):
    """Phase C: 人物链。"""
    return _phase_link(text, fpath, character_index, self_entity,
                       'C', '人物链', max_links)


# ============================================================
# Diff 生成与主流程
# ============================================================

def generate_diff(original: str, modified: str, filepath: str) -> str:
    """生成 unified diff。"""
    o_lines = original.splitlines(keepends=True)
    m_lines = modified.splitlines(keepends=True)
    if o_lines and not o_lines[-1].endswith('\n'):
        o_lines[-1] += '\n'
    if m_lines and not m_lines[-1].endswith('\n'):
        m_lines[-1] += '\n'
    return ''.join(difflib.unified_diff(
        o_lines, m_lines, fromfile=filepath, tofile=filepath, lineterm='\n'
    ))


def main():
    parser = argparse.ArgumentParser(description='玄鉴仙族 Wiki · 内链建设')
    parser.add_argument('--phase', choices=['A', 'B', 'C', 'all'], default='all',
                        help='执行哪个阶段')
    parser.add_argument('--dry-run', action='store_true',
                        help='（默认行为）只生成 diff，不写入文件')
    parser.add_argument('--apply', action='store_true',
                        help='确认后直接应用修改')
    parser.add_argument('--output', type=str,
                        default=str(SCRIPTS_DIR / 'link_build_diff.txt'),
                        help='diff 输出文件路径')
    parser.add_argument('--max-per-page', type=int, default=5,
                        help='每页最大新增内链数')
    args = parser.parse_args()

    print("=" * 60)
    print("玄鉴仙族 Wiki · 内链建设 v3")
    print("=" * 60)

    print("\n[1/4] 构建实体索引...")
    creation_index = build_entity_index()
    character_index = build_people_index()
    print(f"    造物实体: {len(creation_index)}（来自 {PAGES_DIR}）")
    print(f"    人物实体: {len(character_index)}（来自 {PEOPLE_DIR}）")

    print("\n[2/4] 扫描造物页面...")
    all_changes = []
    modified_files: dict[str, tuple[str, str]] = {}

    for subdir in PAGES_DIR.iterdir():
        if not subdir.is_dir() or subdir.name not in DIR_NS:
            continue
        for fpath in subdir.glob("*.wiki"):
            entity = _strip_l_prefix(fpath.stem)
            original = fpath.read_text(encoding='utf-8')
            modified = original
            file_changes = []

            if args.phase in ('A', 'all'):
                modified, ch_a = phase_a_fix_redlinks(modified, str(fpath))
                file_changes.extend(ch_a)

            if args.phase in ('B', 'all'):
                modified, ch_b = phase_b_creation_links(
                    modified, fpath, creation_index,
                    entity, max_links=args.max_per_page,
                )
                file_changes.extend(ch_b)

            if args.phase in ('C', 'all'):
                b_count = sum(1 for c in file_changes if c['phase'] == 'B')
                remaining = max(0, args.max_per_page - b_count)
                modified, ch_c = phase_c_character_links(
                    modified, fpath, character_index,
                    entity, max_links=remaining,
                )
                file_changes.extend(ch_c)

            if file_changes:
                all_changes.extend(file_changes)
                modified_files[str(fpath)] = (original, modified)

    print(f"    扫描完成，涉及 {len(modified_files)} 个文件")

    print("\n[3/4] 生成 diff 报告...")
    summary: dict[str, int] = defaultdict(int)
    diff_parts = []
    for fpath, (orig, mod) in modified_files.items():
        diff = generate_diff(orig, mod, fpath)
        if diff:
            diff_parts.append(diff)
            diff_parts.append("\n")
    for ch in all_changes:
        summary[ch['phase']] += 1

    diff_text = ''.join(diff_parts)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(diff_text, encoding='utf-8')
    print(f"    diff 已保存至: {output_path}")
    print(f"    Phase A (红链纠正): {summary.get('A', 0)} 处")
    print(f"    Phase B (造物互链): {summary.get('B', 0)} 处")
    print(f"    Phase C (人物链): {summary.get('C', 0)} 处")

    json_path = output_path.with_suffix('.json')
    json_path.write_text(
        json.dumps(all_changes, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    print(f"    变更清单: {json_path}")

    if args.apply:
        print("\n[4/4] 应用修改...")
        for fpath, (_, mod) in modified_files.items():
            Path(fpath).write_text(mod, encoding='utf-8')
        print(f"    已修改 {len(modified_files)} 个文件")
    else:
        print("\n[4/4] 审阅模式 — 未应用修改")
        print(f"    请审阅 {output_path}，确认后加 --apply 执行")
    print("\n" + "=" * 60)


if __name__ == '__main__':
    main()
