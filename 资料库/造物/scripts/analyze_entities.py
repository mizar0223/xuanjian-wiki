#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os

BASE = "/data/workspace/rq0rlzeg/xuanjian-wiki/资料库/造物"
PAGES_DIR = os.path.join(BASE, "pages")
WORKSTATE_PATH = os.path.join(BASE, ".workbuddy/wide_window/workstate.json")
RANKING_PATH = os.path.join(BASE, ".workbuddy/wide_window/entity_ranking.json")

# 加载数据
with open(WORKSTATE_PATH, 'r', encoding='utf-8') as f:
    ws = json.load(f)
with open(RANKING_PATH, 'r', encoding='utf-8') as f:
    ranking = json.load(f)

registry = ws.get('entity_registry', {})

# 读取pages目录中的所有页面名
existing = set()
for d in sorted(os.listdir(PAGES_DIR)):
    subdir = os.path.join(PAGES_DIR, d)
    if os.path.isdir(subdir):
        files = sorted([f for f in os.listdir(subdir) if f.endswith('.wiki') or f.endswith('.md')])
        for f in files:
            raw = f.replace('.wiki', '').replace('.md', '')
            # 去掉造物-前缀
            name = raw[3:] if raw.startswith('造物-') else raw
            existing.add(name)

# 1. workstate中有但pages中没有
ws_names = set(registry.keys())
missing_in_pages = ws_names - existing
print("=" * 60)
print(" [A] workstate有 但 pages目录缺失的实体")
print("=" * 60)
print(f"  缺失数量: {len(missing_in_pages)}")
if missing_in_pages:
    items = []
    for name in missing_in_pages:
        occ = registry[name].get('meta', {}).get('total_occurrences', 0)
        cat = registry[name].get('category', 'unknown')
        items.append((name, occ, cat))
    items.sort(key=lambda x: x[1], reverse=True)
    for name, occ, cat in items:
        print(f"  - {name} (频次{occ}, {cat})")

# 2. pages中有但workstate中没有
extra_in_pages = existing - ws_names
print()
print("=" * 60)
print(" [B] pages目录有 但 workstate中无记录的实体")
print("=" * 60)
print(f"  额外数量: {len(extra_in_pages)}")
if extra_in_pages:
    for name in sorted(extra_in_pages)[:50]:
        print(f"  - {name}")
    if len(extra_in_pages) > 50:
        print(f"  ... 还有 {len(extra_in_pages)-50} 个")

# 3. 共同拥有的
common = ws_names & existing
print()
print("=" * 60)
print(" [C] workstate和pages共同拥有的实体")
print("=" * 60)
print(f"  共同数量: {len(common)}")

# 4. 按频次统计（基于ranking）
print()
print("=" * 60)
print(" [D] 全部实体按频次分布")
print("=" * 60)
freq_map = {}
for r in ranking:
    occ = r['occurrences']
    freq_map[occ] = freq_map.get(occ, 0) + 1
for k in sorted(freq_map.keys(), reverse=True):
    print(f"  频次 {k:3d}: {freq_map[k]:3d} 个")

# 5. 频次3-4的实体清单
print()
print("=" * 60)
print(" [E] 频次3-4的实体清单（需评估补录）")
print("=" * 60)
freq_34 = [r for r in ranking if r['occurrences'] in [3, 4]]
print(f"  共 {len(freq_34)} 个:")
for i, r in enumerate(freq_34, 1):
    name = r['name']
    in_pages = "✓" if name in existing else "✗"
    in_ws = "✓" if name in ws_names else "✗"
    print(f"  {i:2d}. {name} | 频次:{r['occurrences']} | 字数:{r['chars']} | {r['category']} | pages:{in_pages} ws:{in_ws}")

# 6. 频次1的实体（L6层，机械底版）
print()
print("=" * 60)
print(" [F] 频次1的实体（L6层，仅1次）")
print("=" * 60)
freq_1 = [r for r in ranking if r['occurrences'] == 1]
print(f"  共 {len(freq_1)} 个")

# 7. 推荐优先创建的9个页面
print()
print("=" * 60)
print(" [G] 推荐：优先创建的9个新页面")
print("=" * 60)
# 选择频次在5-9之间且有足够上下文字数的实体
# 首先看看哪些是当前缺失或需要重新创建的
# 实际上所有workstate实体都已经有页面了，那么我们选择"需要补全"的
# 即pages存在但内容可能不完整的低频实体
# 反向思考：推荐9个"最值得升级/完善"的实体

candidates = []
for r in ranking:
    name = r['name']
    if r['occurrences'] >= 5 and r['chars'] >= 2000:
        if name in ws_names:
            info = registry[name]
            meta = info.get('meta', {})
            candidates.append({
                'name': name,
                'occurrences': r['occurrences'],
                'chars': r['chars'],
                'category': r['category'],
                'unique_chapters': meta.get('unique_chapters', 0),
                'first': meta.get('first_chapter', 0),
                'last': meta.get('last_chapter', 0),
            })

# 按综合分数排序：频次 * 字数 / 100
candidates.sort(key=lambda x: x['occurrences'] * x['chars'] / 100, reverse=True)
print(f"  候选池: {len(candidates)} 个实体(频次≥5且字数≥2000)")
print(f"  推荐Top 9:")
for i, c in enumerate(candidates[:9], 1):
    print(f"  {i}. {c['name']} | 频次:{c['occurrences']} | 字数:{c['chars']} | 章数:{c['unique_chapters']} | {c['category']}")
