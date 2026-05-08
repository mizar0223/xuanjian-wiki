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
import os
from pathlib import Path


def fix_match_info(content):
    """删除'原文出处'行中的匹配统计信息"""
    # 匹配 "原文出处（共 X 处匹配，全量保留）：" 或 "原文出处（共 X 处匹配，智能抽样）："
    content = re.sub(
        r'原文出处（共 \d+ 处匹配[^）]*）：',
        '原文出处：',
        content
    )
    # 也处理没有冒号的情况
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
    
    # 2. 修正加更数字格式
    # 模式：加更X/Y，其中原文是 加更XY（数字连在一起）
    # 需要根据总数的位数来分割
    
    # 处理 "加更" 后面跟数字的情况
    # 已知的总数有：10, 20, 112, 113
    # 规则：总数在末尾，前面是序号
    
    def fix_jiageng_number(match):
        prefix = match.group(1)  # "加更" 前面的文字（如"潜龙勿用"）
        num_str = match.group(2)  # 连在一起的数字
        suffix = match.group(3)  # 后面的字符（通常是"）"）
        
        # 尝试不同的总数分割方式
        # 优先尝试3位总数（如113, 112）
        if len(num_str) >= 4:
            # 尝试3位总数
            total_3 = num_str[-3:]
            seq_3 = num_str[:-3]
            if seq_3 and int(seq_3) < int(total_3):
                return f"加更{prefix}{seq_3}/{total_3}{suffix}"
        
        if len(num_str) >= 3:
            # 尝试2位总数
            total_2 = num_str[-2:]
            seq_2 = num_str[:-2]
            if seq_2 and int(seq_2) <= int(total_2):
                return f"加更{prefix}{seq_2}/{total_2}{suffix}"
        
        # 如果都不匹配，保持原样
        return match.group(0)
    
    # 匹配 "加更" + 可选文字 + 数字 + "）"
    # 例如：加更14113）、加更31112）
    content = re.sub(
        r'加更([^0-9）]*)(\d{3,})（?）?',
        lambda m: fix_jiageng_number(m),
        content
    )
    
    # 更精确的处理：直接匹配已知模式
    # 处理 "潜龙勿用加更XXXXX）" 格式
    def fix_known_patterns(content):
        # 潜龙勿用加更X/113 (总数113)
        content = re.sub(r'潜龙勿用加更(\d{1,2})113）', r'潜龙勿用加更\1/113）', content)
        # 潜龙勿用黄金盟加更X/113
        content = re.sub(r'潜龙勿用黄金盟加更(\d{1,2})113）', r'潜龙勿用黄金盟加更\1/113）', content)
        # 潜龙加更X/112
        content = re.sub(r'潜龙加更(\d{1,2})112）', r'潜龙加更\1/112）', content)
        # 潜龙大佬白银加更X/20
        content = re.sub(r'潜龙大佬白银加更(\d{1,2})20）', r'潜龙大佬白银加更\1/20）', content)
        # 小指勾尚白银盟加更X/10
        content = re.sub(r'小指勾尚白银盟加更(\d{1,2})10）', r'小指勾尚白银盟加更\1/10）', content)
        # 碎星小左轮加更X/2
        content = re.sub(r'碎星小左轮加更(\d)2）', r'碎星小左轮加更\1/2）', content)
        # 萧真人白银X/2
        content = re.sub(r'萧真人白银(\d)2）', r'萧真人白银\1/2）', content)
        # 那年的小明白银X/2
        content = re.sub(r'那年的小明白银(\d)2）', r'那年的小明白银\1/2）', content)
        # 艾黛儿贾特X/2
        content = re.sub(r'艾黛儿贾特(\d)2）', r'艾黛儿贾特\1/2）', content)
        # 荣耀五星加更 - 无数字后缀的不需要处理
        return content
    
    content = fix_known_patterns(content)
    
    return content


def process_wiki_file(filepath):
    """处理单个wiki文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # 1. 删除匹配统计信息
    content = fix_match_info(content)
    
    # 2. 修正章节名格式
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
    
    # 验证：检查是否还有未处理的模式
    remaining_match = 0
    remaining_fraction = 0
    for wiki_file in wiki_dir.glob("*.wiki"):
        with open(wiki_file, 'r', encoding='utf-8') as f:
            content = f.read()
        if re.search(r'共 \d+ 处匹配', content):
            remaining_match += 1
        if '（112）' in content or '（212）' in content:
            remaining_fraction += 1
    
    print(f"\n验证:")
    print(f"  残留'共X处匹配': {remaining_match} 个文件")
    print(f"  残留'（112）/（212）': {remaining_fraction} 个文件")


if __name__ == '__main__':
    main()
