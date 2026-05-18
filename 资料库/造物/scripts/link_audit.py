#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
玄鉴仙族 Wiki · 链接审计与修复
================================

合并自三个旧脚本：

* ``scan_red_links.py``      → 子命令 ``scan``：扫描红链
* ``generate_fix_diff.py``   → 子命令 ``diff``：A1+A2 修复 diff（审阅模式）
* ``apply_a1_fix.py``        → 子命令 ``apply``：A1 人物前缀直接修复

用法
----

::

    # 扫描红链，输出报告
    python3 link_audit.py scan

    # 生成 A1+A2 修复 diff（审阅模式）
    python3 link_audit.py diff

    # 应用 A1 人物前缀修复（直接写入）
    python3 link_audit.py apply --confirm

路径策略：基于 ``_paths.py``，零硬编码。
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import (  # noqa: E402
    PAGES_DIR,
    PEOPLE_DIR,
    WORKBUDDY_DIR,
    DIR_NS,
)

# ============================================================
# 常量
# ============================================================

LINK_PAT = re.compile(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]')
ALL_LINKS_PAT = re.compile(r'\[\[(.*?)\]\]')

# 命名空间前缀（识别非红链所需）
KNOWN_NS = ('造物', '人物', '道统', '势力', '神通', '事件', '地点',
            'Category', 'File', 'Image', 'Template')

# 品阶/类型标签词（误链，应改为纯文本）
RANK_TAGS = {
    '灵物', '灵宝', '灵器', '灵资', '材料',
    '筑基法器', '紫府灵资', '筑基法剑', '紫府灵物',
    '紫府灵丹', '极品灵气', '待分类', '紫府灵器',
    '筑基灵物', '符箓', '丹药', '法器', '凡器', '灵气',
    '古灵器/灵宝', '道胎法旨',
}


def load_people() -> set[str]:
    """从主仓 ``pages/人物与势力/`` 收集所有人物名。"""
    if not PEOPLE_DIR.is_dir():
        return set()
    return {p.stem for p in PEOPLE_DIR.glob("*.wiki")}


# ============================================================
# 通用：本地页面收集（线上标题格式）
# ============================================================

def collect_local_pages() -> set[str]:
    """收集造物子项目中所有本地 .wiki 页面对应的线上标题。

    ``00-体系/X.wiki`` → ``X``
    ``其它子目录/X.wiki`` → 根据 ``DIR_NS`` 配置加前缀（当前均为无前缀）
    """
    pages: set[str] = set()
    for wiki_file in PAGES_DIR.rglob("*.wiki"):
        rel = wiki_file.relative_to(PAGES_DIR)
        parts = rel.parts
        if len(parts) < 2:
            continue
        dir_name = parts[0]
        ns = DIR_NS.get(dir_name)
        if ns is None:
            continue
        # 文件名做品阶前缀剥离（L1- / L2- 等）
        stem = re.sub(r'^L\d+-', '', wiki_file.stem)
        title = f"{ns}-{stem}" if ns else stem
        pages.add(title)
    # 加入主仓维度
    for p in load_people():
        pages.add(f"人物-{p}")
        pages.add(p)  # 人物本名也算
    return pages


# ============================================================
# 子命令：scan ==================================================

def cmd_scan(args: argparse.Namespace) -> int:
    """扫描红链。"""
    local_pages = collect_local_pages()
    print(f"本地页面总数（含人物）: {len(local_pages)}")

    red_links: dict[str, list[tuple[str, int]]] = defaultdict(list)
    all_counter: Counter = Counter()

    for wiki_file in sorted(PAGES_DIR.rglob("*.wiki")):
        rel = wiki_file.relative_to(PAGES_DIR)
        try:
            lines = wiki_file.read_text(encoding='utf-8').splitlines()
        except Exception as e:
            print(f"读取失败: {rel}: {e}")
            continue
        for line_no, line in enumerate(lines, 1):
            for m in ALL_LINKS_PAT.finditer(line):
                target = m.group(1).split('|')[0].strip()
                if not target:
                    continue
                if target.startswith(('Category:', 'File:', 'Image:', 'Template:',
                                       'http://', 'https://')):
                    continue
                all_counter[target] += 1
                if target not in local_pages:
                    red_links[target].append((str(rel), line_no))

    print(f"\n总链接数:     {sum(all_counter.values())}")
    print(f"唯一链接目标: {len(all_counter)}")
    print(f"红链目标数:   {len(red_links)}")
    print(f"红链总出现:   {sum(len(v) for v in red_links.values())}")

    sorted_red = sorted(red_links.items(), key=lambda x: len(x[1]), reverse=True)

    # 命名空间分布
    ns_counter: Counter = Counter()
    for target, refs in sorted_red:
        ns = target.split('-', 1)[0] if '-' in target else "(无命名空间)"
        ns_counter[ns] += len(refs)

    print("\n=== 按命名空间分布 ===")
    for ns, count in ns_counter.most_common():
        print(f"  {ns}: {count}")

    print("\n=== TOP 30 红链 ===")
    for target, refs in sorted_red[:30]:
        files = {f for f, _ in refs}
        print(f"  {target}: {len(refs)} 次 / {len(files)} 文件")

    # 输出报告
    report_path = Path(args.output) if args.output \
        else WORKBUDDY_DIR / "red_links_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open('w', encoding='utf-8') as f:
        f.write("# 红链扫描报告\n\n")
        f.write(f"- 本地页面总数: {len(local_pages)}\n")
        f.write(f"- 总链接数: {sum(all_counter.values())}\n")
        f.write(f"- 唯一链接目标数: {len(all_counter)}\n")
        f.write(f"- 红链目标数: {len(red_links)}\n")
        f.write(f"- 红链出现次数: {sum(len(v) for v in red_links.values())}\n\n")
        f.write("## 按命名空间分布\n\n")
        f.write("| 命名空间 | 出现次数 |\n|---------|---------|\n")
        for ns, count in ns_counter.most_common():
            f.write(f"| {ns} | {count} |\n")
        f.write("\n## 全部红链（按频次降序）\n\n")
        f.write("| 排名 | 链接目标 | 出现次数 | 涉及文件数 | 样例来源 |\n")
        f.write("|-----|---------|---------|----------|---------|\n")
        for rank, (target, refs) in enumerate(sorted_red, 1):
            files = sorted({f for f, _ in refs})
            sample = files[0] if files else ""
            f.write(f"| {rank} | {target} | {len(refs)} | {len(files)} | {sample} |\n")
    print(f"\n详细报告: {report_path}")
    return 0


