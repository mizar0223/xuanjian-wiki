#!/usr/bin/env python3
"""批量生成批次2的54个实体的Wiki页面"""

import re
import os

OUTPUT_DIR = '/data/workspace/rq0rlzeg/xuanjian-wiki/资料库/造物/.workbuddy/output_wiki_batch2'

def classify(name, func_lines):
    """根据名字关键词分类品阶和道统"""
    pj, pj_c = '未知', '❓'
    dt, dt_c = '未知', '❓'
    type_key = '法器'

    # === 品阶判定 ===
    # 灵水/灵资类
    if any(k in name for k in ['灵水','元水','泉水','寒铁','赤金','离金']):
        pj, pj_c = '灵资', '⚡'
    elif any(k in name for k in ['寒铁','玄铁','岁金','铂金']):
        pj, pj_c = '材料', '⚡'
    elif any(k in name for k in ['宝袋','宝鼎','宝心玉']):
        pj, pj_c = '灵器', '⚡'
    elif any(k in name for k in ['剑']):
        pj, pj_c = '筑基法器', '⚡'
        type_key = '剑器'
    elif any(k in name for k in ['刀','枪']):
        pj, pj_c = '法器', '⚡'
    elif any(k in name for k in ['扇','令','旗']):
        pj, pj_c = '法器', '⚡'
    elif any(k in name for k in ['石','玉']):
        pj, pj_c = '灵资', '⚡'
        type_key = '灵资'
    elif any(k in name for k in ['珠','印','炉','灯']):
        pj, pj_c = '灵器', '⚡'
    elif any(k in name for k in ['书','图','卷']):
        pj, pj_c = '典籍', '⚡'
    # 水
    if any(k in name for k in ['水','泉','牝']):
        pj, pj_c = '灵资', '⚡'
    # 火
    if any(k in name for k in ['火']):
        if '无明' in name or '无擘' in name:
            pj, pj_c = '灵物', '⚡'
        else:
            pj, pj_c = '灵资', '⚡'

    # 特殊
    if name == '天灯':
        pj, pj_c = '特殊', '⚡'
    if name == '江中炉':
        pj, pj_c = '灵器', '⚡'
    if name == '太阳衍光宝袋':
        pj, pj_c = '灵宝', '✅'
    if name == '坎金围连环':
        pj, pj_c = '上品灵器', '✅'
    if name == '命阳白玉剑':
        pj, pj_c = '仙剑/灵宝', '⚡'
    if name == '袤土宝心玉':
        pj, pj_c = '灵器', '⚡'
    if name == '道勖阴魄玄刃':
        pj, pj_c = '灵器', '⚡'
    if name == '上善明玄玉':
        pj, pj_c = '灵资', '✅'

    # === 道统判定 ===
    # 从原文上下文确认（已读到的数据）
    confirmed_map = {
        '天星赤金': ('离火', '✅'),
        '太阳衍光宝袋': ('太阳', '✅'),
        '坎金围连环': ('坎水', '✅'),
        '虺元灵水': ('府水', '✅'),
        '清元灵水': ('坎水', '✅'),
        '洞鹭元水': ('府水', '✅'),
        '归谿牝水': ('牝水', '✅'),
        '沉犷岁金': ('合水', '✅'),
        '月阙剑': ('剑道', '⚡'),
        '命阳白玉剑': ('玉真', '⚡'),
        '道煞玄名剑': ('剑道', '⚡'),
    }
    if name in confirmed_map:
        dt, dt_c = confirmed_map[name]
    else:
        # 机械推断
        if any(k in name for k in ['离火','雉','焚','燠','炎','焃','赤','火','阳衍']):
            dt, dt_c = '离火', '⚡'
        elif any(k in name for k in ['水','泉','牝','虺','鹭','渌']):
            dt, dt_c = '府水', '⚡'
        elif any(k in name for k in ['金','铁','铜']):
            dt, dt_c = '庚金', '⚡'
        elif any(k in name for k in ['石','玉']):
            dt, dt_c = '艮土', '⚡'
        elif any(k in name for k in ['木','桑','参木']):
            dt, dt_c = '巽木', '⚡'
        elif any(k in name for k in ['剑']) and '月阙' in name:
            dt, dt_c = '剑道', '⚡'
        elif '命阳' in name or '白玉剑' in name:
            dt, dt_c = '玉真', '⚡'

    # 功能标签
    tags = []
    if any(k in name for k in ['火','水','金','铁','铜','石','玉','木']):
        tags.append('炼丹材料')
    if any(k in name for k in ['剑','刀','枪','刃','弓']):
        tags.append('攻击')
    if any(k in name for k in ['袋','炉']):
        tags.append('储物')
    if any(k in name for k in ['灯']):
        tags.append('探查')
    if any(k in name for k in ['扇','旗']):
        tags.append('防御')

    return pj, pj_c, dt, dt_c, '、'.join(tags) if tags else '特殊'

