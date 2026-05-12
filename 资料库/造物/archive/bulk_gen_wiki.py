#!/usr/bin/env python3
"""批量生成批次3+4的276个低频实体Wiki页面"""

import re
import os

# ===== 分类规则引擎 =====

def classify_pindao(name, raw_type, func_text, appear_text):
    """推断品阶"""
    name_lower = name
    
    # 丹药
    if '丹' in name:
        return '丹药'
    if '药' in name and '材' not in name and '宝' not in name:
        return '灵药'
    
    # 材料类
    material_keywords = ['金', '银', '铜', '铁', '石', '玉', '木', '水', '火', '土']
    if any(k in name for k in material_keywords) and not any(s in name for s in ['剑', '刀', '枪', '弓', '令', '符', '珠', '印', '环', '鼎', '瓶', '镜', '图', '书', '旗', '扇', '塔', '伞', '索', '甲', '衣']):
        if '灵' in name or '紫府' in func_text:
            return '灵资'
        if '极品' in func_text:
            return '极品灵气'
        return '材料'
    
    # 练气法器
    if '练气' in func_text and ('法' in func_text or '器' in func_text):
        return '练气法器'
    
    # 器物类
    if '剑' in name:
        if '仙' in name or '灵宝' in func_text:
            return '灵宝剑'
        return '筑基法剑'
    if '刀' in name or '枪' in name or '弓' in name:
        if '灵器' in func_text:
            return '灵器'
        return '筑基法器'
    if any(s in name for s in ['令', '符']):
        if '古' in func_text:
            return '古符箓'
        if '紫府' in func_text:
            return '紫府符箓'
        return '符箓'
    if any(s in name for s in ['珠']):
        if '古' in func_text:
            return '古灵器'
        if '灵器' in func_text:
            return '灵器'
        return '法器'
    if any(s in name for s in ['印', '环']):
        return '灵器'
    if any(s in name for s in ['鼎', '炉']):
        return '灵器'
    if any(s in name for s in ['瓶', '罐']):
        if '古' in func_text:
            return '古法器'
        return '法器'
    if any(s in name for s in ['图', '书']):
        if '灵宝' in func_text:
            return '灵宝'
        return '典籍'
    if any(s in name for s in ['旗', '扇']):
        return '法器'
    if any(s in name for s in ['塔']):
        return '灵器'
    if any(s in name for s in ['伞']):
        return '灵器'
    if any(s in name for s in ['索', '甲', '衣']):
        if '灵器' in func_text:
            return '灵器'
        return '法器'
    if any(s in name for s in ['盘']):
        return '灵器'
    
    # 灵气/灵萃
    if '气' in name and '灵' in name:
        return '灵气'
    
    # 灵水/灵火类
    if '水' in name:
        if '灵' in name or '灵水' in func_text:
            return '灵水'
        return '灵资'
    if '火' in name:
        if '灵' in name or '灵火' in func_text:
            return '灵火'
        return '灵资'
    
    # 默认
    return '待分类'


