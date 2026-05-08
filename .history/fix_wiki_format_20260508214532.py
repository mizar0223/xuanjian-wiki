#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量调整wiki文件中的章节名格式：
1. 删除"原文出处"行中的"（共 X 处匹配，全量保留）"等提示文字
2. 修正章节名中的格式：
   - （112）→（1+1/2）
   - （潜龙勿用加更14113）→（潜龙勿用加更14/113）
"""

import re
from pathlib import Path


def fix_match_info(content):
    """删除'原文出处'行中的匹配统计信息"""
    content = re.sub(
        r'原文出处（共 \d+ 处匹配[^）]*）：',
        '原文出处：',
        content
    )
    content = re.sub(
        r'原文出处（共 \d+ 处匹配[^）]*）',
        '原文出处',
        content
    )
    return content


def fix_chapter_fraction(content):
    """修正章节名中的分数格式"""
    # 1. 修正 （112）→（1+1/2）和 （212）→（2+1/2）
    content = content.replace('（112）', '（1+1/2）')
    content = content.replace('（212）', '（2+1/2）')
    
    # 2. 使用精确模式匹配已知的加更格式
    # 总数113的：潜龙勿用加更X113 → 潜龙勿用加更X/113
    content = re.sub(r'潜龙勿用加更(\d{1,2})113）', r'潜龙勿用加更\1/113）', content)
    # 潜龙勿用黄金盟加更X113 → 潜龙勿用黄金盟加更X/113
    content = re.sub(r'潜龙勿用黄金盟加更(\d{1,2})113）', r'潜龙勿用黄金盟加更\1/113）', content)
    # 潜龙加更X112 → 潜龙加更X/112
    content = re.sub(r'潜龙加更(\d{1,2})112）', r'潜龙加更\1/112）', content)
    # 潜龙大佬白银加更X20 → 潜龙大佬白银加更X/20
    content = re.sub(r'潜龙大佬白银加更(\d{1,2})20）', r'潜龙大佬白银加更\1/20）', content)
    # 小指勾尚白银盟加更X10 → 小指勾尚白银盟加更X/10
    content = re.sub(r'小指勾尚白银盟加更(\d{1,2})10）', r'小指勾尚白银盟加更\1/10）', content)
    # 碎星小左轮加更12 → 碎星小左轮加更1/2
    content = re.sub(r'碎星小左轮加更(\d)2）', r'碎星小左轮加更\1/2）', content)
    # 萧真人白银12 → 萧真人白银1/2
    content = re.sub(r'萧真人白银(\d)2）', r'萧真人白银\1/2）', content)
    # 那年的小明白银12 → 那年的小明白银1/2
    content = re.sub(r'那年的小明白银(\d)2）', r'那年的小明白银\1/2）', content)
    # 艾黛儿贾特22 → 艾黛儿贾特2/2
    content = re.sub(r'艾黛儿贾特(\d)2）', r'艾黛儿贾特\1/2）', content)
    
    return content


def process_wiki_file(filepath):
    """处理单个wiki文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    content = fix_match_info(content)
    content = fix_chapter_fraction(content)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def main():
    wiki_dir = Path(__file__).parent / "pages" / "仙基道统" / "神通"
    wiki_files = list(wiki_dir.glob("*.wiki"))
    print(f"共 {len(wiki_files)} 个wiki文件")
    
    modified = 0
    for wiki_file in sorted(wiki_files):
        if process_wiki_file(wiki_file):
            modified += 1
    
    print(f"✅ 已修改: {modified} 个文件")
    
    # 验证
    remaining_match = 0
    remaining_fraction = 0
    remaining_jiageng = 0
    for wiki_file in wiki_dir.glob("*.wiki"):
        with open(wiki_file, 'r', encoding='utf-8') as f:
            content = f.read()
        if re.search(r'共 \d+ 处匹配', content):
            remaining_match += 1
        if '（112）' in content or '（212）' in content:
            remaining_fraction += 1
        # 检查是否还有未处理的连续数字加更格式
        if re.search(r'加更\d{3,}）', content):
            remaining_jiageng += 1
    
    print(f"\n验证:")
    print(f"  残留'共X处匹配': {remaining_match} 个文件")
    print(f"  残留'（112）/（212）': {remaining_fraction} 个文件")
    print(f"  残留'加更+连续数字': {remaining_jiageng} 个文件")


if __name__ == '__main__':
    main()
