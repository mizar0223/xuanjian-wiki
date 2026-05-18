#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双任务执行脚本：
1. 提取9个新页面候选
2. 44个低频实体上下文密度分析
"""
import json, os, glob, re
from collections import Counter, defaultdict

BASE = "/data/workspace/rq0rlzeg/xuanjian-wiki/资料库/造物"
PAGES_DIR = os.path.join(BASE, "pages")
WS_PATH = os.path.join(BASE, ".workbuddy/wide_window/workstate.json")
RANKING_PATH = os.path.join(BASE, ".workbuddy/wide_window/entity_ranking.json")

# 可能的源文本目录
SRC_CANDIDATES = [
    "/data/workspace/rq0rlzeg/xuanjian-wiki/Pdf/02_加工产出/章节txt切分输出-chunk-normal-avg-5000-keepEolTrue",
    "/data/workspace/rq0rlzeg/xuanjian-wiki/Pdf/02_加工产出/章节txt切分输出",
]

def find_src_dir():
    for d in SRC_CANDIDATES:
        if os.path.exists(d):
            return d
    pdf_dir = "/data/workspace/rq0rlzeg/xuanjian-wiki/Pdf"
    if os.path.exists(pdf_dir):
        for root, dirs, files in os.walk(pdf_dir):
            if any(f.endswith('.txt') for f in files):
                return root
    return None

# 加载数据
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

print("=" * 60)
print("  任务A: 找出'新页面'候选")
print("=" * 60)

# 已上传但可能需要补录的9个新页面
# 方法1: workstate中未上传到pages目录高频优先
missing = ws_names - existing
missing_entities = []
for name in missing:
    meta = registry[name].get('meta', {})
    missing_entities.append({
        'name': name,
        'occurrences': meta.get('total_occurrences', 0),
        'chars': meta.get('merged_chars', 0),
        'category': registry[name].get('category', 'unknown'),
        'first': meta.get('first_chapter', 0),
        'last': meta.get('last_chapter', 0),
    })
missing_entities.sort(key=lambda x: x['occurrences'], reverse=True)

print(f"  workstate有但pages目录缺失: {len(missing_entities)} 个")
if missing_entities:
    print(f"\n  Top 10 缺失实体:")
    for i, e in enumerate(missing_entities[:10], 1):
        print(f"  {i}. {e['name']} | 频次:{e['occurrences']} | 字数:{e['chars']} | {e['category']}")

# 方法2: ranking中频次>=10, 且已有页面的
high_value = [r for r in ranking if r['occurrences'] >= 10 and r['name'] in ws_names]
high_value.sort(key=lambda x: x['chars'], reverse=True)
print(f"\n  高频高价值实体(≥10次&在ws中): {len(high_value)} 个")

# 考虑到workstate中所有实体都已有pages文件，"9个新页面"可能指的是新维度/新分类的页面
# 比如体系页面、人物页面、法诀书页等
extra_pages = existing - ws_names
print(f"\n  Pages中有但workstate无记录: {len(extra_pages)} 个")
print(f"  这可能是人物维度、体系维度等附加页面")

# 提取频次为5-9的实体作为"新页面"候选
new_page_candidates = [r for r in ranking if r['occurrences'] in range(5, 10)]
print(f"\n  频次5-9实体共: {len(new_page_candidates)} 个")
print(f"  从中选Top 9作为'新页面'候选:")
for i, r in enumerate(sorted(new_page_candidates, key=lambda x: x['chars'], reverse=True)[:9], 1):
    print(f"  {i}. {r['name']} | 频次:{r['occurrences']} | 字数:{r['chars']} | {r['category']}")

print()
print("=" * 60)
print("  任务B: 低频实体(频次3-4)上下文密度分析")
print("=" * 60)

freq_34 = [r for r in ranking if r['occurrences'] in [3, 4]]
print(f"  频次3-4实体总数: {len(freq_34)} 个")

# 如果存在源文本，做密度分析
src_dir = find_src_dir()
if src_dir:
    print(f"  源文本目录: {src_dir}")
    # 合并所有源文本
    all_text = []
    txt_files = glob.glob(os.path.join(src_dir, "*.txt"))
    for fp in sorted(txt_files)[:30]:
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                all_text.append(f.read())
        except:
            pass
    full_text = '\n'.join(all_text)
    print(f"  加载文本: {len(full_text)} 字符")
    
    indicators = ['灵气','道统','神通','修炼','法术','法宝','灵宝','炼制','服用','功效','品阶','属性','阴阳','五行','金丹','紫府','筑基','真元','法器','位业','仙基','法诀','书页','丹方']
    
    density_results = []
    for r in freq_34:
        name = r['name']
        mentions = 0
        total_density = 0
        for m in re.finditer(re.escape(name), full_text):
            mentions += 1
            start = max(0, m.start() - 150)
            end = min(len(full_text), m.end() + 150)
            ctx = full_text[start:end]
            den = sum(1 for kw in indicators if kw in ctx)
            total_density += den
        
        avg_density = total_density / mentions if mentions > 0 else 0
        density_results.append({
            'name': name,
            'occurrences': r['occurrences'],
            'chars': r['chars'],
            'category': r['category'],
            'density': round(avg_density, 2),
            'mention_count': mentions,
        })
    
    # 按密度排序
    density_results.sort(key=lambda x: x['density'], reverse=True)
    print(f"\n  === 高密度支点候选 (Top 20) ===")
    for i, d in enumerate(density_results[:20], 1):
        rec = "★推荐补录" if d['density'] >= 2.0 else ""
        print(f"  {i:2d}. {d['name']} | 密度:{d['density']} | 频次:{d['occurrences']} | {d['category']} {rec}")
    
    # 高密度 vs 低密度
    high_density = [d for d in density_results if d['density'] >= 2.0]
    low_density = [d for d in density_results if d['density'] < 1.0]
    print(f"\n  高密度(≥2.0): {len(high_density)} 个 → 建议补录")
    print(f"  中密度(1.0-2.0): {len(density_results)-len(high_density)-len(low_density)} 个 → 酌情")
    print(f"  低密度(<1.0): {len(low_density)} 个 → 延后或放弃")
    
    # 输出高密度候选名单
    print(f"\n  === 高密度支点候选名单 (44个中的重点) ===")
    for i, d in enumerate(high_density, 1):
        print(f"  {i}. {d['name']} (密度{d['density']}, {d['occurrences']}次, {d['category']})")
    
    # 保存报告
    report = {
        'new_page_candidates': [{'name':r['name'],'occurrences':r['occurrences'],'chars':r['chars'],'category':r['category']} for r in sorted(new_page_candidates, key=lambda x:x['chars'], reverse=True)[:9]],
        'high_density_entities': high_density,
        'low_density_entities': low_density,
        'all_density': density_results,
    }
    report_path = os.path.join(BASE, '.workbuddy/density_report.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n  报告已保存: {report_path}")
else:
    print("  未找到源文本目录")
