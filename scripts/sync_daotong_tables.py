#!/usr/bin/env python3
"""根据《玄鉴仙族·神通仙基汇总》(2026-05-04) 同步道统页面中的神通表。

权威源: 资料库/神通/04_参考权威/01_神通仙基_外部来源与展示/玄鉴仙族_神通仙基汇总.md

本脚本不会重写整张页面，只会:
    1. 解析汇总Markdown，得到每个道统的权威神通行 (神通名 / 下位/替参 / 神通类别)
    2. 读取每个道统页面，定位 "神通" wikitable, 用权威数据重建表内容
       - 校验列保留为 "已收录" (该列由权威表存在性反推)
    3. 不影响其他段落 (位业详情、原文/文化考据等)
    4. 同步道统映射变化时也补建缺失的神通独立页面
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
PAGES_DIR = ROOT / 'pages'
AUTH_MD = ROOT / '资料库' / '神通' / '04_参考权威' / '01_神通仙基_外部来源与展示' / '玄鉴仙族_神通仙基汇总.md'

# 道统名 → 现有页面文件名 (因为部分道统页面名带括号注释，例如 道统-玄雷（神雷）)
DAOTONG_PAGE_OVERRIDE = {
    '玄雷': '道统-玄雷（神雷）',
    '霄雷': '道统-霄雷（祥雷）',
    '元雷': '道统-元雷（旸雷）',
    '兑金': '道统-兑金（庚金）',  # 待确认
    '宣土': '道统-宣土（社土）',
    '归土': '道统-归土（稷土）',
    '戊土': '道统-戊土（戍土）',
    '邃炁': '道统-邃炁（玄炁）',
    '紫炁': '道统-紫炁',
    '执孛': '道统-执孛（修越）',
    '长庚': '道统-长庚（剑道）',
    '全丹': '道统-全丹（元胎）',
    '清炁': '道统-清炁',
    '太阴': '道统-太阴',
    '少阴': '道统-少阴',
    '厥阴': '道统-厥阴',
    '太阳': '道统-太阳',
    '少阳': '道统-少阳',
    '明阳': '道统-明阳',
}


def parse_authority_md() -> dict[str, list[dict]]:
    """解析汇总Markdown, 返回 {道统名: [{name, alias, kind}]}"""
    text = AUTH_MD.read_text(encoding='utf-8')
    result: dict[str, list[dict]] = {}

    # 切分章节: ### 道统名
    sections = re.split(r'^###\s+(.+?)\s*$', text, flags=re.M)
    # sections = [前置, daotong1, body1, daotong2, body2, ...]
    for i in range(1, len(sections), 2):
        head = sections[i].strip()
        body = sections[i + 1]
        # 在 body 中遇到下一个 '## ' 二级标题或 '---' 分隔符就截断
        body = re.split(r'^(?:##\s|---\s*$)', body, maxsplit=1, flags=re.M)[0]
        # 去除括号注释,例如 "执孛（修越）" -> "执孛"
        daotong = re.split(r'[（(]', head, 1)[0].strip()
        # 跳过统计章节
        if daotong in {'统计总览'}:
            continue
        rows = []
        # 匹配表格内容行 ( | a | b | c | d | )
        for line in body.splitlines():
            line = line.strip()
            if not line.startswith('|') or '---' in line:
                continue
            cells = [c.strip() for c in line.strip('|').split('|')]
            if len(cells) < 3:
                continue
            # 跳过表头行
            if cells[0] in {'神通', '体系'}:
                continue
            name = cells[0]
            # 去除括号后缀,如 "不穷锋(任意替)" -> 主名 "不穷锋"
            base_name = re.split(r'[（(]', name, 1)[0].strip()
            if not base_name or base_name in {'—', '-'}:
                continue
            alias_raw = cells[1]
            alias = re.sub(r'^→\s*', '', alias_raw).strip()
            if alias in {'—', '-', ''}:
                alias = ''
            kind = cells[2] if len(cells) > 2 else ''
            if kind in {'—', '-', ''}:
                kind = ''
            # 名称扩展信息保留(如 "(任意替)")
            extra = name[len(base_name):].strip(' （()')
            rows.append({
                'name': base_name,
                'name_raw': name,
                'alias': alias,
                'kind': kind,
                'extra': extra,
            })
        if rows:
            result[daotong] = rows
    return result


def daotong_page_path(daotong: str) -> Path | None:
    """根据道统名定位页面文件"""
    candidates = [
        DAOTONG_PAGE_OVERRIDE.get(daotong, f'道统-{daotong}'),
        f'道统-{daotong}',
    ]
    daotong_dir = PAGES_DIR / '仙基道统' / '道统'
    for cand in candidates:
        path = daotong_dir / f'{cand}.wiki'
        if path.exists():
            return path
    # 模糊查找: 文件名以 "道统-{daotong}" 开头
    for path in daotong_dir.glob(f'道统-{daotong}*.wiki'):
        return path
    return None


def cell(value: str) -> str:
    return value if value else '—'


def build_shentong_table(rows: list[dict]) -> str:
    """构建神通表的 wiki 文本"""
    lines = ['{| class="wikitable sortable"', '|-', '! 神通 !! 类别 !! 下位／古称／别称／替参 !! 校验']
    for row in rows:
        name = row['name']
        kind = cell(row['kind'])
        alias = cell(row['alias'])
        # 显示用名称: 若有 extra 则显示 "name(extra)"
        display = f"{name}({row['extra']})" if row['extra'] else name
        link = f"[[神通-{name}|{display}]]" if row['extra'] else f"[[神通-{name}|{name}]]"
        lines.append('|-')
        lines.append(f'| {link} || {kind} || {alias} || 已收录')
    lines.append('|}')
    return '\n'.join(lines)


def update_daotong_page(path: Path, rows: list[dict]) -> bool:
    """替换道统页面中的神通表"""
    text = path.read_text(encoding='utf-8')
    # 找到神通表: 第一个 {| class="wikitable sortable" 紧随 ! 神通(名称)? !! ... 的表
    pattern = re.compile(
        r'(\{\|\s*class="wikitable sortable"\s*\n\|-\s*\n!\s*神通(?:名称)?\s*!!.*?\n\|\})',
        re.S,
    )
    new_table = build_shentong_table(rows)
    new_text, n = pattern.subn(new_table, text, count=1)
    if n == 0:
        return False
    if new_text != text:
        path.write_text(new_text, encoding='utf-8')
        return True
    return False


def ensure_shentong_page(daotong: str, row: dict) -> bool:
    """如果神通页面不存在,创建一个最简框架"""
    name = row['name']
    path = PAGES_DIR / '仙基道统' / '神通' / f'神通-{name}.wiki'
    if path.exists():
        return False
    # 构建最简模板
    text = f"""{{{{导航栏}}}}

