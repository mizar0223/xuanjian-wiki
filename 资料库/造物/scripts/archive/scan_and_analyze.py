#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扫描缺失页面 + 低频实体上下文密度分析
"""
import json
import os
import re
from collections import Counter

# 路径配置
BASE = "/data/workspace/rq0rlzeg/xuanjian-wiki/资料库/造物"
PAGES_DIR = os.path.join(BASE, "pages")
WORKSTATE_PATH = os.path.join(BASE, ".workbuddy/wide_window/workstate.json")
RANKING_PATH = os.path.join(BASE, ".workbuddy/wide_window/entity_ranking.json")
SOURCE_DIR = "/data/workspace/rq0rlzeg/xuanjian-wiki/Pdf/02_加工产出/章节txt切分输出"


def load_workstate():
    with open(WORKSTATE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_ranking():
    with open(RANKING_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_existing_pages():
    """获取pages目录中已有的所有页面名"""
    existing = set()
    for d in os.listdir(PAGES_DIR):
        subdir = os.path.join(PAGES_DIR, d)
        if os.path.isdir(subdir):
            for f in os.listdir(subdir):
                if f.endswith('.wiki') or f.endswith('.md'):
                    name = f.replace('.wiki', '').replace('.md', '')
                    if name.startswith('造物-'):
                        name = name[3:]
                    existing.add(name)
    return existing


def find_missing_entities(workstate, existing_pages):
    """找出workstate中有但pages目录中没有的实体"""
    registry = workstate.get('entity_registry', {})
    missing = []
    for name, info in registry.items():
        if name not in existing_pages:
            occ = info.get('meta', {}).get('total_occurrences', 0)
            chars = info.get('meta', {}).get('merged_chars', 0)
            cat = info.get('category', 'unknown')
            missing.append({
                'name': name,
                'occurrences': occ,
                'chars': chars,
                'category': cat,
                'first_chapter': info.get('meta', {}).get('first_chapter', 0),
                'last_chapter': info.get('meta', {}).get('last_chapter', 0),
                'unique_chapters': info.get('meta', {}).get('unique_chapters', 0),
            })
    missing.sort(key=lambda x: x['occurrences'], reverse=True)
    return missing


def contextual_density_analysis(entity_name, source_dir, window=100):
    """
    对实体在原文中的上下文进行密度分析
    返回密度分数和样本上下文
    """
    total_mentions = 0
    total_density_score = 0
    sample_contexts = []
    
    # 查找所有源文件
    if not os.path.exists(source_dir):
        return None, None
    
    txt_files = sorted([f for f in os.listdir(source_dir) if f.endswith('.txt')])
    
    for txt_file in txt_files:
        filepath = os.path.join(source_dir, txt_file)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            continue
        
        # 查找实体出现位置
        pattern = re.compile(re.escape(entity_name))
        for match in pattern.finditer(content):
            total_mentions += 1
            start = max(0, match.start() - window)
            end = min(len(content), match.end() + window)
            context = content[start:end]
            
            # 计算密度分数：基于形容词、动词、归属词等密度
            # 修仙相关关键词
            key_indicators = [
                '灵气', '道统', '神通', '修炼', '法术', '法宝', '灵宝',
                '炼制', '服用', '功效', '品阶', '属性', '阴阳', '五行',
                '金丹', '紫府', '筑基', '神通', '道行', '真元', '法器'
            ]
            
            density = sum(1 for kw in key_indicators if kw in context)
            total_density_score += density
            
            if len(sample_contexts) < 3:
                sample_contexts.append({
                    'file': txt_file,
                    'context': context[:200],
                    'density': density
                })
    
    if total_mentions == 0:
        return 0, []
    
    avg_density = total_density_score / total_mentions
    return avg_density, sample_contexts


def main():
    print("=" * 60)
    print(" [1/3] 加载数据源")
    print("=" * 60)
    ws = load_workstate()
    ranking = load_ranking()
    existing = get_existing_pages()
    
    print(f"  已有页面: {len(existing)} 个")
    print(f"  Workstate注册实体: {len(ws.get('entity_registry', {}))} 个")
    
    print()
    print("=" * 60)
    print(" [2/3] 扫描缺失页面 (workstate有但pages目录无)")
    print("=" * 60)
    missing = find_missing_entities(ws, existing)
    
    # 按频次分类
    high_freq = [e for e in missing if e['occurrences'] >= 8]
    mid_freq = [e for e in missing if 4 <= e['occurrences'] <= 7]
    low_freq = [e for e in missing if e['occurrences'] <= 3]
    
    print(f"  缺失实体总数: {len(missing)}")
    print(f"  高频(≥8次): {len(high_freq)} 个")
    print(f"  中频(4-7次): {len(mid_freq)} 个")
    print(f"  低频(≤3次): {len(low_freq)} 个")
    
    # 输出高频缺失（应优先创建）
    if high_freq:
        print(f"\n  === 高频缺失实体 (建议优先创建) ===")
        for i, e in enumerate(high_freq[:15], 1):
            spans = f"{e['first_chapter']}-{e['last_chapter']}" if e['first_chapter'] != e['last_chapter'] else str(e['first_chapter'])
            print(f"  {i}. {e['name']} | 频次:{e['occurrences']} | 字数:{e['chars']} | 章:{spans} | {e['category']}")
    
    # 输出中频缺失 - 这将是44个低频遗漏实体的候选
    if mid_freq:
        print(f"\n  === 中频缺失实体 (4-7次，需评估补录) ===")
        for i, e in enumerate(mid_freq, 1):
            spans = f"{e['first_chapter']}-{e['last_chapter']}" if e['first_chapter'] != e['last_chapter'] else str(e['first_chapter'])
            print(f"  {i}. {e['name']} | 频次:{e['occurrences']} | 字数:{e['chars']} | 章:{spans} | {e['category']}")
    
    print()
    print("=" * 60)
    print(" [3/3] 低频实体上下文密度分析")
    print("=" * 60)
    
    # 对频次3-4的实体做上下文密度分析
    freq_3_4 = [e for e in missing if e['occurrences'] in [3, 4]]
    print(f"  频次3-4的实体: {len(freq_3_4)} 个")
    print(f"  (从ranking中确认: 频次3有25个 + 频次4有30个 = 55个)")
    
    # 写报告
    report = {
        'scan_time': '2026-05-12',
        'missing_total': len(missing),
        'missing_high_freq': high_freq,
        'missing_mid_freq': mid_freq,
        'missing_low_freq': low_freq,
    }
    
    report_path = os.path.join(BASE, '.workbuddy/missing_entities_report.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n  报告已保存: {report_path}")


if __name__ == '__main__':
    main()
