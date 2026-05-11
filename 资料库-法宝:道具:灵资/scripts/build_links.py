#!/usr/bin/env python3
"""
玄鉴仙族 Wiki · 内链建设脚本 v2
方案1：A红链纠正 + B造物互链 + C人物链
保留书名号，审阅模式（先生成diff，确认后apply）
"""

import os
import re
import json
import difflib
import argparse
from pathlib import Path
from collections import defaultdict

PAGES_DIR = Path("/Users/leoshi/AIBOOK/xuanjian/wiki/资料库-法宝:道具:灵资/pages")

DIR_NS = {
    "01-灵气": "造物",
    "02-灵物-灵资": "造物",
    "03-丹药": "造物",
    "04-灵器": "造物",
    "05-灵宝": "造物",
    "06-古灵器": "造物",
    "07-筑基法器": "造物",
    "08-符箓": "造物",
    "09-法宝": "造物",
    "10-材料": "造物",
    "11-法术秘法": "造物",
    "12-其他": "造物",
    "13-待分类": "造物",
    "20-人物": "人物",
}

# Phase A: 必须纠正的红链
PHASE_A_CORRECTIONS = {
    "月华元府": ("造物", "势力"),
    "望月湖": ("造物", "地点"),
    "鉴中天地": ("造物", "地点"),
    "洞华天": ("造物", "地点"),
    "帝岐光": ("造物", "神通"),
    "大离赤熙光": ("造物", "神通"),
    "月桂衍化玄光": ("造物", "神通"),
}


def build_entity_index():
    """扫描pages目录，建立实体索引 {实体名: (命名空间, 目录, 路径)}"""
    index = {}
    for subdir in PAGES_DIR.iterdir():
        if not subdir.is_dir():
            continue
        ns = DIR_NS.get(subdir.name)
        if not ns:
            continue
        for fpath in subdir.glob("*.wiki"):
            entity = fpath.stem
            index[entity] = (ns, subdir.name, fpath)
    return index


def extract_existing_links(text):
    """提取文本中所有 [[...]] 链接，返回 (full_match, target, display, start, end) 列表"""
    pattern = re.compile(r'\[\[([^\]|]+)(?:\|([^\]]*))?\]\]')
    results = []
    for m in pattern.finditer(text):
        target = m.group(1).strip()
        display = m.group(2).strip() if m.group(2) else target
        results.append((m.group(0), target, display, m.start(), m.end()))
    return results


def find_protected_spans(text):
    """返回需要跳过的文本区间 (start, end, reason)"""
    spans = []

    # 1. 原文引用区 == 原文引用 == 到下一个 == 或文件尾
    for m in re.finditer(r'== 原文引用 ==', text):
        start = m.start()
        next_title = re.search(r'\n== ', text[start + len(m.group(0)):])
        if next_title:
            end = start + len(m.group(0)) + next_title.start()
        else:
            end = len(text)
        spans.append((start, end, "原文引用区"))

    # 2. info表 {| ... |}
    for m in re.finditer(r'\{\|', text):
        start = m.start()
        end_match = re.search(r'\|\}', text[start:])
        if end_match:
            end = start + end_match.end()
            spans.append((start, end, "info表"))

    # 3. Category 行
    for m in re.finditer(r'\[\[Category:[^\]]+\]\]', text):
        spans.append((m.start(), m.end(), "Category"))

    # 4. 章节标题 == 标题 ==
    for m in re.finditer(r'\n==+ [^=]+ ==+', text):
        spans.append((m.start(), m.end(), "章节标题"))

    # 5. 所属道统区
    for m in re.finditer(r'== 所属道统 ==', text):
        start = m.start()
        next_title = re.search(r'\n== ', text[start + len(m.group(0)):])
        if next_title:
            end = start + len(m.group(0)) + next_title.start()
        else:
            end = len(text)
        spans.append((start, end, "所属道统区"))

    return spans


def is_in_protected(pos, spans):
    for start, end, _ in spans:
        if start <= pos < end:
            return True
    return False


def is_inside_existing_link(pos, links):
    for _, _, _, start, end in links:
        if start <= pos < end:
            return True
    return False