# ============================================================
# 子命令：diff（A1 + A2 修复审阅） ===================================

def _analyze_file_for_fix(wiki_file: Path, people: set[str]) -> list[dict]:
    """分析单个文件，返回 A1/A2 修复建议。"""
    try:
        text = wiki_file.read_text(encoding='utf-8')
    except Exception:
        return []
    fixes = []
    for line_no, line in enumerate(text.split('\n'), 1):
        for m in LINK_PAT.finditer(line):
            target = m.group(1).strip()
            display = m.group(2)
            original = m.group(0)
            if not target:
                continue
            # 跳过已有命名空间的
            if '-' in target and target.split('-', 1)[0] in KNOWN_NS:
                continue
            # A1: 人物裸链接
            if target in people:
                replacement = f'[[人物-{target}|{display or target}]]'
                fixes.append({
                    'line_no': line_no, 'line': line, 'original': original,
                    'replacement': replacement, 'type': 'A1',
                    'reason': f'A1-人物裸链接: [[{target}]] → [[人物-{target}]]',
                })
            # A2: 品阶标签误链
            elif target in RANK_TAGS:
                replacement = display or target
                fixes.append({
                    'line_no': line_no, 'line': line, 'original': original,
                    'replacement': replacement, 'type': 'A2',
                    'reason': f'A2-品阶误链: [[{target}]] → 纯文本「{replacement}」',
                })
    return fixes


