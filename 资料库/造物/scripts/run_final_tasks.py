#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双任务最终执行脚本：
1. 提取9个新页面候选（基于频次5-9的高价值实体）
2. 55个低频实体(频次3-4)的上下文密度分析（基于context文件）
"""
import json, os, glob, re
from collections import defaultdict

BASE = "/data/workspace/rq0rlzeg/xuanjian-wiki/资料库/造物"
PAGES_DIR = os.path.join(BASE, "pages")
WS_PATH = os.path.join(BASE, ".workbuddy/wide_window/workstate.json")
RANKING_PATH = os.path.join(BASE, ".workbuddy/wide_window/entity_ranking.json")
CTX_BASE = os.path.join(BASE, ".workbuddy/wide_window/context")

with open(WS_PATH, 'r', encoding='utf-8') as f:
    ws = json.load(f)
with open(RANKING_PATH, 'r', encoding='utf-8') as f:
    ranking = json.load(f)

registry = ws.get('entity_registry', {})
ws_names = set(registry.keys())

# 已有页面
existing = set()
for d in os.listdir(PAGES_DIR):
    subdir = os.path.join(PAGES_DIR, d)
    if os.path.isdir(subdir):
        for f in os.listdir(subdir):
            if f.endswith('.wiki') or f.endswith('.md'):
                name = f.replace('.wiki','').replace('.md','')
                if name.startswith('造物-'):
                    name = name[3:]
                existing.add(name)

print("=" * 70)
print("  任务A: 9个新页面候选")
print("=" * 70)

# 频次5-9的实体（中频，可能需要新页面或页面补全）
freq_5_9 = [r for r in ranking if 5 <= r['occurrences'] <= 9]
freq_5_9.sort(key=lambda x: x['chars'], reverse=True)
print(f"  频次5-9实体: {len(freq_5_9)} 个")
print(f"\n  推荐Top 9个新页面（按字数/综合价值排序）:")
for i, r in enumerate(freq_5_9[:9], 1):
    print(f"  {i}. {r['name']}")
    print(f"     频次:{r['occurrences']} | 字数:{r['chars']} | 类别:{r['category']}")
    meta = registry.get(r['name'], {}).get('meta', {})
    chaps = meta.get('unique_chapters', 0)
    print(f"     跨章密度:{chaps}章 | 首次出现:第{meta.get('first_chapter',0)}章")

print()
print("=" * 70)
print("  任务B: 低频实体(频次3-4)上下文密度分析")
print("=" * 70)

freq_34 = [r for r in ranking if r['occurrences'] in [3, 4]]
print(f"  分析对象: {len(freq_34)} 个实体 (频次3-4)")

# 密度指标
indicators = {
    'high': ['灵气','道统','神通','修炼','法术','法宝','灵宝','炼制','服用','功效'],
    'medium': ['品阶','属性','阴阳','五行','金丹','紫府','筑基','真元','法器','位业','仙基'],
    'low': ['法诀','书页','丹方','符箓','阵法','禁制','灵性','灵纹']
}
all_indicators = sum(indicators.values(), [])

def analyze_context(entity_name):
    """基于context文件分析单实体的上下文密度"""
    # 找到context文件
    ctx_path = None
    for root, dirs, files in os.walk(CTX_BASE):
        for d in dirs:
            if d == entity_name:
                candidate = os.path.join(root, d, 'context.txt')
                if os.path.exists(candidate):
                    ctx_path = candidate
                    break
        if ctx_path:
            break
    
    if not ctx_path:
        return None
    
    with open(ctx_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    char_count = len(content)
    
    # 关键词密度分析
    high_count = sum(content.count(kw) for kw in indicators['high'])
    med_count = sum(content.count(kw) for kw in indicators['medium'])
    low_count = sum(content.count(kw) for kw in indicators['low'])
    
    # 加权密度分数
    weighted_score = high_count * 3 + med_count * 2 + low_count * 1
    
    # 判断是否有"叙事包裹"（周围有完整的句子描述）
    has_description = any(punc in content for punc in ['是', '为', '有', '能', '可'])
    
    return {
        'char_count': char_count,
        'high_kw': high_count,
        'med_kw': med_count,
        'low_kw': low_count,
        'weighted_score': weighted_score,
        'has_description': has_description,
        'density_tier': 'high' if weighted_score >= 15 else ('medium' if weighted_score >= 8 else 'low')
    }

results = []
for r in freq_34:
    name = r['name']
    ctx_info = analyze_context(name)
    results.append({
        'name': name,
        'occurrences': r['occurrences'],
        'chars': r['chars'],
        'category': r['category'],
        'context_analysis': ctx_info,
    })

# 按加权分数排序
results.sort(key=lambda x: x['context_analysis']['weighted_score'] if x['context_analysis'] else 0, reverse=True)

print(f"\n  === 高密度支点候选 (Top 20, 加权分≥15) ===")
high_density = [r for r in results if r['context_analysis'] and r['context_analysis']['density_tier'] == 'high']
for i, r in enumerate(results[:20], 1):
    ctx = r['context_analysis']
    if ctx:
        rec = "【补录】" if ctx['density_tier'] == 'high' else ("【酌情】" if ctx['density_tier'] == 'medium' else "")
        print(f"  {i:2d}. {r['name']} | 加权分:{ctx['weighted_score']:2d}(高{ctx['high_kw']}中{ctx['med_kw']}低{ctx['low_kw']}) | 上下文{ctx['char_count']}字 | {r['category']} {rec}")
    else:
        print(f"  {i:2d}. {r['name']} | 无上下文文件 | {r['category']}")

# 统计分布
high = sum(1 for r in results if r['context_analysis'] and r['context_analysis']['density_tier'] == 'high')
medium = sum(1 for r in results if r['context_analysis'] and r['context_analysis']['density_tier'] == 'medium')
low = sum(1 for r in results if r['context_analysis'] and r['context_analysis']['density_tier'] == 'low')
no_ctx = sum(1 for r in results if not r['context_analysis'])

print(f"\n  === 密度分布统计 ===")
print(f"  高密度(加权≥15): {high} 个 → 强烈建议补录")
print(f"  中密度(加权8-14): {medium} 个 → 酌情补录")
print(f"  低密度(加权<8): {low} 个 → 延后/机械底版")
print(f"  无上下文文件: {no_ctx} 个")

# 保存完整报告
report = {
    'task_a_new_pages': [{'name':r['name'],'occurrences':r['occurrences'],'chars':r['chars'],'category':r['category']} for r in freq_5_9[:9]],
    'task_b_density_analysis': results,
    'density_summary': {'high': high, 'medium': medium, 'low': low, 'no_context': no_ctx}
}
report_path = os.path.join(BASE, '.workbuddy/tasks_analysis_report.json')
with open(report_path, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(f"\n  完整报告已保存: {report_path}")
