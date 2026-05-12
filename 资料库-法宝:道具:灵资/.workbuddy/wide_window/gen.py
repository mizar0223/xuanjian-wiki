#!/usr/bin/env python3
"""简版批量生成器 - 直接可用"""
import json, os, re, glob as g

TASK = '/Users/leoshi/AIBOOK/xuanjian/wiki/资料库-法宝:道具:灵资/.workbuddy/wide_window/agent_tasks'
OUT = '/Users/leoshi/AIBOOK/xuanjian/wiki/资料库-法宝:道具:灵资/.workbuddy/output_wiki_batch'

def gen_wiki(name, cat, occ, fc, ft, lc, dao, dc, refs):
    lines = ['{{导航栏}}', '', f"'''{name}'''是《玄鉴仙族》中的[[{cat}]]。", '',
             '== 基本信息 ==', '', '{| class="wikitable"', '|-', '! 字段 !! 内容',
             '|-', f'| 品阶 || [[{cat}]]', '|-', '| 品阶置信度 || 推断',
             '|-', f'| 道统 || {dao}', '|-', f'| 道统置信度 || {dc}',
             '|-', f'| 出现次数 || {occ}次',
             '|-', f'| 首次出现 || 第{fc}章{ft}', '|-', f'| 最新出现 || 第{lc}章', '|}',
             '', '== 原文引用 ==']
    if refs: lines.extend(f'→ {r[:250]}' for r in refs)
    else: lines.append("''待补充''")
    lines.extend(['', f'== 所属道统 ==', f"'''道统'''：{dao} ({dc})", '',
                  f'[[Category:造物]]', f'[[Category:{cat}]]', f'[[Category:道统-{dao}]]'])
    return '\n'.join(lines)

def get_dao(name, ctx):
    rules = [('明阳','明阳'),('府水','府水'),('离火','离火'),('庚金','庚金'),
             ('坎水','坎水'),('太阴','太阴'),('并火','并火'),('真炁','真炁'),
             ('紫炁','紫炁'),('司天','司天'),('玉真','玉真'),('霄雷','霄雷'),
             ('剑道','剑道'),('巽木','巽木'),('艮土','艮土'),('全丹','全丹')]
    for kw, dt in rules:
        if re.search(kw, ctx[:3000]): return dt, '推断'
    return '未知', '待确认'

n = 0
for bid in sorted(os.listdir(TASK)):
    if not bid.endswith('.json'): continue
    with open(f'{TASK}/{bid}') as f: task = json.load(f)
    bname = bid.replace('.json','').replace('batch_','')
    odir = f'{OUT}_{bname}'; os.makedirs(odir, exist_ok=True)
    for e in task['entities']:
        name = e['name']
        op = os.path.join(odir, f'造物-{name}.wiki')
        ctx = ''
        try:
            with open(e['context_file']) as f: ctx = f.read()
        except:
            found = g.glob(f'/Users/leoshi/AIBOOK/xuanjian/wiki/资料库-法宝:道具:灵资/.workbuddy/wide_window/context/*/{name}/context.txt')
            if found: ctx = open(found[0]).read()
        if not ctx: continue
        m = re.search(r'第(\d+)章[《]([^》]*)', ctx)
        fc, ft = (m.group(1), f'《{m.group(2)}》') if m else ('?','')
        lc = fc
        for lm in re.finditer(r'窗口 \d+/\d+ \| 第(\d+)章', ctx): lc = lm.group(1)
        dao, dc = get_dao(name, ctx)
        refs = []
        for rm in re.finditer(r'.{20,300}【'+re.escape(name)+r'】.{20,300}', ctx):
            r = rm.group().strip()[:300]
            if len(r)>30 and r not in refs: refs.append(r)
            if len(refs)>=3: break
        with open(op,'w') as f: f.write(gen_wiki(name, e['category'], e['occurrences'], fc, ft, lc, dao, dc, refs))
        n += 1
print(f'Generated {n} wiki pages')