def cmd_diff(args: argparse.Namespace) -> int:
    """生成 A1+A2 修复 diff（审阅模式）。"""
    people = load_people()
    if not people:
        print(f"⚠️  未在 {PEOPLE_DIR} 找到人物条目，A1 修复将为空。")
    print(f"人物名单数量: {len(people)}")

    all_fixes: list[dict] = []
    file_fixes: dict[str, list[dict]] = defaultdict(list)
    type_counter: Counter = Counter()

    wiki_files = list(PAGES_DIR.rglob("*.wiki"))
    for wf in sorted(wiki_files):
        rel = str(wf.relative_to(PAGES_DIR))
        for f in _analyze_file_for_fix(wf, people):
            f['file'] = rel
            file_fixes[rel].append(f)
            all_fixes.append(f)
            type_counter[f['type']] += 1

    report_path = Path(args.output) if args.output \
        else WORKBUDDY_DIR / "red_links_fix_diff.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with report_path.open('w', encoding='utf-8') as out:
        out.write("# A1+A2 红链修复 Diff 报告（审阅模式）\n\n")
        out.write(f"**扫描范围**: {len(wiki_files)} 个 .wiki 文件\n")
        out.write(f"**建议修改总数**: {len(all_fixes)} 处\n")
        out.write(f"**涉及文件数**: {len(file_fixes)} 个\n")
        out.write(f"- A1 人物裸链接: {type_counter['A1']} 处\n")
        out.write(f"- A2 品阶误链:   {type_counter['A2']} 处\n\n")
        out.write("---\n\n## 修复规则说明\n\n")
        out.write("### A1: 人物裸链接（加 `人物-` 前缀）\n")
        out.write("以下人物名在主仓 `pages/人物与势力/` 中存在，"
                  "裸链接 `[[人物名]]` 统一改为 `[[人物-人物名|人物名]]`：\n\n")
        out.write(", ".join(sorted(people)[:80]))
        if len(people) > 80:
            out.write(f"，…（共 {len(people)} 人，仅展示前 80）")
        out.write("\n\n### A2: 品阶标签误链（改为纯文本）\n")
        out.write("以下品阶/类型词作为内链指向不存在的页面，改为纯文本：\n\n")
        out.write(", ".join(sorted(RANK_TAGS)))
        out.write("\n\n**保留书名号规则**: 如《[[灵物]]》→《灵物》，书名号保留。\n\n")

        sorted_files = sorted(file_fixes.items(), key=lambda x: len(x[1]), reverse=True)
        out.write("---\n\n## 按文件列出修改（TOP 50）\n\n")
        for rank, (rel, fixes) in enumerate(sorted_files[:50], 1):
            out.write(f"### {rank}. {rel}（{len(fixes)} 处）\n\n")
            for f in fixes:
                out.write(f"**行 {f['line_no']}** — {f['reason']}\n")
                out.write("```diff\n")
                out.write(f"- {f['line'].rstrip()}\n")
                new_line = f['line'].replace(f['original'], f['replacement'], 1)
                out.write(f"+ {new_line.rstrip()}\n")
                out.write("```\n\n")

        out.write("---\n\n## 全部文件统计\n\n")
        out.write("| 排名 | 文件 | A1 | A2 | 总计 |\n")
        out.write("|-----|------|----|----|-----|\n")
        for rank, (rel, fixes) in enumerate(sorted_files, 1):
            a1 = sum(1 for f in fixes if f['type'] == 'A1')
            a2 = sum(1 for f in fixes if f['type'] == 'A2')
            out.write(f"| {rank} | {rel} | {a1} | {a2} | {len(fixes)} |\n")

    print(f"Diff 报告: {report_path}")
    print(f"建议修改: {len(all_fixes)} 处 (A1={type_counter['A1']}, A2={type_counter['A2']})")
    print(f"涉及文件: {len(file_fixes)} 个")
    return 0


# ============================================================
# 子命令：apply（A1 直接写入） ====================================

def _fix_a1_line(line: str, people: set[str]) -> str:
    def repl(m: re.Match) -> str:
        target = m.group(1).strip()
        display = m.group(2)
        if target in people:
            return f'[[人物-{target}|{display or target}]]'
        return m.group(0)
    return LINK_PAT.sub(repl, line)


def cmd_apply(args: argparse.Namespace) -> int:
    """A1 人物前缀修复，直接写入文件。"""
    if not args.confirm:
        print("⚠️  apply 会直接修改 .wiki 文件。请加 --confirm 确认执行。")
        print(f"   建议先跑 ``python3 {Path(__file__).name} diff`` 审阅。")
        return 2

    people = load_people()
    print(f"人物名单数量: {len(people)}")
    if not people:
        print("⚠️  未找到人物条目，跳过。")
        return 0

    total_files = 0
    total_fixes = 0
    fixed_files: list[str] = []

    for wf in sorted(PAGES_DIR.rglob("*.wiki")):
        rel = str(wf.relative_to(PAGES_DIR))
        try:
            text = wf.read_text(encoding='utf-8')
        except Exception:
            continue
        new_lines = []
        file_fixes = 0
        for line in text.split('\n'):
            new_line = _fix_a1_line(line, people)
            if new_line != line:
                file_fixes += 1
            new_lines.append(new_line)
        if file_fixes:
            wf.write_text('\n'.join(new_lines), encoding='utf-8')
            total_files += 1
            total_fixes += file_fixes
            fixed_files.append(f"{rel} ({file_fixes}处)")

    log_path = WORKBUDDY_DIR / "a1_fix_log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open('w', encoding='utf-8') as f:
        f.write("# A1 修复日志\n\n")
        f.write(f"修复文件数: {total_files}\n修复链接数: {total_fixes}\n\n")
        f.write("## 修改文件清单\n\n")
        for item in fixed_files:
            f.write(f"- {item}\n")

    print(f"A1 修复完成: {total_files} 个文件 / {total_fixes} 处链接")
    print(f"日志: {log_path}")
    return 0


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description='玄鉴仙族 Wiki · 链接审计与修复',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest='cmd', required=True)

    p_scan = sub.add_parser('scan', help='扫描红链并生成报告')
    p_scan.add_argument('--output', help='报告输出路径（默认: .workbuddy/red_links_report.md）')
    p_scan.set_defaults(func=cmd_scan)

    p_diff = sub.add_parser('diff', help='生成 A1+A2 修复 diff（审阅模式）')
    p_diff.add_argument('--output', help='diff 输出路径（默认: .workbuddy/red_links_fix_diff.md）')
    p_diff.set_defaults(func=cmd_diff)

    p_apply = sub.add_parser('apply', help='应用 A1 人物前缀修复（直接写入）')
    p_apply.add_argument('--confirm', action='store_true', help='确认执行写入')
    p_apply.set_defaults(func=cmd_apply)

    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main() or 0)
