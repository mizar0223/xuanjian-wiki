#!/usr/bin/env python3
"""
宽窗上下文提取器 v1
对指定实体，从40个原著txt中提取所有出现位置的上下文宽窗

窗口参数：
  - 前500字 + 实体标记 + 后500字 ≈ 1000-1500字/窗口
  - overlap检测：连续窗口内容重复>80%则合并
  - 按章节序号排序
  - 每个窗口标注章节元数据
"""

import os
import re
import glob
import json

# 配置
NOVEL_DIR = '/Users/leoshi/AIBOOK/Book_download/output/Parts/玄鉴仙族-按章节数-40章'
CONTEXT_BEFORE = 500  # 实体名前取字数
CONTEXT_AFTER = 500   # 实体名后取字数
OVERLAP_THRESHOLD = 0.8  # 合并阈值

def find_all_occurrences(text, entity_name):
    """找到所有【实体名】的位置，返回(start, end)列表"""
    pattern = re.escape(f'【{entity_name}】')
    positions = []
    for m in re.finditer(pattern, text):
        positions.append((m.start(), m.end()))
    return positions

def extract_window(text, pos_start, pos_end, before=CONTEXT_BEFORE, after=CONTEXT_AFTER):
    """提取上下文宽窗"""
    win_start = max(0, pos_start - before)
    win_end = min(len(text), pos_end + after)
    return text[win_start:win_end], win_start, win_end

def parse_chapter_info(filename, text):
    """从文件名和内容提取章节元数据"""
    # 文件名格式: Part_XX.txt 或类似
    base = os.path.basename(filename)
    # 尝试从内容提取章节信息
    chapters = []
    for m in re.finditer(r'第(\d+)章[ 　]*(.*?)(?:\n|$)', text[:2000]):
        ch_num = m.group(1)
        ch_title = m.group(2).strip()[:30]
        chapters.append((int(ch_num), ch_title))
    return chapters

def extract_entity_context(entity_name, novel_files, output_dir):
    """主函数：提取单个实体的全量宽窗上下文"""
    
    all_windows = []
    
    for filepath in sorted(novel_files):
        filename = os.path.basename(filepath)
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
        
        positions = find_all_occurrences(text, entity_name)
        if not positions:
            continue
        
        for pos_start, pos_end in positions:
            window_text, win_start, win_end = extract_window(text, pos_start, pos_end)
            
            # 找到所在章节
            # 从win_start往前搜索最近的"第X章"
            before_text = text[:win_start]
            ch_match = list(re.finditer(r'第(\d+)章[ 　]*([^\n]{0,40})', before_text))
            ch_num = int(ch_match[-1].group(1)) if ch_match else 0
            ch_title = ch_match[-1].group(2).strip() if ch_match else '未知'
            
            all_windows.append({
                'chapter': ch_num,
                'chapter_title': ch_title,
                'file': filename,
                'win_start': win_start,
                'win_end': win_end,
                'text': window_text,
                'entity_pos': pos_start - win_start,  # 实体在窗口内的位置
            })
    
    # 排序
    all_windows.sort(key=lambda w: w['chapter'])
    
    # 合并重叠窗口
    merged = merge_overlapping_windows(all_windows, entity_name)
    
    # 输出文件
    output_path = os.path.join(output_dir, f'{entity_name}_context.txt')
    output_meta = os.path.join(output_dir, f'{entity_name}_meta.json')
    
    # 写入拼接文本
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# 《玄鉴仙族》【{entity_name}】全量上下文\n")
        f.write(f"# 总提及: {len(all_windows)}次 | 合并窗口: {len(merged)}个\n")
        f.write(f"# 窗口参数: 前{CONTEXT_BEFORE}字+后{CONTEXT_AFTER}字\n")
        f.write("=" * 60 + "\n\n")
        
        for i, m in enumerate(merged):
            f.write(f"↕↕↕ 窗口 {i+1}/{len(merged)} | ")
            f.write(f"第{m['chapter']}章《{m['chapter_title']}》")
            # 如果合并了多个原始窗口
            if m.get('merged_from', 1) > 1:
                f.write(f" | 合并{m['merged_from']}个连续引用")
            f.write(f" | 文件:{m['file']} ↕↕↕\n\n")
            f.write(m['text'])
            f.write("\n\n" + "—" * 40 + "\n\n")
        
        # 末尾附简要索引
        f.write("\n\n" + "=" * 60 + "\n")
        f.write(f"# {entity_name} 出现索引\n")
        for w in all_windows:
            f.write(f"# 第{w['chapter']}章《{w['chapter_title']}》({w['file']})\n")
    
    # 写入元数据
    chapter_count = len(set(w['chapter'] for w in all_windows))
    with open(output_meta, 'w', encoding='utf-8') as f:
        json.dump({
            'entity': entity_name,
            'total_occurrences': len(all_windows),
            'merged_windows': len(merged),
            'unique_chapters': chapter_count,
            'total_chars': sum(len(w['text']) for w in all_windows),
            'merged_chars': sum(len(m['text']) for m in merged),
        }, f, ensure_ascii=False, indent=2)
    
    return {
        'occurrences': len(all_windows),
        'merged': len(merged),
        'chapters': chapter_count,
        'chars': sum(len(m['text']) for m in merged),
    }

def merge_overlapping_windows(windows, entity_name):
    """合并内容有大量重叠的连续窗口"""
    if not windows:
        return []
    
    merged = []
    current = dict(windows[0])
    current['merged_from'] = 1
    
    for w in windows[1:]:
        # 检查是否连续（同章节或相邻章节）
        same_or_adjacent = (w['chapter'] - current['chapter']) <= 1
        
        # 检查文本重叠度
        current_set = set(current['text'])
        next_set = set(w['text'])
        if current_set:
            overlap = len(current_set & next_set) / len(current_set)
        else:
            overlap = 0
        
        if same_or_adjacent and overlap > OVERLAP_THRESHOLD:
            # 合并：保留更长的那个
            if len(w['text']) > len(current['text']):
                current['text'] = w['text']
                current['chapter'] = w['chapter']
                current['chapter_title'] = w['chapter_title']
            current['merged_from'] += 1
        else:
            merged.append(current)
            current = dict(w)
            current['merged_from'] = 1
    
    merged.append(current)
    return merged

def main():
    entity_name = '颈下羽'  # POC实体
    output_dir = '/Users/leoshi/AIBOOK/xuanjian/wiki/资料库-法宝:道具:灵资/.workbuddy/wide_window'
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取所有txt文件
    novel_files = sorted(glob.glob(os.path.join(NOVEL_DIR, '*.txt')))
    print(f"📚 原著文件: {len(novel_files)}个")
    
    # 提取上下文
    result = extract_entity_context(entity_name, novel_files, output_dir)
    
    print(f"\n✅ POC完成: 【{entity_name}】")
    print(f"  总提及: {result['occurrences']}次")
    print(f"  合并窗口: {result['merged']}个")
    print(f"  跨章节: {result['chapters']}章")
    print(f"  拼接总字数: {result['chars']:,}字")
    print(f"  输出: {output_dir}/{entity_name}_context.txt")
    print(f"  元数据: {output_dir}/{entity_name}_meta.json")

if __name__ == '__main__':
    main()
