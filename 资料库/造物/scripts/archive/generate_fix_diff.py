#!/usr/bin/env python3
"""生成 A1+A2 红链修复 diff 报告（审阅模式）"""
import re
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path("/data/workspace/rq0rlzeg/xuanjian-wiki/资料库/造物/pages")
REPORT = Path("/data/workspace/rq0rlzeg/xuanjian-wiki/资料库/造物/.workbuddy/red_links_fix_diff.md")

# 人物名单（本地 pages/20-人物/ 下存在的）
PEOPLE = {
    '司元白', '旬邑子', '李周巍', '李尺泾', '李曦峻', '李曦明',
    '李清虹', '李渊修', '李渊蛟', '李玄锋', '李通崖', '李遂宁',
    '李阙宛', '迟步梓', '郗常', '陆江仙'
}

# 品阶/类型标签词（误链，应改为纯文本）
RANK_TAGS = {
    '灵物', '灵宝', '灵器', '灵资', '材料',
    '筑基法器', '紫府灵资', '筑基法剑', '紫府灵物',
    '紫府灵丹', '极品灵气', '待分类', '紫府灵器',
    '筑基灵物', '符箓', '丹药', '法器', '凡器', '灵气',
    '古灵器/灵宝', '道胎法旨'
}

LINK_PAT = re.compile(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]')

def analyze_file(wiki_file):
    """分析单个文件，返回建议修改列表"""
    try:
        text = wiki_file.read_text(encoding='utf-8')
    except Exception as e:
        return []

    fixes = []
    lines = text.split('\n')
    for line_no, line in enumerate(lines, 1):
        for m in LINK_PAT.finditer(line):
            target = m.group(1).strip()
            display = m.group(2)
            original = m.group(0)

            if not target:
                continue
            # 跳过已有命名空间的
            if '-' in target and target.split('-', 1)[0] in (
                '造物', '人物', '道统', '势力', '神通', '事件', '地点', 'Category', 'File', 'Image'
            ):
                continue

            # A1: 人物裸链接
            if target in PEOPLE:
                if display:
                    replacement = f'[[人物-{target}|{display}]]'
                else:
                    replacement = f'[[人物-{target}|{target}]]'
                fixes.append({
                    'line_no': line_no,
                    'line': line,
                    'original': original,
                    'replacement': replacement,
                    'reason': f'A1-人物裸链接: [[{target}]] → [[人物-{target}]]',
                    'type': 'A1'
                })
            # A2: 品阶标签误链
            elif target in RANK_TAGS:
                if display:
                    replacement = display
                else:
                    replacement = target
                fixes.append({
                    'line_no': line_no,
                    'line': line,
                    'original': original,
                    'replacement': replacement,
                    'reason': f'A2-品阶误链: [[{target}]] → 纯文本「{replacement}」',
                    'type': 'A2'
                })

    return fixes

def main():
    all_fixes = []
    file_fixes = defaultdict(list)
    type_counter = Counter()

    for wiki_file in sorted(ROOT.rglob("*.wiki")):
        rel = str(wiki_file.relative_to(ROOT))
        fixes = analyze_file(wiki_file)
        for f in fixes:
            f['file'] = rel
            file_fixes[rel].append(f)
            all_fixes.append(f)
            type_counter[f['type']] += 1

    # 写报告
    with open(REPORT, 'w', encoding='utf-8') as out:
        out.write("# A1+A2 红链修复 Diff 报告（审阅模式）\n\n")
        out.write(f"**扫描范围**: 全部 {len(list(ROOT.rglob('*.wiki')))} 个 .wiki 文件\n")
        out.write(f"**建议修改总数**: {len(all_fixes)} 处\n")
        out.write(f"**涉及文件数**: {len(file_fixes)} 个\n")
        out.write(f"- A1 人物裸链接: {type_counter['A1']} 处\n")
        out.write(f"- A2 品阶误链: {type_counter['A2']} 处\n\n")

        out.write("---\n\n")
        out.write("## 修复规则说明\n\n")
        out.write("### A1: 人物裸链接（加 `人物-` 前缀）\n")
        out.write("以下人物名在本地存在页面，裸链接 `[[人物名]]` 统一改为 `[[人物-人物名|人物名]]`：\n\n")
        out.write(", ".join(sorted(PEOPLE)))
        out.write("\n\n")
        out.write("### A2: 品阶标签误链（改为纯文本）\n")
        out.write("以下品阶/类型词作为内链指向不存在的页面，改为纯文本：\n\n")
        out.write(", ".join(sorted(RANK_TAGS)))
        out.write("\n\n")
        out.write("**保留书名号规则**: 如果原文中链接被书名号包裹（如《[[灵物]]》），修复后变为《灵物》，书名号保留。\n\n")

        out.write("---\n\n")
        out.write("## 按文件列出修改（TOP 50 文件）\n\n")

        sorted_files = sorted(file_fixes.items(), key=lambda x: len(x[1]), reverse=True)
        for rank, (rel, fixes) in enumerate(sorted_files[:50], 1):
            out.write(f"### {rank}. {rel}（{len(fixes)} 处）\n\n")
            for f in fixes:
                out.write(f"**行 {f['line_no']}** — {f['reason']}\n")
                out.write(f"```diff\n")
                out.write(f"- {f['line'].rstrip()}\n")
                # 构造修改后的行
                new_line = f['line'].replace(f['original'], f['replacement'], 1)
                out.write(f"+ {new_line.rstrip()}\n")
                out.write(f"```\n\n")

        # 汇总统计
        out.write("---\n\n")
        out.write("## 全部文件修改统计\n\n")
        out.write("| 排名 | 文件路径 | A1 | A2 | 总计 |\n")
        out.write("|-----|---------|----|----|-----|\n")
        for rank, (rel, fixes) in enumerate(sorted_files, 1):
            a1 = sum(1 for f in fixes if f['type'] == 'A1')
            a2 = sum(1 for f in fixes if f['type'] == 'A2')
            out.write(f"| {rank} | {rel} | {a1} | {a2} | {len(fixes)} |\n")

    print(f"Diff 报告已生成: {REPORT}")
    print(f"总计建议修改: {len(all_fixes)} 处 (A1={type_counter['A1']}, A2={type_counter['A2']})")
    print(f"涉及文件: {len(file_fixes)} 个")

if __name__ == "__main__":
    main()