def classify_daotong(name, raw_type, func_text, appear_text):
    """推断道统"""
    
    # 火德
    if any(k in name for k in ['阳', '煌', '明光']):
        return '明阳'
    if any(k in name for k in ['离', '焚', '赤', '炎', '雉']):
        return '离火'
    if '真火' in name or '真火' in func_text:
        return '真火'
    if any(k in name for k in ['并火', '六丁']):
        return '并火'
    if '牡' in name and '火' in name:
        return '牡火'
    
    # 水德
    if any(k in name for k in ['渌', '颈', '羽', '府水']):
        return '府水'
    if any(k in name for k in ['坎', '坎水']):
        return '坎水'
    if '牝' in name:
        return '牝水'
    if '水' in name:
        if '泉' in name or '流' in name or '溪' in name:
            return '府水'
        return '坎水'
    
    # 金德
    if any(k in name for k in ['庚', '申白', '执金']):
        return '庚金'
    if '库' in name and '金' in name:
        return '库金'
    if '金' in name and any(k in name for k in ['乌', '白', '赤', '玄', '沉']):
        return '庚金'
    
    # 土德
    if '艮' in name or '赶山' in name:
        return '艮土'
    
    # 木德
    if '巽' in name:
        return '巽木'
    if '木' in name:
        if any(k in name for k in ['桑', '林', '树', '参']):
            return '巽木'
        return '巽木'
    
    # 阴阳
    if any(k in name for k in ['太阴', '月', '玄卿', '薜荔']):
        return '太阴'
    if any(k in name for k in ['太阳', '郁仪']):
        return '太阳'
    if '少阳' in name:
        return '少阳'
    if '厥阴' in name:
        return '厥阴'
    
    # 炁
    if '紫' in name and ('炁' in name or '珠' in name):
        return '紫炁'
    if '真炁' in name or '无丈' in name:
        return '真炁'
    if '青' in name and ('宣' in name or '尺' in name):
        return '青宣'
    if '邃' in name:
        return '邃炁'
    if '寒' in name:
        return '寒炁'
    if '晞' in name or '曦' in name:
        return '晞炁'
    if '煞' in name:
        return '煞炁'
    
    # 雷
    if any(k in name for k in ['雷', '霆', '玄罚', '玄雷']):
        return '霄雷'
    if '元' in name and '磁' in name:
        return '元雷'
    
    # 火（没有更具体的匹配）
    if '火' in name:
        return '离火'
    
    # 玉
    if '玉真' in name or ('玉' in name and '剑' in name):
        return '玉真'
    
    # 水（没有更具体的匹配）
    if '水' in func_text:
        return '坎水'
    
    return '未知'


def classify_tags(name, raw_type, func_text):
    """推断功能标签"""
    tags = []
    if '攻' in func_text or '杀' in func_text or '斩' in func_text:
        tags.append('攻击')
    if '防' in func_text or '御' in func_text or '护' in func_text or '盾' in func_text or '甲' in func_text:
        tags.append('防御')
    if '炼' in name and any(k in func_text for k in ['修炼', '辅助', '突破']):
        tags.append('辅助修炼')
    if '丹' in func_text and '炼' in func_text:
        tags.append('炼丹材料')
    if '器' in func_text and '炼' in func_text:
        tags.append('炼器材料')
    if '镇' in func_text:
        tags.append('镇压')
    if '储' in func_text or '纳' in func_text:
        tags.append('储物')
    if '飞' in func_text or '遁' in func_text:
        tags.append('飞行')
    if '探' in func_text or '察' in func_text:
        tags.append('探查')
    if '治' in func_text or '疗' in func_text:
        tags.append('治疗')
    if '召' in func_text or '唤' in func_text:
        tags.append('召唤')
    if '幻' in func_text or '变' in func_text:
        tags.append('幻化')
    if '增' in func_text:
        tags.append('增幅')
    if not tags:
        tags.append('待分类')
    return ', '.join(tags)


def escape_wiki(text):
    """转义wiki特殊字符"""
    if not text:
        return ''
    text = text.replace('\n', ' ').replace('\r', '')
    return text


# ===== 实体解析 =====

