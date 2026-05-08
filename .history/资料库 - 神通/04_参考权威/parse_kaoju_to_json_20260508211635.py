#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将《玄鉴仙族》五德位业体系原文考据完整版 Markdown 文件解析为结构化 JSON。
"""

import re
import json
from pathlib import Path

def parse_kaoju_md(filepath):
    """解析原文考据 Markdown 文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    result = {
        "元数据": {
            "标题": "《玄鉴仙族》五德位业体系 · 原文考据标准化文档（完整版）",
            "来源文件": "玄鉴仙族_五德位业体系_原文考据_完整版.md",
            "版本": "结构化版",
            "说明": "基于原著第1-1480章检索每个道统、神通/仙基的原文出处，记录所在章节号、章节名及上下文描写。",
            "检索范围": "第1章 ~ 第1480章",
            "检索关键词数": 307,
            "原始匹配数": 14191,
            "体系道统数": 59,
            "神通仙基条目数": 206,
            "有原文出处": 192,
            "无原文出处": 14,
            "生成日期": "2026-05-08"
        },
        "未检得条目": [],
        "体系列表": []
    }
    
    # 解析未检得条目（第三节）
    未检得_pattern = re.compile(r'- \*\*\[(.+?)\]\*\* (.+?)（古称/别称：(.+?)）')
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 解析未检得条目
        m = 未检得_pattern.match(line.strip())
        if m:
            path_str = m.group(1)
            name = m.group(2)
            alias = m.group(3)
            parts = path_str.split(' - ')
            result["未检得条目"].append({
                "体系路径": path_str,
                "神通名称": name,
                "古称别称": alias if alias != "无" else "—"
            })
        
        i += 1
    
    # 重新遍历，解析体系结构
    i = 0
    current_tixi = None
    current_weizhi = None
    current_shentong = None
    
    while i < len(lines):
        line = lines[i]
        
        # 匹配体系大标题: ### 【木德】
        tixi_match = re.match(r'^### 【(.+?)】', line)
        if tixi_match:
            current_tixi = {
                "体系名称": tixi_match.group(1),
                "位置列表": []
            }
            result["体系列表"].append(current_tixi)
            current_weizhi = None
            current_shentong = None
            i += 1
            continue
        
        # 匹配位置标题: #### 正位 - 正木
        weizhi_match = re.match(r'^#### (.+?) - (.+)', line)
        if weizhi_match and current_tixi is not None:
            weizhi_type = weizhi_match.group(1).strip()
            weizhi_name = weizhi_match.group(2).strip()
            current_weizhi = {
                "位置类型": weizhi_type,
                "位置名称": weizhi_name,
                "道统": weizhi_name,
                "道统原文出处": [],
                "神通列表": []
            }
            current_tixi["位置列表"].append(current_weizhi)
            current_shentong = None
            
            # 接下来解析道统原文出处
            i += 1
            # 跳过空行
            while i < len(lines) and lines[i].strip() == '':
                i += 1
            
            # 检查是否有道统原文出处标题
            if i < len(lines) and '道统' in lines[i] and '原文出处' in lines[i]:
                # 解析匹配数信息
                header_line = lines[i]
                match_info = re.search(r'共 (\d+) 处匹配', header_line)
                display_info = re.search(r'展示 (\d+) 处', header_line)
                total_matches = int(match_info.group(1)) if match_info else 0
                display_count = int(display_info.group(1)) if display_info else total_matches
                
                current_weizhi["道统匹配总数"] = total_matches
                current_weizhi["道统展示数"] = display_count
                
                i += 1
                # 解析原文条目
                while i < len(lines):
                    entry_line = lines[i].strip()
                    
                    # 遇到神通标题或下一个位置标题则停止
                    if entry_line.startswith('**◆') or entry_line.startswith('####') or entry_line.startswith('###'):
                        break
                    
                    # 匹配原文条目: 数字. **第XXX章《YYY》** [标记]
                    entry_match = re.match(r'(\d+)\.\s+\*\*第(\d+)章《(.+?)》\*\*\s*(.*)', entry_line)
                    if entry_match:
                        entry_num = int(entry_match.group(1))
                        chapter_num = int(entry_match.group(2))
                        chapter_name = entry_match.group(3)
                        tag_str = entry_match.group(4).strip()
                        
                        tags = []
                        if '[首次]' in tag_str or '「首次」' in tag_str:
                            tags.append("首次")
                        if '[最新]' in tag_str or '「最新」' in tag_str:
                            tags.append("最新")
                        
                        # 读取引用内容（下一行以 > 开头）
                        quote_lines = []
                        i += 1
                        while i < len(lines):
                            ql = lines[i]
                            if ql.strip().startswith('>'):
                                quote_lines.append(ql.strip().lstrip('> ').strip())
                                i += 1
                            elif ql.strip() == '':
                                i += 1
                                # 检查下一行是否还是引用
                                if i < len(lines) and lines[i].strip().startswith('>'):
                                    continue
                                break
                            else:
                                break
                        
                        quote_text = '\n'.join(quote_lines)
                        
                        entry_obj = {
                            "序号": entry_num,
                            "章节号": chapter_num,
                            "章节名": chapter_name,
                            "原文摘录": quote_text
                        }
                        if tags:
                            entry_obj["标记"] = tags
                        
                        current_weizhi["道统原文出处"].append(entry_obj)
                        continue
                    
                    i += 1
                continue
            else:
                continue
        
        # 匹配神通标题: **◆ 木成方** - 命 （古称/别称：天下易）
        shentong_match = re.match(r'^\*\*◆ (.+?)\*\*\s*(.*)', line)
        if shentong_match and current_weizhi is not None:
            name_part = shentong_match.group(1).strip()
            rest_part = shentong_match.group(2).strip()
            
            # 解析神通类别
            category = "—"
            cat_match = re.match(r'^-\s*(.+?)(?:\s|$|（)', rest_part)
            if cat_match:
                category = cat_match.group(1).strip()
            
            # 解析古称/别称
            alias = "—"
            alias_match = re.search(r'（古称/别称：(.+?)）', rest_part)
            if alias_match:
                alias = alias_match.group(1)
            
            current_shentong = {
                "神通名称": name_part,
                "神通类别": category,
                "古称别称": alias,
                "原文出处": []
            }
            current_weizhi["神通列表"].append(current_shentong)
            
            i += 1
            # 跳过空行
            while i < len(lines) and lines[i].strip() == '':
                i += 1
            
            # 解析匹配信息行
            if i < len(lines):
                info_line = lines[i].strip()
                match_info = re.search(r'匹配 (\d+) 处', info_line)
                if match_info:
                    current_shentong["匹配总数"] = int(match_info.group(1))
                    if '全量保留' in info_line:
                        current_shentong["保留策略"] = "全量保留"
                    elif '智能抽样' in info_line:
                        sample_match = re.search(r'抽样\((\d+)/(\d+)\)', info_line)
                        if sample_match:
                            current_shentong["保留策略"] = f"智能抽样({sample_match.group(1)}/{sample_match.group(2)})"
                        else:
                            current_shentong["保留策略"] = "智能抽样"
                    i += 1
                elif '未检得' in info_line or '无原文' in info_line:
                    current_shentong["匹配总数"] = 0
                    current_shentong["保留策略"] = "无原文出处"
                    i += 1
            
            # 跳过空行
            while i < len(lines) and lines[i].strip() == '':
                i += 1
            
            # 解析原文条目
            while i < len(lines):
                entry_line = lines[i].strip()
                
                # 遇到下一个神通标题、位置标题或体系标题则停止
                if entry_line.startswith('**◆') or entry_line.startswith('####') or entry_line.startswith('###'):
                    break
                
                # 匹配原文条目（两种格式）
                # 格式1: 数字. **第XXX章《YYY》**
                # 格式2: 缩进的  数字. **第XXX章《YYY》**
                entry_match = re.match(r'\s*(\d+)\.\s+\*\*第(\d+)章《(.+?)》\*\*\s*(.*)', entry_line)
                if entry_match:
                    entry_num = int(entry_match.group(1))
                    chapter_num = int(entry_match.group(2))
                    chapter_name = entry_match.group(3)
                    tag_str = entry_match.group(4).strip()
                    
                    tags = []
                    if '[首次]' in tag_str or '「首次」' in tag_str:
                        tags.append("首次")
                    if '[最新]' in tag_str or '「最新」' in tag_str:
                        tags.append("最新")
                    
                    # 读取引用内容
                    quote_lines = []
                    i += 1
                    while i < len(lines):
                        ql = lines[i]
                        if ql.strip().startswith('>'):
                            quote_lines.append(ql.strip().lstrip('> ').strip())
                            i += 1
                        elif ql.strip() == '':
                            i += 1
                            # 检查下一行是否还是引用或条目
                            if i < len(lines) and lines[i].strip().startswith('>'):
                                continue
                            break
                        else:
                            break
                    
                    quote_text = '\n'.join(quote_lines)
                    
                    entry_obj = {
                        "序号": entry_num,
                        "章节号": chapter_num,
                        "章节名": chapter_name,
                        "原文摘录": quote_text
                    }
                    if tags:
                        entry_obj["标记"] = tags
                    
                    current_shentong["原文出处"].append(entry_obj)
                    continue
                
                i += 1
            continue
        
        i += 1
    
    return result


