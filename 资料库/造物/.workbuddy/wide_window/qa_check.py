#!/usr/bin/env python3
"""QA核对脚本：检查道统标注是否与实体名中的道统标帜字冲突"""
import os, re, glob

BASE = '/Users/leoshi/AIBOOK/xuanjian/wiki/资料库-法宝:道具:灵资/.workbuddy'
OUT = f'{BASE}/output_wiki_batch'

# 名字标帜字 → 必须属于的道统
NAME_SIGNALS = [
    ('并火', '并火'), ('庚金', '庚金'), ('离火', '离火'),
    ('渌', '渌水'), ('明阳', '明阳'),
    ('太阳', '太阳'), ('太阴', '太阴'),
    ('府水', '府水'), ('坎水', '坎水'),
    ('真炁', '真炁'), ('紫炁', '紫炁'),
    ('庚', '庚金'), ('离', '离火'), ('并', '并火'),
]

red_flags = []

for batch_dir in sorted(glob.glob(f'{OUT}_*')):
    bid = os.path.basename(batch_dir).replace('output_wiki_batch_', '')
    for f in sorted(glob.glob(f'{batch_dir}/*.wiki')):
        name = os.path.basename(f).replace('造物-', '').replace('.wiki', '')
        
        # 读取道统标注
        with open(f) as fp:
            content = fp.read()
        
        m = re.search(r'道统\s*\|\|\s*(.+?)(?:\n|$)', content)
        if not m: continue
        labeled_dt = m.group(1).strip()
        
        # 检查名字标帜
        for signal, expected_dt in NAME_SIGNALS:
            if signal in name and labeled_dt != expected_dt and f'[[{expected_dt}]]' not in labeled_dt and expected_dt not in labeled_dt:
                red_flags.append(f'  🔴 {bid}/{name}: 名含"{signal}"应为{expected_dt}, 实际标注"{labeled_dt}"')
                break

if red_flags:
    print(f'=== QA核对: 发现{len(red_flags)}个道统冲突 ===')
    for flag in red_flags:
        print(flag)
else:
    print('✅ QA核对: 无名字-道统冲突')