def parse_batch3(filepath):
    """解析批次3文件"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    entities = []
    # 分割实体块
    blocks = re.split(r'\n(?=#### )', content)
    
    for block in blocks:
        name_match = re.match(r'#### (.+)', block)
        if not name_match:
            continue
        name = name_match.group(1).strip()
        
        # 提取字段
        raw_type = re.search(r'\*\*类型\*\*[：:]\s*(.+?)\s*\|', block)
        raw_type = raw_type.group(1).strip() if raw_type else '待分类'
        
        freq = re.search(r'频次\*\*[：:]\s*(.+?)(?:\n|次)', block)
        freq = freq.group(1).strip() if freq else '?'
        
        first_ch = re.search(r'首次\*\*[：:]\s*(.+?)(?:\n)', block)
        first_ch = first_ch.group(1).strip() if first_ch else '?'
        
        latest_ch = re.search(r'最新\*\*[：:]\s*(.+?)(?:\n)', block)
        latest_ch = latest_ch.group(1).strip() if latest_ch else '?'
        
        func = re.search(r'功能\*\*[：:]\s*((?:.|\n)*?)(?:\n- \*\*外形|$)', block)
        if func:
            func_text = func.group(1).strip()
            func_text = re.sub(r'\n+', ' ', func_text)
            func_text = func_text.strip().lstrip('。；，、')
        else:
            func_text = '待考据'
        
        appear = re.search(r'外形\*\*[：:]\s*((?:.|\n)*?)(?:\n- \*\*使用|$)', block)
        if appear:
            appear_text = appear.group(1).strip()
            appear_text = re.sub(r'\n+', ' ', appear_text)
            appear_text = appear_text.strip().lstrip('。；，、')
        else:
            appear_text = ''
        
        use_hist = re.search(r'使用\*\*[：:]\s*\n((?:.|\n)*?)(?=\n####|\Z)', block)
        use_lines = []
        if use_hist:
            for line in use_hist.group(1).strip().split('\n'):
                line = line.strip()
                if line.startswith('· '):
                    use_lines.append(line[2:])
        use_text = ' | '.join(use_lines[:3]) if use_lines else ''
        
        entities.append({
            'name': name,
            'raw_type': raw_type,
            'freq': freq,
            'first_ch': first_ch,
            'latest_ch': latest_ch,
            'func_text': func_text,
            'appear_text': appear_text,
            'use_text': use_text,
        })
    
    return entities


def parse_batch4(filepath):
    """解析批次4文件（格式不同，更简洁）"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    entities = []
    # 匹配格式：**实体名**（第X章《章名》）
    # 或 · 场景：...
    
    # 先按段落找
    lines = content.split('\n')
    current_name = None
    current_scene = ''
    current_func = ''
    current_appear = ''
    
    for line in lines:
        # 匹配 **实体名**（章节）
        name_match = re.match(r'\*\*(.+?)\*\*[（(]第(\d+)章[《](.+?)[》](.*)', line)
        if name_match:
            if current_name:
                entities.append({
                    'name': current_name,
                    'raw_type': '待分类',
                    'freq': '1次',
                    'first_ch': current_first_ch,
                    'latest_ch': current_first_ch,
                    'func_text': current_func or '待考据',
                    'appear_text': current_appear or '',
                    'use_text': current_scene or '',
                })
            
            current_name = name_match.group(1).strip()
            current_first_ch = f"第{name_match.group(2)}章《{name_match.group(3)}》"
            current_scene = ''
            current_func = ''
            current_appear = ''
            if name_match.group(4).strip():
                current_scene = name_match.group(4).strip()
            continue
        
        # 匹配 · 场景：
        scene_match = re.match(r'·\s*场景[：:]\s*(.+)', line)
        if scene_match and current_name:
            current_scene = scene_match.group(1).strip()
            continue
        
        # 匹配 · 功能：
        func_match = re.match(r'·\s*功能[：:]\s*(.+)', line)
        if func_match and current_name:
            current_func = func_match.group(1).strip()
            continue
        
        # 匹配 · 外形：
        appear_match = re.match(r'·\s*外形[：:]\s*(.+)', line)
        if appear_match and current_name:
            current_appear = appear_match.group(1).strip()
            continue
        
        # 匹配 · 来源：
        source_match = re.match(r'·\s*来源[：:]\s*(.+)', line)
        if source_match and current_name:
            continue  # 暂不处理
    
    # 最后一个
    if current_name:
        entities.append({
            'name': current_name,
            'raw_type': '待分类',
            'freq': '1次',
            'first_ch': current_first_ch,
            'latest_ch': current_first_ch,
            'func_text': current_func or '待考据',
            'appear_text': current_appear or '',
            'use_text': current_scene or '',
        })
    
    return entities


# ===== Wiki页面生成 =====

