#!/usr/bin/env python3
"""根据权威资料《玄鉴仙族·神通仙基汇总》(2026-05-04 校对至第1456章) 同步页面命名修正。

权威资料修正记录:
    阙阴→厥阴、修越→执孛、丑葵藏→丑癸藏、九重欆→九重擭、㡔梁银→帑梁银、
    罗刹海→罗剎海、侯神殊→候神殊、制養宜→制飬宜、赤断簇→赤断镞、
    天金胄→天金冑、形度阡→形渡阡、不二與→不二舆、掩蔽服→掩弊服、律演危→律演威

本脚本仅修正现存于 pages/ 目录下、与权威汇总不一致的字形差异，
即:
    九重镬 → 九重擭
    天金胄 → 天金冑
    罗刹海 → 罗剎海

执行内容:
    1. 重命名神通页面文件 (神通-旧名.wiki → 神通-新名.wiki)
    2. 替换所有页面文件中对旧名的引用
    3. 同时更新 wikilink 中的展示文字
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES_DIR = ROOT / 'pages'

# 字形修正映射: 旧名 -> 新名
NAME_CORRECTIONS = {
    '九重镬': '九重擭',
    '天金胄': '天金冑',
    '罗刹海': '罗剎海',
    '制餋宣': '制飬宜',
    '参玄臓': '参玄臟',
    '受灯龠': '受灴龠',
    '满垠煌': '满垠㷐',
    '秉灯夏': '秉灴夏',
}

# 道统名修正映射: 旧名 -> 新名 (需要重命名 道统-旧名*.wiki 文件并修正所有引用)
DAOTONG_CORRECTIONS = {
    '执宰': '执孛',
}


def rename_page_files() -> list[tuple[Path, Path]]:
    """根据修正映射重命名神通页面文件"""
    renamed = []
    for old, new in NAME_CORRECTIONS.items():
        old_file = PAGES_DIR / '仙基道统' / '神通' / f'神通-{old}.wiki'
        new_file = PAGES_DIR / '仙基道统' / '神通' / f'神通-{new}.wiki'
        if old_file.exists() and not new_file.exists():
            old_file.rename(new_file)
            renamed.append((old_file, new_file))
            print(f'  ✓ 重命名: 神通-{old}.wiki → 神通-{new}.wiki')
        elif new_file.exists():
            print(f'  · 已存在: 神通-{new}.wiki, 跳过')
        else:
            print(f'  ! 不存在: 神通-{old}.wiki')

    # 道统页面重命名 (支持模糊匹配 "道统-旧名*.wiki")
    daotong_dir = PAGES_DIR / '仙基道统' / '道统'
    for old, new in DAOTONG_CORRECTIONS.items():
        for old_file in list(daotong_dir.glob(f'道统-{old}*.wiki')):
            stem = old_file.stem  # 如 道统-执宰（修越）
            new_stem = stem.replace(old, new, 1)
            new_file = old_file.parent / f'{new_stem}.wiki'
            if new_file.exists():
                print(f'  · 已存在: {new_file.name}, 跳过')
                continue
            old_file.rename(new_file)
            renamed.append((old_file, new_file))
            print(f'  ✓ 重命名: {old_file.name} → {new_file.name}')
    return renamed


def replace_in_text(text: str) -> tuple[str, int]:
    """对单个文件内容做替换, 注意只替换神通名 (不替换原文引用中的字符)
    替换以下模式:
        - 神通-旧名 → 神通-新名 (页面链接)
        - |旧名]] → |新名]] (link 显示文字)
        - 表格中独立单元格的 旧名
    """
    new_text = text
    total = 0
    for old, new in NAME_CORRECTIONS.items():
        # 1) 替换 wikilink 中的 神通-旧 (页面链接)
        pattern1 = re.compile(rf'(\[\[神通-){re.escape(old)}(\||\]\])')
        new_text, n1 = pattern1.subn(rf'\g<1>{new}\g<2>', new_text)

        # 2) 替换 wikilink 链接 [[神通-新|旧]] 中的展示部分:
        pattern2 = re.compile(rf'(\[\[神通-{re.escape(new)}\|){re.escape(old)}(\]\])')
        new_text, n2 = pattern2.subn(rf'\g<1>{new}\g<2>', new_text)

        # 3) 替换页面正文中独立出现的旧名
        # 顶部标题: '''旧名'''
        pattern3 = re.compile(rf"'''({re.escape(old)})'''")
        new_text, n3 = pattern3.subn(f"'''{new}'''", new_text)

        total += n1 + n2 + n3

    # 道统名修正
    for old, new in DAOTONG_CORRECTIONS.items():
        # 1) 替换 [[道统-旧 → [[道统-新
        pattern1 = re.compile(rf'(\[\[道统-){re.escape(old)}')
        new_text, n1 = pattern1.subn(rf'\g<1>{new}', new_text)
        # 2) 替换 |旧名]] 或 |旧名（...）]] 中的展示文字
        pattern2 = re.compile(rf'(\|){re.escape(old)}(?=[）)\]])')
        new_text, n2 = pattern2.subn(rf'\g<1>{new}', new_text)
        # 3) 替换正文中 '''旧名''' 顶部标题
        pattern3 = re.compile(rf"'''({re.escape(old)})")
        new_text, n3 = pattern3.subn(f"'''{new}", new_text)
        # 4) 替换"道统 || 旧名" 等 wiki 表格内容
        pattern4 = re.compile(rf'(\|\s*道统\s*\|\|\s*){re.escape(old)}')
        new_text, n4 = pattern4.subn(rf'\g<1>{new}', new_text)
        # 5) 替换正文/位业详情中作为独立词出现的"旧名"(如 "克制执宰", "与执宰冲突", "对应下仪；克制执宰")
        # 注意保留作品原文 (在 <small>...</small> 中) 不变,这里采用按行检查
        lines = new_text.split('\n')
        n5 = 0
        for idx, line in enumerate(lines):
            stripped = line.strip()
            # 跳过原文摘录行 (含 <small>)
            if '<small>' in line or '</small>' in line:
                continue
            # 跳过表格的链接显示文字行 (已由 pattern2 处理)
            if old in line:
                # 替换所有出现 (该独立字"执宰"出现在权柄特征/道统关系/位业详情中, 不会与其他字组合)
                new_line = line.replace(old, new)
                if new_line != line:
                    n5 += new_line.count(new) - line.count(new)
                    lines[idx] = new_line
        new_text = '\n'.join(lines)
        # 6) 替换 ===  执宰（...） === 等等小节标题
        # 由于上面pattern2和step5可能漏掉位于章节标题里的, 已经被step5覆盖
        total += n1 + n2 + n3 + n4 + n5
    return new_text, total


def update_all_pages() -> int:
    """遍历所有 wiki 页面, 应用替换"""
    total_changes = 0
    for path in PAGES_DIR.rglob('*.wiki'):
        text = path.read_text(encoding='utf-8')
        new_text, count = replace_in_text(text)
        if count and new_text != text:
            path.write_text(new_text, encoding='utf-8')
            total_changes += count
            print(f'  ✓ {path.relative_to(ROOT)}: {count} 处替换')
    return total_changes


def update_categories_in_renamed(renamed: list[tuple[Path, Path]]) -> None:
    """更新已重命名的页面文件内的标题和正文,使其与新文件名一致"""
    for _, new_file in renamed:
        text = new_file.read_text(encoding='utf-8')
        new_text, _ = replace_in_text(text)
        if new_text != text:
            new_file.write_text(new_text, encoding='utf-8')
            print(f'  ✓ 内部修订: {new_file.name}')


def main() -> int:
    if not PAGES_DIR.exists():
        print(f'错误: 找不到 {PAGES_DIR}', file=sys.stderr)
        return 1

    print('== 阶段 1: 重命名页面文件 ==')
    renamed = rename_page_files()

    print('\n== 阶段 2: 修订重命名文件的内部内容 ==')
    update_categories_in_renamed(renamed)

    print('\n== 阶段 3: 同步所有页面中对旧名的引用 ==')
    total = update_all_pages()
    print(f'\n本次共修订 {total} 处引用, 重命名 {len(renamed)} 个页面文件。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())