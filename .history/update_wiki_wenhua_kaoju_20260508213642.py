#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将文化考据数据批量更新到对应的wiki文件中。
在"== 原文考据 =="之后、"== 相关页面 =="之前插入"== 文化考据 =="章节。
有考据的填入内容，无考据的标记为"待考据"。
"""

import re
import os
from pathlib import Path


def parse_wenhua_kaoju(filepath):
    """解析文化考据Markdown文件，提取每个神通的考据内容"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    # 找到所有 #### 开头的条目
    kaoju_map = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        # 匹配: #### 勿查我（上巫）
        match = re.match(r'^#### (.+?)（(.+?)）', line)
        if match:
            st_name = match.group(1).strip()
            daotong = match.group(2).strip()
            
            # 收集该条目的所有内容直到下一个 #### 或文件结束
            i += 1
            content_lines = []
            while i < len(lines):
                if lines[i].startswith('#### '):
                    break
                content_lines.append(lines[i])
                i += 1
            
            # 解析各维度内容
            raw_content = '\n'.join(content_lines).strip()
            
            # 提取各维度
            dimensions = {}
            current_dim = None
            current_content = []
            
            for cl in content_lines:
                # 匹配维度标题: **字义训诂**：
                dim_match = re.match(r'^\*\*(.+?)\*\*[：:]', cl)
                if dim_match:
                    if current_dim:
                        dimensions[current_dim] = '\n'.join(current_content).strip()
                    current_dim = dim_match.group(1).strip()
                    current_content = []
                else:
                    if current_dim:
                        current_content.append(cl)
            
            if current_dim:
                dimensions[current_dim] = '\n'.join(current_content).strip()
            
            kaoju_map[st_name] = {
                "道统": daotong,
                "维度": dimensions,
                "原始内容": raw_content
            }
            continue
        
        i += 1
    
    return kaoju_map


def format_wiki_kaoju(entry):
    """将考据条目格式化为wiki文本"""
    lines = []
    
    dimensions = entry["维度"]
    
    # 按照SOP中的七维顺序输出
    dim_order = ["字义训诂", "道教典籍", "中医经典", "诗歌典籍", "民俗文化", "道统象征关联", "综合考据"]
    
    for dim_name in dim_order:
        if dim_name in dimensions:
            content = dimensions[dim_name]
            # 清理引用标记
            # 去掉 > 前缀，转为wiki格式
            clean_lines = []
            for cl in content.split('\n'):
                cl = cl.strip()
                if cl.startswith('>'):
                    cl = cl.lstrip('> ').strip()
                if cl:
                    clean_lines.append(cl)
            
            if clean_lines:
                lines.append(f"=== {dim_name} ===")
                lines.append("")
                for cl in clean_lines:
                    lines.append(f": {cl}")
                lines.append("")
    
    return '\n'.join(lines)


def update_wiki_file(wiki_path, kaoju_section):
    """更新wiki文件，在"== 相关页面 =="之前插入文化考据章节"""
    with open(wiki_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 如果已经有文化考据章节，先移除旧的
    if '== 文化考据 ==' in content:
        # 找到文化考据章节的开始位置
        start_idx = content.index('== 文化考据 ==')
        # 找到前面的内容（去掉尾部空行）
        before = content[:start_idx].rstrip('\n')
        
        # 找到文化考据之后的下一个 == 章节
        rest = content[start_idx:]
        rest_lines = rest.split('\n')
        end_offset = 0
        found_next = False
        for idx, rl in enumerate(rest_lines):
            if idx == 0:
                continue
            if rl.startswith('== ') or rl.startswith('[[Category:'):
                end_offset = sum(len(l) + 1 for l in rest_lines[:idx])
                found_next = True
                break
        
        if found_next:
            after = rest[end_offset:]
            content = before + '\n\n' + after
        # 如果没找到下一个章节，保持原样
    
    # 在"== 相关页面 =="之前插入
    insert_marker = '== 相关页面 =='
    if insert_marker in content:
        idx = content.index(insert_marker)
        before = content[:idx].rstrip('\n')
        after = content[idx:]
        content = before + '\n\n' + kaoju_section + '\n' + after
    else:
        # 如果没有"相关页面"章节，在 [[Category: 之前插入
        cat_marker = '[[Category:'
        if cat_marker in content:
            idx = content.index(cat_marker)
            before = content[:idx].rstrip('\n')
            after = content[idx:]
            content = before + '\n\n' + kaoju_section + '\n' + after
        else:
            content = content.rstrip('\n') + '\n\n' + kaoju_section + '\n'
    
    with open(wiki_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True


def main():
    base_dir = Path(__file__).parent
    kaoju_file = base_dir / "资料库 - 神通" / "04_参考权威" / "玄鉴仙族_五德位业体系_文化考据.md"
    wiki_dir = base_dir / "pages" / "仙基道统" / "神通"
    
    print(f"加载文化考据数据: {kaoju_file}")
    kaoju_map = parse_wenhua_kaoju(kaoju_file)
    print(f"  共 {len(kaoju_map)} 个考据条目")
    
    # 获取所有wiki文件
    wiki_files = list(wiki_dir.glob("神通-*.wiki"))
    print(f"  共 {len(wiki_files)} 个wiki文件")
    
    # 统计
    updated_with_kaoju = 0
    updated_pending = 0
    
    for wiki_file in sorted(wiki_files):
        # 从文件名提取神通名称
        st_name = wiki_file.stem.replace("神通-", "")
        
        if st_name in kaoju_map:
            # 有考据数据
            entry = kaoju_map[st_name]
            wiki_content = format_wiki_kaoju(entry)
            
            kaoju_section = f"== 文化考据 ==\n\n{wiki_content}"
            update_wiki_file(wiki_file, kaoju_section)
            updated_with_kaoju += 1
        else:
            # 无考据数据，标记为待考据
            kaoju_section = "== 文化考据 ==\n\n''待考据''\n"
            update_wiki_file(wiki_file, kaoju_section)
            updated_pending += 1
    
    print(f"\n完成:")
    print(f"  ✅ 已填入考据: {updated_with_kaoju} 个wiki文件")
    print(f"  ⏳ 标记待考据: {updated_pending} 个wiki文件")
    print(f"  📊 总计更新: {updated_with_kaoju + updated_pending} 个wiki文件")


if __name__ == '__main__':
    main()
