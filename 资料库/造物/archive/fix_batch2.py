#!/usr/bin/env python3
"""修复Agent-B产出的54个wiki页面常见格式问题"""
import os, re, glob

DIR = '/data/workspace/rq0rlzeg/xuanjian-wiki/资料库/造物/.workbuddy/output_wiki_batch2'
files = sorted(glob.glob(f'{DIR}/*.wiki'))

stats = {'pagename_fix': 0, 'chapter_fix': 0, 'conf_fix': 0}

for fpath in files:
    fname = os.path.basename(fpath)
    entity_name = fname.replace('造物-', '').replace('.wiki', '')
    
    with open(fpath, 'r') as fp:
        content = fp.read()
    original = content
    
    # 1. Fix {{{PAGENAME}}} → entity_name
    if '{{{PAGENAME}}}' in content:
        content = content.replace('{{{PAGENAME}}}', entity_name)
        stats['pagename_fix'] += 1
    
    # 2. Fix 第第XXX章《YYY》章 → 第XXX章《YYY》
    content = re.sub(r'第第(\d+章《[^》]+》)章', r'第\1', content)
    if '第第' not in content and '第第' in original:
        stats['chapter_fix'] += 1
    
    # 3. Fix 置信度格式: || ⚡ → || ⚡推断
    content = re.sub(r'\|\| ⚡\n', r'|| ⚡推断\n', content)
    content = re.sub(r'\|\| ✅\n', r'|| ✅已确认\n', content)
    content = re.sub(r'\|\| ❓\n', r'|| ❓待确认\n', content)
    
    if content != original:
        with open(fpath, 'w') as fp:
            fp.write(content)

print(f"✅ 批次2修复完成:")
print(f"  PAGENAME替换: {stats['pagename_fix']} 文件")
print(f"  章节格式修复: {stats['chapter_fix']} 文件")