def main():
    script_dir = Path(__file__).parent
    input_file = script_dir / "玄鉴仙族_五德位业体系_原文考据_完整版.md"
    output_file = script_dir / "玄鉴仙族_五德位业体系_原文考据_结构化.json"
    
    print(f"正在解析: {input_file}")
    result = parse_kaoju_md(input_file)
    
    # 统计信息
    total_tixi = len(result["体系列表"])
    total_weizhi = sum(len(t["位置列表"]) for t in result["体系列表"])
    total_shentong = sum(
        len(w["神通列表"]) 
        for t in result["体系列表"] 
        for w in t["位置列表"]
    )
    total_quotes = sum(
        len(s["原文出处"])
        for t in result["体系列表"]
        for w in t["位置列表"]
        for s in w["神通列表"]
    )
    total_daotong_quotes = sum(
        len(w["道统原文出处"])
        for t in result["体系列表"]
        for w in t["位置列表"]
    )
    
    print(f"解析完成:")
    print(f"  - 体系数: {total_tixi}")
    print(f"  - 位置(道统)数: {total_weizhi}")
    print(f"  - 神通/仙基条目数: {total_shentong}")
    print(f"  - 道统原文引用数: {total_daotong_quotes}")
    print(f"  - 神通原文引用数: {total_quotes}")
    print(f"  - 未检得条目数: {len(result['未检得条目'])}")
    
    # 写入 JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n已输出: {output_file}")
    print(f"文件大小: {output_file.stat().st_size / 1024:.1f} KB")


if __name__ == '__main__':
    main()
