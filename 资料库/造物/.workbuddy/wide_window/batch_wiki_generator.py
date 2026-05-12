#!/usr/bin/env python3
"""批量Wiki生成器 - 简化版"""

import json, os, re, glob

TASK_DIR = '/Users/leoshi/AIBOOK/xuanjian/wiki/资料库-法宝:道具:灵资/.workbuddy/wide_window/agent_tasks'
OUT_BASE = '/Users/leoshi/AIBOOK/xuanjian/wiki/资料库-法宝:道具:灵资/.workbuddy/output_wiki_batch'

def infer_dt(name, ctx):
    # 规则1: 名字自证优先 — 实体名含道统标帜字
    name_signals = [
        ('渌', '渌水'), ('明阳', '明阳'), ('离火', '离火'), ('离', '离火'),
        ('庚金', '庚金'), ('太阳', '太阳'), ('太阴', '太阴'),
        ('并火', '并火'), ('并', '并火'), ('府水', '府水'),
        ('坎水', '坎水'), ('真炁', '真炁'), ('紫炁', '紫炁'),
        ('司天', '司天'), ('剑道', '剑'), ('庚', '庚金'),
    ]
    for signal, dt in name_signals:
        if signal in name:
            return dt
    
    # 规则2: 上下文推断
    ctx_signals = [
        ('明阳','明阳'),('府水','府水'),('离火','离火'),
        ('庚金','庚金'),('坎水','坎水'),('太阴','太阴'),
        ('并火','并火'),('真炁','真炁'),('紫炁','紫炁'),
        ('玉真','玉真'),('霄雷','霄雷'),('渌水','渌水'),
    ]
    for kw, dt in ctx_signals:
        if kw in ctx[:3000]:
            return dt
    return '未知'

def extract_refs(name, ctx):
    refs = []
    for m in re.finditer(r'.{30,300}【' + re.escape(name) + r'】.{30,300}', ctx):
        r = m.group(0).strip()[:280]
        if r not in refs: refs.append(r)
        if len(refs) >= 3: break
    return refs

total = 0
for bid in sorted(os.listdir(TASK_DIR)):
    if not bid.startswith('batch_'): continue
    bid_id = bid.replace('batch_','').replace('.json','')
    
    with open(os.path.join(TASK_DIR, bid)) as f: task = json.load(f)
    out_dir = f'{OUT_BASE}_{bid_id}'
    os.makedirs(out_dir, exist_ok=True)
    
    for e in task['entities']:
        name = e['name']; cat = e['category']; occ = e['occurrences']
        op = os.path.join(out_dir, f'造物-{name}.wiki')
        
        # P1: 文件保护 — 已有深度页面(>3KB)不覆盖
        if os.path.exists(op) and os.path.getsize(op) > 3000:
            continue
        
        ctx = ''
        try:
            with open(e['context_file']) as f: ctx = f.read()
        except:
            fnd = glob.glob(f'/Users/leoshi/AIBOOK/xuanjian/wiki/资料库-法宝:道具:灵资/.workbuddy/wide_window/context/*/{name}/context.txt')
            if fnd:
                with open(fnd[0]) as f: ctx = f.read()
        
        if not ctx: continue
        
        m = re.search(r'第(\d+)章[《]([^》]*)', ctx)
        fc, ft = (m.group(1), f'《{m.group(2)}》') if m else ('?','')
        lm = list(re.finditer(r'窗口 \d+/\d+ \| 第(\d+)章', ctx))
        lc = lm[-1].group(1) if lm else fc
        dt = infer_dt(name, ctx)
        refs = extract_refs(name, ctx)
        
        lines = ['{{导航栏}}', '',
                 f"'''{name}'''是《玄鉴仙族》中的[[{cat}]]。", '',
                 '== 基本信息 ==', '',
                 '{| class="wikitable"', '|-', '! 字段 !! 内容',
                 '|-', f'| 品阶 || [[{cat}]]', '|-', '| 品阶置信度 || 推断',
                 '|-', f'| 道统 || {dt}', '|-', '| 道统置信度 || 推断' if dt!='未知' else '|- | 道统置信度 || 待确认',
                 '|-', f'| 出现次数 || {occ}次',
                 '|-', f'| 首次出现 || 第{fc}章{ft}',
                 '|-', f'| 最新出现 || 第{lc}章', '|}', '',
                 '== 原文引用 ==']
        if refs:
            for r in refs: lines.append(f'→ {r[:250]}')
        else:
            lines.append("''待补充''")
        
        lines += ['', "== 名字由来 ==", "''待考据''", '',
                  "== 功能与威能 ==", "''待考据''", '',
                  "== 所属道统 ==", f"'''道统'''：{dt}", '',
                  f'[[Category:造物]]', f'[[Category:{cat}]]', f'[[Category:道统-{dt}]]']
        
        with open(op, 'w') as f: f.write('\n'.join(lines))
        total += 1

print(f'Generated: {total} pages')
