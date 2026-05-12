#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上下文密度分析 + 新页面提取脚本
"""
import json, os, re
from collections import Counter

BASE = "/data/workspace/rq0rlzeg/xuanjian-wiki/资料库/造物"
PAGES_DIR = os.path.join(BASE, "pages")
WS_PATH = os.path.join(BASE, ".workbuddy/wide_window/workstate.json")
RANKING_PATH = os.path.join(BASE, ".workbuddy/wide_window/entity_ranking.json")
SRC_DIR = "/data/workspace/rq0rlzeg/xuanjian-wiki/Pdf/02_加工产出/章节txt切分输出-chunk-normal-avg-5000-keepEolTrue"

with open(WS_PATH, 'r') as f:
    ws = json.load(f)
with open(RANKING_PATH, 'r') as f:
    ranking = json.load(f)

registry = ws.get('entity_registry', {})

# Pages目录中已有的
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

# 1. 找出workstate有但pages目录无的
ws_names = set(registry.keys())
missing = ws_names - existing
print(f"=== 缺失实体: {len(missing)} ===")
for name in sorted(missing)[:20]:
    meta = registry[name].get('meta', {})
    print(f"  {name}: {meta.get('total_occurrences',0)}x, {meta.get('merged_chars',0)} chars")

# 2. 频次3-4的
freq_34 = [r for r in ranking if r['occurrences'] in [3,4]]
print(f"\n=== 频次3-4实体: {len(freq_34)} ===")
for r in freq_34[:10]:
    status = "已有" if r['name'] in existing else "缺失"
    print(f"  {r['name']}: {r['occurrences']}x, {r['chars']} chars, {r['category']} [{status}]")

# 3. 上下文密度分析
def density_analysis(entity_name, src_dir, window=150):
    if not os.path.exists(src_dir):
        return None
    indicators = ['灵气','道统','神通','修炼','法术','法宝','灵宝','炼制','服用','功效','品阶','属性','阴阳','五行','金丹','紫府','筑基','真元','法器','位业','仙基']
    txt = []
    for f in sorted(os.listdir(src_dir)):
        if f.endswith('.txt'):
            path = os.path.join(src_dir, f)
            try:
                with open(path, 'r', encoding='utf-8') as fh:
                    txt.append(fh.read())
            except:
                pass
    full = '\n'.join(txt)
    
    mentions = 0
    total_density = 0
    for m in re.finditer(re.escape(entity_name), full):
        mentions += 1
        start = max(0, m.start() - window)
        end = min(len(full), m.end() + window)
        ctx = full[start:end]
        den = sum(1 for kw in indicators if kw in ctx)
        total_density += den
    
    if mentions == 0:
        return 0, 0
    return total_density / mentions, mentions

print(f"\n=== 上下文密度分析 (频次3-4) ===")
results = []
for r in freq_34[:20]:
    name = r['name']
    d, m = density_analysis(name, SRC_DIR)
    results.append((name, r['occurrences'], r['chars'], r['category'], d, m))
    print(f"  {name}: 密度={d:.1f} 提及={m} 频次={r['occurrences']}x")
