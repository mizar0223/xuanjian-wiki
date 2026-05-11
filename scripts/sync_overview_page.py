#!/usr/bin/env python3
"""同步总览页 `道统丨神通丨仙基.wiki` 中各道统区段的神通表。

原理：
  对总览页中每个 "主页面：[[道统-XXX|...]]" 区段，从对应的单独道统页面
  `pages/仙基道统/道统/道统-XXX.wiki` 中读取「神通列表」表格，并将其
  替换到总览页的对应位置。其他段落（位业详情、统计总览等）不动。

约束：
  - 单独道统页是脚本 `sync_daotong_tables.py` 维护的权威表，已与
    《玄鉴仙族·神通仙基汇总》对齐（含已收录/补充/汇总未列等校验态）。
  - 总览页区段中无表格的（如 `保木` 之前的 "暂无已知神通条目"），若
    单独页面有了表格也会被自动改写为表格。
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES_DIR = ROOT / 'pages'
OVERVIEW_FILE = PAGES_DIR / '仙基道统' / '道统丨神通丨仙基.wiki'
DAOTONG_DIR = PAGES_DIR / '仙基道统' / '道统'

# 总览页中区段头格式：主页面：[[道统-名称|显示名]] 或 [[道统-名称]]
SECTION_HEADER_RE = re.compile(r'主页面：\[\[(道统-[^\|\]]+)(?:\|[^\]]+)?\]\]')

# 表格匹配：从 `{| class="wikitable sortable"` 到下一个 `|}`
TABLE_RE = re.compile(r'\{\|\s*class="wikitable sortable".*?\n\|\}', re.DOTALL)

# 也要匹配 "暂无已知神通条目" 占位
PLACEHOLDER_RE = re.compile(r'暂无已知神通条目。?')


def extract_shentong_table(daotong_file: Path) -> str | None:
    """从单独道统页读取神通列表表格的完整 wiki 文本。

    单独道统页里基本信息表为 `class="wikitable"`，神通表为
    `class="wikitable sortable"`，因此后者具有唯一性，无需依赖
    "=== 神通列表 ===" 标题来定位（部分页面无此标题）。
    """
    text = daotong_file.read_text(encoding='utf-8')
    tm = TABLE_RE.search(text)
    if tm:
        return tm.group(0)
    # 没表格——判断是否为占位
    if '暂无已知神通条目' in text:
        return '暂无已知神通条目。'
    return None


def find_daotong_page(page_name: str) -> Path | None:
    """根据 "道统-XXX" 找到 pages/仙基道统/道统/ 下的对应文件 (兼容带括号别称)."""
    # 直接拼
    p = DAOTONG_DIR / f'{page_name}.wiki'
    if p.exists():
        return p
    # 带括号别称（如 "道统-并鸺（鸺葵）"）
    short = page_name
    for f in DAOTONG_DIR.glob(f'{page_name}*.wiki'):
        return f
    # 反向：总览页可能写的是带括号的名字，单独页面也带括号
    return None


def split_overview_into_sections(text: str) -> list[tuple[str, str]]:
    """切分总览页为 [(prefix_or_section_name, body)...].

    第一个元素是前置部分(prefix)；之后每三条为 (page_name, display_name, body)。
    """
    # 用包含 "显示名" 捕获的正则切分
    pattern = re.compile(r'主页面：\[\[(道统-[^\|\]]+)(?:\|([^\]]+))?\]\]')
    return pattern.split(text)


def replace_table_in_body(body: str, new_table: str) -> tuple[str, bool]:
    """在区段 body 中，替换首个 wikitable 表格 (或占位) 为 new_table。"""
    # 计算需要替换的范围：从区段头到第一个 "----" 或 "'''位业详情'''" 之间
    # 我们只在该范围内做替换，避免把后面的别的表格替换掉。
    # 区段结束标志：'----' 或 "== " 标题
    # 但 TABLE_RE 本身限定就是首个 wikitable sortable 表格，已足够安全。
    m = TABLE_RE.search(body)
    if m:
        if m.group(0) == new_table:
            return body, False
        return body[:m.start()] + new_table + body[m.end():], True
    # 没找到表格：尝试替换占位
    pm = PLACEHOLDER_RE.search(body)
    if pm:
        if new_table == '暂无已知神通条目。':
            return body, False
        return body[:pm.start()] + new_table + body[pm.end():], True
    # 都没有：插入到区段开始的空行后
    if new_table == '暂无已知神通条目。':
        return body, False
    # body 形如 "\n\n{| ...\n|}\n\n----\n..."；这里区段头紧跟换行，第一段内容
    # 可能就在 body 开头。我们在第一个空行处插入。
    insert_at = 0
    # 跳过开头的空白行
    nl = re.match(r'\s*\n', body)
    if nl:
        insert_at = nl.end()
    return body[:insert_at] + new_table + '\n\n' + body[insert_at:], True


def main():
    text = OVERVIEW_FILE.read_text(encoding='utf-8')
    parts = split_overview_into_sections(text)
    # parts[0] 为前置；之后每两个为 (page_name, body)
    if len(parts) < 3:
        print('未找到任何道统区段；请检查总览页结构')
        return

    out = [parts[0]]
    n_sections = 0
    n_changed = 0
    missing_pages = []

    # split 现在每三个为一组：(page_name, display_name_or_None, body)
    for i in range(1, len(parts), 3):
        page_name = parts[i]
        display = parts[i + 1] if (i + 1) < len(parts) else None
        body = parts[i + 2] if (i + 2) < len(parts) else ''
        n_sections += 1

        daotong_file = find_daotong_page(page_name)
        if daotong_file is None:
            missing_pages.append(page_name)
            link = f'[[{page_name}|{display}]]' if display else f'[[{page_name}]]'
            out.append(f'主页面：{link}')
            out.append(body)
            continue

        new_table = extract_shentong_table(daotong_file)
        if new_table is None:
            link = f'[[{page_name}|{display}]]' if display else f'[[{page_name}]]'
            out.append(f'主页面：{link}')
            out.append(body)
            continue

        new_body, changed = replace_table_in_body(body, new_table)
        if changed:
            n_changed += 1
            print(f'  ✓ 更新 {page_name}')
        # 保留原显示名（含 "执宰" 等与 page_name 不同的标签）
        link = f'[[{page_name}|{display}]]' if display else f'[[{page_name}]]'
        out.append(f'主页面：{link}')
        out.append(new_body)

    new_text = ''.join(out)

    if missing_pages:
        print('\n以下道统在 道统/ 目录下未找到对应单独页面，未做替换：')
        for p in missing_pages:
            print(f'  - {p}')

    if new_text != text:
        OVERVIEW_FILE.write_text(new_text, encoding='utf-8')
        print(f'\n已写回 {OVERVIEW_FILE.relative_to(ROOT)} —— 共 {n_changed}/{n_sections} 个区段被更新')
    else:
        print(f'\n无变化（共扫描 {n_sections} 个区段）')


if __name__ == '__main__':
    main()