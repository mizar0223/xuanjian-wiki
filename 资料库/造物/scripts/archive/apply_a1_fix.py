#!/usr/bin/env python3
"""执行 A1 修复：人物裸链接加前缀"""
import re
from pathlib import Path

ROOT = Path("/data/workspace/rq0rlzeg/xuanjian-wiki/资料库/造物/pages")

PEOPLE = {
    '司元白', '旬邑子', '李周巍', '李尺泾', '李曦峻', '李曦明',
    '李清虹', '李渊修', '李渊蛟', '李玄锋', '李通崖', '李遂宁',
    '李阙宛', '迟步梓', '郗常', '陆江仙'
}

# 匹配 [[人物名]] 或 [[人物名|显示文本]]
LINK_PAT = re.compile(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]')

def fix_line(line):
    """替换一行中的人物裸链接"""
    def repl(m):
        target = m.group(1).strip()
        display = m.group(2)
        if target in PEOPLE:
            if display:
                return f'[[人物-{target}|{display}]]'
            else:
                return f'[[人物-{target}|{target}]]'
        return m.group(0)
    return LINK_PAT.sub(repl, line)

def main():
    total_files = 0
    total_fixes = 0
    fixed_files = []

    for wiki_file in sorted(ROOT.rglob("*.wiki")):
        rel = str(wiki_file.relative_to(ROOT))
        try:
            text = wiki_file.read_text(encoding='utf-8')
        except Exception:
            continue

        new_lines = []
        file_fixes = 0
        changed = False
        for line in text.split('\n'):
            new_line = fix_line(line)
            if new_line != line:
                file_fixes += 1
                changed = True
            new_lines.append(new_line)

        if changed:
            wiki_file.write_text('\n'.join(new_lines), encoding='utf-8')
            total_files += 1
            total_fixes += file_fixes
            fixed_files.append(f"{rel} ({file_fixes}处)")

    # 写日志
    log_path = Path("/data/workspace/rq0rlzeg/xuanjian-wiki/资料库/造物/.workbuddy/a1_fix_log.md")
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write("# A1 修复日志\n\n")
        f.write(f"修复文件数: {total_files}\n")
        f.write(f"修复链接数: {total_fixes}\n\n")
        f.write("## 修改文件清单\n\n")
        for item in fixed_files:
            f.write(f"- {item}\n")

    print(f"A1 修复完成: {total_files} 个文件, {total_fixes} 处链接")
    print(f"日志: {log_path}")

if __name__ == "__main__":
    main()
