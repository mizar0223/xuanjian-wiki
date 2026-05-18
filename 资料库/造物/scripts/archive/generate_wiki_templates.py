#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成9个新页面 + 47个高密度低频实体的wiki底版
"""
import json, os, re

BASE = "/data/workspace/rq0rlzeg/xuanjian-wiki/资料库/造物"
WS_PATH = os.path.join(BASE, ".workbuddy/wide_window/workstate.json")
RANKING_PATH = os.path.join(BASE, ".workbuddy/wide_window/entity_ranking.json")
CTX_BASE = os.path.join(BASE, ".workbuddy/wide_window/context")
NEW_PAGES_DIR = os.path.join(BASE, "pages/_new_pages")

def safe_dir(name):
    return re.sub(r'[<>:"/\\|?*]', '_', name)

def generate_wiki_template(entity_name, ranking_info, meta_info, context_text):
    """生成标准wiki底版模板"""
    cat = ranking_info.get('category', '待分类')
    occ = ranking_info.get('occurrences', 0)
    chars = ranking_info.get('chars', 0)
    first_ch = meta_info.get('first_chapter', 0)
    last_ch = meta_info.get('last_chapter', 0)
    unique_ch = meta_info.get('unique_chapters', 0)
    
    # 提取上下文中的关键句（前5行作为描述）
    desc_lines = []
    for line in context_text.split('\n')[:10]:
        line = line.strip()
        if line and len(line) > 10 and entity_name in line:
            desc_lines.append(line)
        if len(desc_lines) >= 3:
            break
    
    description = desc_lines[0] if desc_lines else "待补充描述"
    
    # 生成wiki模板
    lines = [
        "{{导航栏}}",
        "",
        f"'''{entity_name}'''是《玄鉴仙族》中的{cat}。",
        "",
        f"{description}",
        "",
        "== 基本信息 ==",
        "",
        '{| class="wikitable"',
        "|-",
        "! 字段 !! 内容",
        "|-",
        f"| 类别 || {cat}",
        "|-",
        f"| 出现频次 || {occ} 次",
        "|-",
        f"| 首次出现 || 第{first_ch}章",
        "|-",
        f"| 末次出现 || 第{last_ch}章",
        "|-",
        f"| 跨章分布 || {unique_ch} 章",
        "|-",
        f"| 上下文总长 || {chars} 字",
        "|}",
        "",
        "== 描述 ==",
        "",
    ]
    
    # 添加上下文关键片段
    for line in desc_lines[1:]:
        lines.append(line)
        lines.append("")
    
    # 添加完整上下文（折叠）
    lines.append("== 原文上下文 ==")
    lines.append("")
    lines.append('<div class="mw-collapsible mw-collapsed">')
    lines.append('<div class="mw-collapsible-toggle" style="background:#f0f0f0;padding:4px;border:1px solid #ccc;cursor:pointer;font-weight:bold;">▼ 展开完整上下文</div>')
    lines.append('<div class="mw-collapsible-content" style="padding:8px;border:1px solid #ccc;border-top:none;">')
    lines.append("<pre>")
    # 截断过长的上下文
    ctx_display = context_text[:5000] + "..." if len(context_text) > 5000 else context_text
    lines.append(ctx_display)
    lines.append("</pre>")
    lines.append("</div>")
    lines.append("</div>")
    lines.append("")
    
    # 添加分类
    lines.append("== 相关页面 ==")
    lines.append("")
    lines.append(f"* [[造物-{entity_name}]]")
    lines.append("* [[玄鉴仙族·造物百科]]")
    lines.append("")
    lines.append(f"[[Category:{cat}]]")
    lines.append("[[Category:玄鉴仙族]]")
    lines.append("")
    
    return '\n'.join(lines)

# 加载数据
with open(WS_PATH, 'r', encoding='utf-8') as f:
    ws = json.load(f)
with open(RANKING_PATH, 'r', encoding='utf-8') as f:
    ranking = json.load(f)

registry = ws.get('entity_registry', {})

# 1. 9个新页面候选 (频次5-9)
freq_5_9 = [r for r in ranking if 5 <= r['occurrences'] <= 9]
freq_5_9.sort(key=lambda x: x['chars'], reverse=True)
new_page_candidates = freq_5_9[:9]

# 2. 高密度低频实体 (从report读取)
report_path = os.path.join(BASE, '.workbuddy/tasks_analysis_report.json')
with open(report_path, 'r', encoding='utf-8') as f:
    report = json.load(f)

high_density = [r for r in report['task_b_density_analysis'] 
                if r['context_analysis'] and r['context_analysis']['density_tier'] == 'high']

print("=" * 60)
print("  生成9个新页面 + 47个高密度实体wiki底版")
print("=" * 60)

os.makedirs(NEW_PAGES_DIR, exist_ok=True)

# 生成9个新页面
generated = 0
for r in new_page_candidates:
    name = r['name']
    meta = registry.get(name, {}).get('meta', {})
    
    # 读取上下文
    ctx_path = None
    for root, dirs, files in os.walk(CTX_BASE):
        for d in dirs:
            if d == name:
                cp = os.path.join(root, d, 'context.txt')
                if os.path.exists(cp):
                    ctx_path = cp
                    break
        if ctx_path:
            break
    
    ctx_text = ""
    if ctx_path:
        with open(ctx_path, 'r', encoding='utf-8') as f:
            ctx_text = f.read()
    
    wiki_content = generate_wiki_template(name, r, meta, ctx_text)
    out_path = os.path.join(NEW_PAGES_DIR, f"造物-{safe_dir(name)}.wiki")
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(wiki_content)
    generated += 1
    print(f"  [新页] {name} -> {out_path}")

# 生成高密度低频实体底版
for r in high_density:
    name = r['name']
    meta = registry.get(name, {}).get('meta', {})
    
    # 读取上下文
    ctx_path = None
    for root, dirs, files in os.walk(CTX_BASE):
        for d in dirs:
            if d == name:
                cp = os.path.join(root, d, 'context.txt')
                if os.path.exists(cp):
                    ctx_path = cp
                    break
        if ctx_path:
            break
    
    ctx_text = ""
    if ctx_path:
        with open(ctx_path, 'r', encoding='utf-8') as f:
            ctx_text = f.read()
    
    wiki_content = generate_wiki_template(name, r, meta, ctx_text)
    out_path = os.path.join(NEW_PAGES_DIR, f"造物-{safe_dir(name)}.wiki")
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(wiki_content)
    generated += 1
    print(f"  [补录] {name} -> {out_path}")

print(f"\n  共生成 {generated} 个wiki底版文件")
print(f"  输出目录: {NEW_PAGES_DIR}")