def find_unlinked_mentions(text, entity, namespace, existing_links, protected_spans, self_entity):
    """
    在文本中查找某实体的未链接提及（First-Mention-Only）。
    返回 (start, end, matched_text, replacement) 或 None
    """
    if entity == self_entity:
        return None

    # 优先匹配带书名号【entity】，再匹配 [entity]，最后匹配裸entity
    # 安全策略：2字及以下实体名只允许带书名号匹配，避免子串误匹配（如"白飬金书"中的"金书"）
    patterns = [
        (re.compile(re.escape(f'【{entity}】')), f'【{entity}】', True),
        (re.compile(re.escape(f'[{entity}]')), f'[{entity}]', True),
    ]
    if len(entity) >= 3:
        patterns.append((re.compile(re.escape(entity)), entity, False))

    for pattern, matched_text, has_brackets in patterns:
        for m in pattern.finditer(text):
            start, end = m.start(), m.end()

            # 检查是否在保护区内
            if is_in_protected(start, protected_spans):
                continue

            # 检查是否在已有链接内部
            if is_inside_existing_link(start, existing_links):
                continue

            # 检查是否紧邻在已有链接的display部分（避免 [[A|Bentity]] 这种情况）
            # 这种情况通过 existing_links 检查应该已经覆盖了

            # 检查前面是否已有 [[ 但未闭合（即位于链接target或display内部）
            # 通过 existing_links 已经覆盖，但为了安全再检查一次
            for _, _, _, ls, le in existing_links:
                if ls <= start < le:
                    break
            else:
                # 不在任何已有链接内
                # 如果是 [entity] 单方括号，去掉括号显示
                if matched_text.startswith('[') and matched_text.endswith(']'):
                    display = entity
                else:
                    display = matched_text
                replacement = f'[[{namespace}-{entity}|{display}]]'
                return (start, end, matched_text, replacement)

    return None


def phase_a_fix_redlinks(text, fpath_str):
    """Phase A: 纠正命名空间错误的红链"""
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
            if pipe_pos != -1:
                display = full_old[pipe_pos + 1:-2]
            else:
                display = entity

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


def phase_b_creation_links(text, fpath, entity_index, self_entity, max_links=5):
    """Phase B: 添加造物互链"""
    changes = []
    new_text = text
    linked_in_page = set()

    # 按实体名长度降序排列，优先匹配长的（避免子串误匹配）
    creation_entities = [
        (entity, ns) for entity, (ns, _, _) in entity_index.items()
        if ns == "造物" and entity != self_entity
    ]
    creation_entities.sort(key=lambda x: len(x[0]), reverse=True)

    for entity, ns in creation_entities:
        if len(linked_in_page) >= max_links:
            break
        if entity in linked_in_page:
            continue

        existing_links = extract_existing_links(new_text)
        protected_spans = find_protected_spans(new_text)

        result = find_unlinked_mentions(new_text, entity, ns, existing_links, protected_spans, self_entity)
        if result:
            start, end, matched_text, replacement = result
            changes.append({
                'phase': 'B',
                'file': str(fpath),
                'old': matched_text,
                'new': replacement,
                'reason': f'造物互链: {entity}'
            })
            new_text = new_text[:start] + replacement + new_text[end:]
            linked_in_page.add(entity)

    return new_text, changes


def phase_c_character_links(text, fpath, character_index, self_entity, max_links=5):
    """Phase C: 添加人物链"""
    changes = []
    new_text = text
    linked_in_page = set()

    character_entities = [
        (entity, ns) for entity, (ns, _, _) in character_index.items()
        if ns == "人物" and entity != self_entity
    ]
    character_entities.sort(key=lambda x: len(x[0]), reverse=True)

    for entity, ns in character_entities:
        if len(linked_in_page) >= max_links:
            break
        if entity in linked_in_page:
            continue

        existing_links = extract_existing_links(new_text)
        protected_spans = find_protected_spans(new_text)

        result = find_unlinked_mentions(new_text, entity, ns, existing_links, protected_spans, self_entity)
        if result:
            start, end, matched_text, replacement = result
            changes.append({
                'phase': 'C',
                'file': str(fpath),
                'old': matched_text,
                'new': replacement,
                'reason': f'人物链: {entity}'
            })
            new_text = new_text[:start] + replacement + new_text[end:]
            linked_in_page.add(entity)

    return new_text, changes


