#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将原文考据结构化JSON中的数据批量更新到对应的wiki文件中。
在每个神通wiki文件的"== 相关页面 =="之前插入"== 原文考据 =="章节。
"""

import json
import os
from pathlib import Path


def load_kaoju_data(json_path):
    """加载考据JSON数据，构建 神通名称 -> 考据信息 的映射"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 构建映射: 神通名称 -> { 体系, 道统, 匹配总数, 保留策略, 原文出处列表 }
    shentong_map = {}
    
    for tixi in data["体系列表"]:
        tixi_name = tixi["体系名称"]
        for weizhi in tixi["位置列表"]:
            daotong_name = weizhi["道统"]
            for st in weizhi["神通列表"]:
                st_name = st["神通名称"]
                key = st_name
                
                entry = {
                    "体系": tixi_name,
                    "道统": daotong_name,
                    "神通类别": st.get("神通类别", "—"),
                    "古称别称": st.get("古称别称", "—"),
                    "匹配总数": st.get("匹配总数", 0),
                    "保留策略": st.get("保留策略", ""),
                    "原文出处": st.get("原文出处", [])
                }
                
                # 如果同名神通出现在多个道统中，用列表存储
                if key not in shentong_map:
                    shentong_map[key] = []
                shentong_map[key].append(entry)
    
    return shentong_map


def format_kaoju_section(entries):
    """将考据条目格式化为wiki文本"""
    lines = []
    lines.append("")
    lines.append("== 原文考据 ==")
    lines.append("")
    
    for entry in entries:
        total = entry["匹配总数"]
        strategy = entry["保留策略"]
        quotes = entry["原文出处"]
        
        if len(entries) > 1:
            lines.append(f"=== {entry['道统']}道统下 ===")
            lines.append("")
        
        if total == 0:
            lines.append("截至第1480章，未检得原文出处。")
            lines.append("")
            continue
        
        # 匹配信息
        info_parts = [f"共 {total} 处匹配"]
        if strategy:
            info_parts.append(strategy)
        lines.append(f"原文出处（{'，'.join(info_parts)}）：")
        lines.append("")
        
        # 原文引用列表
        for q in quotes:
            seq = q["序号"]
            ch_num = q["章节号"]
            ch_name = q["章节名"]
            text = q["原文摘录"]
            tags = q.get("标记", [])
            
            tag_str = ""
            if tags:
                tag_str = " " + " ".join(f"[{t}]" for t in tags)
            
            lines.append(f"# '''第{ch_num}章《{ch_name}》'''{tag_str}")
            # 引用文本，用wiki的blockquote格式
            # 将换行替换为空格，保持单行
            clean_text = text.replace('\n', ' ').strip()
            if clean_text:
                lines.append(f"#: <small>{clean_text}</small>")
        
        lines.append("")
    
    return '\n'.join(lines)


def update_wiki_file(wiki_path, kaoju_section):
    """更新wiki文件，在"== 相关页面 =="之前插入考据章节"""
    with open(wiki_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 如果已经有原文考据章节，先移除旧的
    if '== 原文考据 ==' in content:
        # 找到原文考据章节的开始和结束位置
        start_idx = content.index('== 原文考据 ==')
        # 找到下一个 == 章节标题（相关页面或Category）
        rest = content[start_idx + len('== 原文考据 =='):]
        # 寻找下一个 == 开头的行
        lines_after = rest.split('\n')
        end_offset = 0
        found_next = False
        for i, line in enumerate(lines_after):
            if i == 0:
                continue
            if line.startswith('== ') or line.startswith('[[Category:'):
                end_offset = sum(len(l) + 1 for l in lines_after[:i])
                found_next = True
                break
        
        if found_next:
            # 去掉前面可能的空行
            before = content[:start_idx].rstrip('\n')
            after = content[start_idx + len('== 原文考据 ==') + end_offset:]
            content = before + '\n\n' + after
        else:
            # 没找到下一个章节，保持原样
            pass
    
    # 在"== 相关页面 =="之前插入
    insert_marker = '== 相关页面 =='
    if insert_marker in content:
        idx = content.index(insert_marker)
        # 确保前面有适当的空行
        before = content[:idx].rstrip('\n')
        after = content[idx:]
        content = before + '\n' + kaoju_section + '\n' + after
    else:
        # 如果没有"相关页面"章节，在 [[Category: 之前插入
        cat_marker = '[[Category:'
        if cat_marker in content:
            idx = content.index(cat_marker)
            before = content[:idx].rstrip('\n')
            after = content[idx:]
            content = before + '\n' + kaoju_section + '\n' + after
        else:
            # 直接追加到末尾
            content = content.rstrip('\n') + '\n' + kaoju_section + '\n'
    
    with open(wiki_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True


def main():
    base_dir = Path(__file__).parent
    json_path = base_dir / "资料库 - 神通" / "04_参考权威" / "玄鉴仙族_五德位业体系_原文考据_结构化.json"
    wiki_dir = base_dir / "pages" / "仙基道统" / "神通"
    
    print(f"加载考据数据: {json_path}")
    shentong_map = load_kaoju_data(json_path)
    print(f"  共 {len(shentong_map)} 个神通条目")
    
    # 获取所有wiki文件
    wiki_files = list(wiki_dir.glob("神通-*.wiki"))
    print(f"  共 {len(wiki_files)} 个wiki文件")
    
    # 统计
    updated = 0
    skipped = 0
    not_found = 0
    
    for wiki_file in sorted(wiki_files):
        # 从文件名提取神通名称: "神通-背南行.wiki" -> "背南行"
        st_name = wiki_file.stem.replace("神通-", "")
        
        if st_name in shentong_map:
            entries = shentong_map[st_name]
            # 只处理有原文出处的条目
            has_quotes = any(len(e["原文出处"]) > 0 for e in entries)
            
            if has_quotes:
                kaoju_section = format_kaoju_section(entries)
                update_wiki_file(wiki_file, kaoju_section)
                updated += 1
            else:
                # 没有原文出处，添加"未检得"说明
                kaoju_section = format_kaoju_section(entries)
                update_wiki_file(wiki_file, kaoju_section)
                updated += 1
        else:
            not_found += 1
            if not_found <= 10:
                print(f"  ⚠️ 考据数据中未找到: {st_name}")
    
    print(f"\n完成:")
    print(f"  ✅ 已更新: {updated} 个wiki文件")
    print(f"  ⚠️ 未找到考据: {not_found} 个wiki文件")
    print(f"  ⏭️ 跳过: {skipped} 个wiki文件")


if __name__ == '__main__':
    main()