'''{name}'''是《玄鉴仙族》中的神通条目。

== 基本信息 ==

{{| class="wikitable sortable"
|-
! 所属体系 !! 所属道统 !! 位置类型 !! 类别 !! 下位／古称／别称／替参
|-
| — || [[道统-{daotong}|{daotong}]] || — || {row['kind'] or '—'} || {row['alias'] or '—'}
|}}

== 所属道统摘要 ==

=== {daotong} ===

* 道统页面：[[道统-{daotong}|{daotong}]]

== 原文考据 ==

''待考据''

== 文化考据 ==

''待考据''

== 相关页面 ==

* [[道统丨神通丨仙基]]
* [[道统-{daotong}|{daotong}]]

[[Category:神通]]
[[Category:修炼体系]]
"""
    path.write_text(text, encoding='utf-8')
    return True


def main() -> int:
    if not AUTH_MD.exists():
        print(f'错误: 找不到权威文件 {AUTH_MD}', file=sys.stderr)
        return 1

    print('== 解析权威Markdown ==')
    auth = parse_authority_md()
    print(f'  共解析道统 {len(auth)} 个,神通行 {sum(len(v) for v in auth.values())} 条\n')

    print('== 同步道统页面 ==')
    updated = 0
    not_found = []
    for daotong, rows in auth.items():
        path = daotong_page_path(daotong)
        if not path:
            not_found.append(daotong)
            continue
        if update_daotong_page(path, rows):
            updated += 1
            print(f'  ✓ 更新 {path.name} ({len(rows)} 条神通)')
    if not_found:
        print(f'\n  ! 未找到道统页面: {not_found}')
    print(f'\n  共更新 {updated} 个道统页面')

    print('\n== 补建缺失的神通页面 ==')
    created = 0
    for daotong, rows in auth.items():
        for row in rows:
            if ensure_shentong_page(daotong, row):
                created += 1
                print(f'  + 新建 神通-{row["name"]}.wiki')
    print(f'\n  共补建 {created} 个神通页面')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())