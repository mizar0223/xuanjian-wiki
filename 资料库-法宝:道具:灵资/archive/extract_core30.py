#!/usr/bin/env python3
"""从4个批次的考据文档中提取30个核心实体的结构化数据"""

import re
import json
import glob

# 30个核心实体（按品阶+道统+剧情重要性选择）
CORE_30 = [
    # 灵资/灵物/材料 (6个)
    "颈下羽",      # 灵资, 府水, 42次
    "金阳煌元",    # 极品灵气, 明阳, 30次
    "玄卿月粹",    # 极品灵气, 太阴, 16次
    "无丈水火",    # 灵物, 真炁, 62次
    "明方天石",    # 灵物, 明阳, 51次
    "祢水寒铁",    # 材料, 府水, 9次

    # 宝药/灵根 (1个)
    "宛陵花",      # 宝药, 39次

    # 筑基法器 (2个)
    "寒廪",        # 筑基法剑, 玉真, 33次
    "玄纹瓶",      # 极品古法器, 39次

    # 灵胚→灵器 (1个)
    "大昇",        # 灵胚→灵器, 明阳/离火, 60次 ★主角武器

    # 灵器 (4个)
    "坎金围连环",  # 上品灵器, 坎水, 7次
    "逍垣琉璃宝塔",# 灵器, 23次
    "申白",        # 灵弓, 庚金, 21次
    "止戈",        # 紫府灵器仿制, 20次

    # 古灵器/灵宝 (6个)
    "辛酉渌泽印",  # 古灵器/灵宝, 府水, 71次
    "华阳王钺",    # 灵宝, 明阳, 87次
    "淮江图",      # 灵宝, 府水?, 78次
    "冲阳辖星宝盘",# 灵宝, 明阳?, 70次
    "见阳环",      # 特殊灵宝, 明阳, 23次
    "六丁并火令",  # 古灵器, 并火, 49次

    # 法宝 (1个)
    "毂州鼎",      # 法宝, 16次

    # 位别 (1个)
    "大衍天素书",  # 位别, 司天, 50次

    # 剑道 (2个)
    "大雪绝锋",    # 灵宝剑, 剑道, 43次
    "命阳白玉剑",  # 仙剑, 玉真, 6次

    # 符箓 (1个)
    "六雷玄罚令",  # 符箓, 霄雷, 24次

    # 特殊/多分类 (5个)
    "三候戍玄火",  # 火焰/灵物?, 离火, 81次
    "问武平清觯",  # 觯器, 25次
    "玄库请凭函",  # 函匣, 28次
    "青尺剑",      # 筑基法剑, 21次
    "百甍玄石伞",  # 伞器, 27次
]

def extract_section(text, section_name):
    """从实体文本中提取指定section"""
    # 匹配 **section**: 到下一个 ** 或 ####
    pattern = rf'\*\*{section_name}\*\*[：:]\s*\n((?:> .*\n)+)'
    m = re.search(pattern, text)
    if m:
        lines = m.group(1).strip().split('\n')
        return [l[2:].strip() if l.startswith('> ') else l.strip() for l in lines if l.strip()]
    return []

def extract_field(text, field_name):
    """提取单行字段"""
    pattern = rf'-\s*\*\*{field_name}\*\*[：:]\s*(.*)'
    m = re.search(pattern, text)
    return m.group(1).strip() if m else ""

def parse_entity_block(text):
    """解析单个实体的完整块"""
    result = {}
    result['频次'] = extract_field(text, '出现频次')
    result['首次出现'] = extract_field(text, '首次出现')
    result['最新出现'] = extract_field(text, '最新出现')
    result['类型_原始'] = extract_field(text, '法宝类型')
    result['章节跨度'] = extract_field(text, '章节跨度')
    result['功能描述'] = extract_section(text, '功能描述')
    result['外形描述'] = extract_section(text, '外形描述')
    result['来源描述'] = extract_section(text, '来源描述')
    result['持有者'] = extract_section(text, '持有者')
    result['使用历史'] = extract_section(text, '使用历史')
    return result

def split_by_entities(content):
    """按 #### 分割实体"""
    blocks = re.split(r'\n(?=#### )', content)
    entities = {}
    for block in blocks:
        m = re.match(r'#### (.+)', block)
        if m:
            name = m.group(1).strip()
            entities[name] = block.strip()
    return entities

def main():
    batch_files = sorted(glob.glob('/Users/leoshi/AIBOOK/xuanjian/wiki/资料库-法宝:道具:灵资/玄鉴仙族_法宝考据_批次*.md'))

    all_entities = {}
    for f in batch_files:
        with open(f, 'r') as fp:
            content = fp.read()
        entities = split_by_entities(content)
        all_entities.update(entities)

    # 提取30个核心实体
    core_data = {}
    for name in CORE_30:
        if name in all_entities:
            core_data[name] = parse_entity_block(all_entities[name])
        else:
            print(f"⚠️ 未找到：{name}")

    # 统计
    found = len(core_data)
    missing = [n for n in CORE_30 if n not in all_entities]

    # 输出
    output = {
        "meta": {
            "total_entities": len(all_entities),
            "core_30_found": found,
            "core_30_missing": missing,
            "extraction_date": "2026-05-09"
        },
        "entities": core_data
    }

    out_path = '/Users/leoshi/AIBOOK/xuanjian/wiki/资料库-法宝:道具:灵资/.workbuddy/phase0_core30_raw.json'
    with open(out_path, 'w') as fp:
        json.dump(output, fp, ensure_ascii=False, indent=2)

    print(f"✅ 提取完成：{found}/{len(CORE_30)} 个核心实体")
    print(f"⚠️ 缺失：{missing if missing else '无'}")
    print(f"📁 输出：{out_path}")

if __name__ == '__main__':
    main()