def parse_entities(content):
    """解析markdown中的实体块"""
    entities = {}
    # 按 #### 分割
    blocks = re.split(r'\n(?=#### )', content)
    for block in blocks:
        m = re.match(r'#### (.+)\n', block)
        if not m:
            continue
        name = m.group(1).strip()
        data = {'name': name, 'raw': block}

        # 频次
        fm = re.search(r'\*\*出现频次\*\*[：:]\s*(\d+)\s*次', block)
        data['freq'] = fm.group(1) if fm else '?'

        # 首次出现
        fm = re.search(r'\*\*首次出现\*\*[：:]\s*(.+?)$', block, re.M)
        data['first'] = fm.group(1).strip() if fm else '?'

        # 功能描述
        func = extract_section(block, '功能描述')
        data['functions'] = func[:5] if func else []

        # 外形描述
        exts = extract_section(block, '外形描述')
        data['appearance'] = exts[:3] if exts else []

        # 来源描述
        src = extract_section(block, '来源描述')
        data['source'] = src[:2] if src else []

        # 使用历史
        hist = extract_usage_history(block)
        data['history'] = hist[:4] if hist else []

        entities[name] = data
    return entities

def extract_section(text, section):
    """提取section内容"""
    pattern = rf'\*\*{section}\*\*[：:]\s*\n((?:> .*\n?)+)'
    m = re.search(pattern, text)
    if m:
        lines = []
        for l in m.group(1).strip().split('\n'):
            l = l.strip()
            if l.startswith('> '):
                l = l[2:]
            elif l.startswith('>'):
                l = l[1:]
            lines.append(l.strip())
        return lines
    return []

def extract_usage_history(text):
    """提取使用历史"""
    pattern = r'\*\*使用历史\*\*[：:]\s*\n((?:> .*\n?)+)'
    m = re.search(pattern, text)
    if m:
        entries = []
        lines = m.group(1).strip().split('\n')
        current = []
        for l in lines:
            l = l.strip()
            if l.startswith('> **'):
                if current:
                    entries.append(' '.join(current))
                current = [l[2:].strip() if l.startswith('> ') else l[1:].strip()]
            elif l.startswith('> '):
                current.append(l[2:].strip())
        if current:
            entries.append(' '.join(current))
        return entries
    return []

def clean_line(s):
    """清理文本"""
    s = re.sub(r'[【】\[\]]', '', s)
    s = re.sub(r'\*\*', '', s)
    s = s.replace('|', '/')
    s = s.strip()
    return s