def generate_diff(original, modified, filepath):
    """生成unified diff"""
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)
    if original_lines and not original_lines[-1].endswith('\n'):
        original_lines[-1] += '\n'
    if modified_lines and not modified_lines[-1].endswith('\n'):
        modified_lines[-1] += '\n'

    diff = list(difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=filepath,
        tofile=filepath,
        lineterm='\n'
    ))
    return ''.join(diff)


def main():
    parser = argparse.ArgumentParser(description='Wiki内链建设')
    parser.add_argument('--phase', choices=['A', 'B', 'C', 'all'], default='all',
                        help='执行哪个阶段')
    parser.add_argument('--dry-run', action='store_true',
                        help='只生成diff，不写入文件')
    parser.add_argument('--output', type=str, default='link_build_diff.txt',
                        help='diff输出文件路径')
    parser.add_argument('--max-per-page', type=int, default=5,
                        help='每页最大新增内链数')
    parser.add_argument('--apply', action='store_true',
                        help='确认后直接应用修改')
    args = parser.parse_args()

    print("=" * 60)
    print("玄鉴仙族 Wiki · 内链建设")
    print("=" * 60)

    print("\n[1/4] 构建实体索引...")
    entity_index = build_entity_index()
    creation_index = {k: v for k, v in entity_index.items() if v[0] == "造物"}
    character_index = {k: v for k, v in entity_index.items() if v[0] == "人物"}
    print(f"    造物实体: {len(creation_index)}")
    print(f"    人物实体: {len(character_index)}")
    print(f"    总计: {len(entity_index)}")

    print("\n[2/4] 扫描造物页面...")
    all_changes = []
    modified_files = {}

    for subdir in PAGES_DIR.iterdir():
        if not subdir.is_dir():
            continue
        ns = DIR_NS.get(subdir.name)
        if ns != "造物":
            continue

        for fpath in subdir.glob("*.wiki"):
            entity = fpath.stem
            original = fpath.read_text(encoding='utf-8')
            modified = original
            file_changes = []

            if args.phase in ('A', 'all'):
                modified, changes_a = phase_a_fix_redlinks(modified, str(fpath))
                file_changes.extend(changes_a)

            if args.phase in ('B', 'all'):
                modified, changes_b = phase_b_creation_links(modified, fpath, entity_index, entity, max_links=args.max_per_page)
                file_changes.extend(changes_b)

            if args.phase in ('C', 'all'):
                b_count = len([c for c in file_changes if c['phase'] == 'B'])
                remaining = max(0, args.max_per_page - b_count)
                modified, changes_c = phase_c_character_links(modified, fpath, character_index, entity, max_links=remaining)
                file_changes.extend(changes_c)

            if file_changes:
                all_changes.extend(file_changes)
                modified_files[str(fpath)] = (original, modified)

    print(f"    扫描完成，涉及 {len(modified_files)} 个文件")

    print(f"\n[3/4] 生成diff报告...")
    diff_parts = []
    summary = {'A': 0, 'B': 0, 'C': 0}

    for fpath, (orig, mod) in modified_files.items():
        diff = generate_diff(orig, mod, fpath)
        if diff:
            diff_parts.append(diff)
            diff_parts.append("\n")

    for ch in all_changes:
        summary[ch['phase']] = summary.get(ch['phase'], 0) + 1

    diff_text = ''.join(diff_parts)
    output_path = Path(args.output)
    output_path.write_text(diff_text, encoding='utf-8')

    print(f"    diff已保存至: {output_path}")
    print(f"    Phase A (红链纠正): {summary.get('A', 0)} 处")
    print(f"    Phase B (造物互链): {summary.get('B', 0)} 处")
    print(f"    Phase C (人物链): {summary.get('C', 0)} 处")

    json_path = output_path.with_suffix('.json')
    json_path.write_text(json.dumps(all_changes, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"    变更清单: {json_path}")

    if args.apply:
        print(f"\n[4/4] 应用修改...")
        for fpath, (orig, mod) in modified_files.items():
            Path(fpath).write_text(mod, encoding='utf-8')
        print(f"    已修改 {len(modified_files)} 个文件")
    else:
        print(f"\n[4/4] 审阅模式 — 未应用修改")
        print(f"    请审阅 {output_path}，确认后加 --apply 执行")

    print("\n" + "=" * 60)


if __name__ == '__main__':
    main()