def generate_wiki(entity):
    """生成单个wiki页面"""
    name = entity['name']
    raw_type = entity['raw_type']
    func_text = entity['func_text']
    appear_text = entity.get('appear_text', '')
    use_text = entity.get('use_text', '')
    first_ch = entity.get('first_ch', '?')
    
    # 分类推断
    pindao = classify_pindao(name, raw_type, func_text, use_text)
    daotong = classify_daotong(name, raw_type, func_text, use_text)
    tags = classify_tags(name, raw_type, func_text)
    
    # 清理功能描述文本 - 去除前导标点/碎片
    def clean_text(t):
        if not t:
            return ''
        t = escape_wiki(t)
        # 去除前导碎片字符（中英文标点、数字、短碎片）
        t = re.sub(r'^[。；，、；：\!?\,\，…\.\d\s"\'）\)】\]]+', '', t)
        t = t.strip()
        return t[:250]
    
    func_clean = clean_text(func_text) or '待考据'
    appear_clean = clean_text(appear_text) or '原文未详述'
    use_clean = clean_text(use_text) or '待补充'
    
    wiki = f"""{{{{导航栏}}}}

'''{name}'''是《玄鉴仙族》中的[[{pindao}]]。

== 基本信息 ==

{{| class="wikitable"
|-
! 字段 !! 内容
|-
| 品阶 || [[{pindao}]]
|-
| 品阶置信度 || ⚡推断
|-
| 道统 || [[道统-{daotong}|{daotong}]]
|-
| 道统置信度 || ⚡推断
|-
| 五行/属性 || —
|-
| 功能标签 || {tags}
|-
| 首次出现 || {first_ch}
|}}

== 名字由来 ==

''待考据''

== 外观描述 ==

{appear_clean}

== 功能与威能 ==

{func_clean}

== 历史沿革 ==

''待考据''

== 所属道统 ==

'''道统'''：[[道统-{daotong}|{daotong}]]

⚡推断（基于名字关键词和功能特征）

== 相关神通/仙基 ==

''待考据''

== 原文引用 ==

{use_clean}

== 考据备注 ==

— 

[[Category:造物]]
[[Category:{pindao}]]
[[Category:道统-{daotong}]]
"""
    return wiki


# ===== 主流程 =====

def main():
    base_dir = '/data/workspace/rq0rlzeg/xuanjian-wiki/资料库/造物'
    
    # 解析批次3
    print("📖 解析批次3...")
    batch3 = parse_batch3(os.path.join(base_dir, '玄鉴仙族_法宝考据_批次3_低频实体.md'))
    print(f"  找到 {len(batch3)} 个实体")
    
    # 解析批次4
    print("📖 解析批次4...")
    batch4 = parse_batch4(os.path.join(base_dir, '玄鉴仙族_法宝考据_批次4_仅出现1次.md'))
    print(f"  找到 {len(batch4)} 个实体")
    
    # 生成批次3
    out3 = os.path.join(base_dir, '.workbuddy/output_wiki_batch3')
    os.makedirs(out3, exist_ok=True)
    print(f"\n🔨 生成批次3 ({len(batch3)}个)...")
    for i, e in enumerate(batch3):
        wiki = generate_wiki(e)
        safe_name = e['name'].replace('/', '_')
        filepath = os.path.join(out3, f'造物-{safe_name}.wiki')
        with open(filepath, 'w') as f:
            f.write(wiki)
        if (i + 1) % 30 == 0:
            print(f"  已完成 {i+1}/{len(batch3)}")
    
    print(f"  ✅ 批次3: {len(batch3)} 个wiki页面已生成")
    
    # 生成批次4
    out4 = os.path.join(base_dir, '.workbuddy/output_wiki_batch4')
    os.makedirs(out4, exist_ok=True)
    print(f"\n🔨 生成批次4 ({len(batch4)}个)...")
    for i, e in enumerate(batch4):
        wiki = generate_wiki(e)
        safe_name = e['name'].replace('/', '_')
        filepath = os.path.join(out4, f'造物-{safe_name}.wiki')
        with open(filepath, 'w') as f:
            f.write(wiki)
        if (i + 1) % 50 == 0:
            print(f"  已完成 {i+1}/{len(batch4)}")
    
    print(f"  ✅ 批次4: {len(batch4)} 个wiki页面已生成")
    
    # 统计
    total = len(batch3) + len(batch4)
    print(f"\n📊 总计: {total} 个wiki页面")
    
    # 品阶分布
    all_entities = batch3 + batch4
    pindao_dist = {}
    daotong_dist = {}
    for e in all_entities:
        pd = classify_pindao(e['name'], e['raw_type'], e['func_text'], e.get('use_text', ''))
        dt = classify_daotong(e['name'], e['raw_type'], e['func_text'], e.get('use_text', ''))
        pindao_dist[pd] = pindao_dist.get(pd, 0) + 1
        daotong_dist[dt] = daotong_dist.get(dt, 0) + 1
    
    print("\n📊 品阶分布:")
    for k, v in sorted(pindao_dist.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")
    
    print("\n📊 道统分布:")
    for k, v in sorted(daotong_dist.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")


if __name__ == '__main__':
    main()