def generate_wiki(entity, pj, pj_c, dt, dt_c, tags):
    """生成单个wiki页面"""
    name = entity['name']
    func_lines = entity.get('functions', [])
    appear_lines = entity.get('appearance', [])
    src_lines = entity.get('source', [])
    hist_lines = entity.get('history', [])

    # 功能描述
    func_text = '\n'.join([f'* {clean_line(l)[:200]}' for l in func_lines]) if func_lines else '待考据'

    # 外观描述
    appear_text = '\n'.join([f'* {clean_line(l)[:200]}' for l in appear_lines]) if appear_lines else '原文未详述'

    # 使用事件
    hist_text = '\n'.join([f'# {clean_line(l)[:300]}' for l in hist_lines]) if hist_lines else '待补充'

    # 原文引用
    quote_lines = (hist_lines[:2] if hist_lines else []) + (src_lines[:1] if src_lines else [])
    quote_text = '\n'.join([f'> {clean_line(l)[:250]}' for l in quote_lines]) if quote_lines else '待补充'

    # 持有者提取
    holders = []
    for l in func_lines + hist_lines:
        for n in ['李曦明','李周巍','李曦峻','李渊蛟','李玄宣','李清虹','李承辽','定阳子','孔婷云','廖落']:
            if n in l and n not in holders:
                holders.append(n)
    holder_text = '、'.join(holders[:5]) if holders else '待考据'

    first_ch = entity.get('first', '?').strip()
    # 清理"第第958章《笑与泪》章" → "第958章《笑与泪》"
    first_ch = first_ch.replace('第第', '第').rstrip('章').strip()
    if first_ch and not first_ch.startswith('第'):
        first_ch = '第' + first_ch
    freq = entity.get('freq', '?')

    # MediaWiki 特有的 {{ }} 和 {{{ }}} 语法，用简单的字符串拼接避免花括号转义混乱
    DBL = '{{'  # MediaWiki 双花括号
    DBL3 = '{{{'  # MediaWiki 三花括号

    wiki = DBL + '导航栏}}\n\n'
    wiki += "'''" + DBL3 + "PAGENAME}}}'''是《玄鉴仙族》中的[[" + pj + "]]。\n\n"
    wiki += '== 基本信息 ==\n\n'
    wiki += '{| class="wikitable"\n'
    wiki += '|-\n'
    wiki += '! 字段 !! 内容\n'
    wiki += '|-\n'
    wiki += '| 品阶 || [[' + pj + ']]\n'
    wiki += '|-\n'
    wiki += '| 品阶置信度 || ' + pj_c + '\n'
    wiki += '|-\n'
    wiki += '| 道统 || [[道统-' + dt + '|' + dt + ']]\n'
    wiki += '|-\n'
    wiki += '| 道统置信度 || ' + dt_c + '\n'
    wiki += '|-\n'
    wiki += '| 五行/属性 || —\n'
    wiki += '|-\n'
    wiki += '| 功能标签 || ' + tags + '\n'
    wiki += '|-\n'
    wiki += '| 主要持有者 || ' + holder_text + '\n'
    wiki += '|-\n'
    wiki += '| 首次出现 || 第' + first_ch + '章\n'
    wiki += '|}\n\n'
    wiki += "== 名字由来 ==\n\n''待考据''\n\n"
    wiki += '== 外观描述 ==\n\n' + appear_text + '\n\n'
    wiki += '== 功能与威能 ==\n\n' + func_text + '\n\n'
    wiki += "== 历史沿革 ==\n\n''待考据''\n\n"
    wiki += '=== 使用事件 ===\n' + hist_text + '\n\n'
    wiki += "== 所属道统 ==\n\n'''道统'''：[[道统-" + dt + '|' + dt + "]]\n\n''待补充''\n\n"
    wiki += "== 相关神通/仙基 ==\n\n''待考据''\n\n"
    wiki += '== 相关实体 ==\n\n'
    wiki += '=== 相关法宝/灵资 ===\n—\n\n'
    wiki += '=== 相关人物 ===\n' + holder_text + '\n\n'
    wiki += '=== 相关地点 ===\n—\n\n'
    wiki += '=== 相关事件 ===\n—\n\n'
    wiki += '== 原文引用 ==\n\n' + quote_text + '\n\n'
    wiki += '== 考据备注 ==\n\n'
    wiki += '批次2中频实体 (频次' + freq + '次)\n\n'
    wiki += '[[Category:造物]]\n'
    wiki += '[[' + 'Category:' + pj + ']]\n'
    wiki += '[[Category:道统-' + dt + ']]\n'
    return wiki

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open('/data/workspace/rq0rlzeg/xuanjian-wiki/资料库/造物/玄鉴仙族_法宝考据_批次2_中频实体.md', 'r') as f:
        content = f.read()

    entities = parse_entities(content)
    print(f"解析到 {len(entities)} 个实体")

    count = 0
    for name, entity in entities.items():
        pj, pj_c, dt, dt_c, tags = classify(name, entity.get('functions', []))
        wiki = generate_wiki(entity, pj, pj_c, dt, dt_c, tags)

        safe_name = name.replace('/', '_')
        filepath = os.path.join(OUTPUT_DIR, f'造物-{safe_name}.wiki')
        with open(filepath, 'w') as f:
            f.write(wiki)
        count += 1

    print(f"✅ 生成 {count} 个wiki文件到 {OUTPUT_DIR}")

if __name__ == '__main__':
    main()
