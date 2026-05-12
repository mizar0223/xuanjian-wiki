#!/usr/bin/env python3
"""
宽窗上下文批量提取器 v2
- 遍历375个实体，从39个原著txt提取所有出现位置的上下文宽窗
- 按品类分目录存储: context/{品类}/{实体名}/context.txt + meta.json
- 支持断点恢复（检查已存在文件跳过）
- 进度写入 workstate.json
"""

import os, re, glob, json, sys, time
from collections import defaultdict

# ═══ 配置 ═══
NOVEL_DIR = '/Users/leoshi/AIBOOK/Book_download/output/Parts/玄鉴仙族-按章节数-40章'
CONTEXT_BEFORE = 500
CONTEXT_AFTER = 500
OVERLAP_THRESHOLD = 0.8
BASE_DIR = '/Users/leoshi/AIBOOK/xuanjian/wiki/资料库-法宝:道具:灵资/.workbuddy/wide_window'
CONTEXT_DIR = os.path.join(BASE_DIR, 'context')
WORKSTATE_PATH = os.path.join(BASE_DIR, 'workstate.json')
WORKFLOW_PATH = os.path.join(BASE_DIR, 'workflow.md')

# 品类映射（基于前期考据+分类标注）
CATEGORY_MAP = {
    '颈下羽': '灵资', '金阳煌元': '灵资', '玄卿月粹': '灵资',
    '尚飨银': '灵资', '天星赤金': '灵资', '冲离宝叶': '灵资',
    '颈下羽': '灵资', '虺元灵水': '灵资', '清元灵水': '灵资',
    '洞鹭元水': '灵资', '稚元真水': '灵资', '东命流水': '灵资',
    '归谿牝水': '灵资', '宝降水': '灵资', '秋亡水': '灵资',
    '秋时露': '灵资', '赤光离珀': '灵资',
    '无丈水火': '灵物', '明方天石': '灵物', '六相仪色': '灵物',
    '六相灵石': '灵物', '袤土宝心玉': '灵物', '上善明玄玉': '灵物',
    '一气白寰石': '灵物', '升燠石': '灵物', '地望血石': '灵物',
    '岭穷玄水石': '灵物', '镂金石': '灵物', '不伤石': '灵物',
    '鹤抱石': '灵物', '无咎灵木': '灵物', '褚春悬木': '灵物',
    '万昱剑书': '灵物',
    '宛陵花': '丹药', '天一吐萃丹': '丹药', '望晋玄衍丹': '丹药',
    '空袖玄道散': '丹药', '蛇元丹': '丹药', '玉芽丹': '丹药',
    '遂元丹': '丹药', '箓丹': '丹药', '玄確经心药': '丹药',
    '虺水悬道散': '丹药', '麟光照一丹': '丹药',
    '寒廪': '筑基法器', '玄纹瓶': '筑基法器', '青尺剑': '筑基法器',
    '湛蓝刃': '筑基法器', '月阙剑': '筑基法器',
    '万煞贯金刀': '筑基法器', '赤金百转枪': '筑基法器',
    '道煞玄名剑': '筑基法器', '白殷扇': '筑基法器',
    '大昇': '灵器', '坎金围连环': '灵器', '申白': '灵器',
    '逍垣琉璃宝塔': '灵器', '止戈': '灵器', '赶山赴海虎': '灵器',
    '六角赤焰盏': '灵器', '百甍玄石伞': '灵器',
    '东命瓶': '灵器', '渡迁令': '灵器', '裨庭青芫宝鼎': '灵器',
    '权业武印': '灵器', '招瑶四时鼎': '灵器',
    '辛酉渌泽印': '灵宝', '华阳王钺': '灵宝', '淮江图': '灵宝',
    '冲阳辖星宝盘': '灵宝', '见阳环': '灵宝', '六丁并火令': '灵宝',
    '重火两明仪': '灵宝',
    '毂州鼎': '法宝', '金桥锁': '法宝',
    '大衍天素书': '位别', '渌台醒心剑': '位别',
    '大雪绝锋': '剑道', '命阳白玉剑': '剑道', '薜荔': '剑道',
    '六雷玄罚令': '符箓', '请君执金符': '符箓',
    '玄珠符种': '仙鉴专属', '箓气': '仙鉴专属', '箓丹': '仙鉴专属',
}

# 补充: 所有实体名列表
ALL_ENTITIES = [
    # 从之前各批次汇总提取
    "一",  # placeholder, will be populated
]

def get_all_entity_names():
    """从考据文档提取全量实体名（兼容批次1-3的####格式和批次4的**格式）"""
    entities = set()
    batch_files = glob.glob('/Users/leoshi/AIBOOK/xuanjian/wiki/资料库-法宝:道具:灵资/玄鉴仙族_法宝考据_批次*.md')
    for f in batch_files:
        with open(f, 'r') as fp:
            for line in fp:
                # 批次1-3: #### 格式
                m = re.match(r'^#### (.+)', line)
                if m:
                    entities.add(m.group(1).strip())
                # 批次4: **实体名**（第X章）格式
                m2 = re.match(r'^\*\*([^*]+)\*\*[（(]第', line)
                if m2:
                    entities.add(m2.group(1).strip())
    return sorted(entities)

def classify_entity(name):
    """根据名字推断品类（机械规则）"""
    if name in CATEGORY_MAP:
        return CATEGORY_MAP[name]
    # 后缀规则
    if any(s in name for s in ['丹', '药', '散']):
        return '丹药'
    if any(s in name for s in ['剑', '刀', '枪', '弓', '戟', '刃']):
        if any(s in name for s in ['仙', '灵', '命']):
            return '剑道'
        return '筑基法器'
    if any(s in name for s in ['印', '图', '钺', '令', '书', '环', '盘', '珠']):
        return '灵宝'
    if any(s in name for s in ['石', '玉', '木', '金', '铁', '铜', '银']):
        return '灵物'
    if any(s in name for s in ['水', '火', '气', '月', '阳']):
        if '灵' in name or '紫府' in name:
            return '灵资'
        return '材料'
    if any(s in name for s in ['瓶', '炉', '扇', '旗', '伞', '索', '甲', '衣', '塔', '函', '觯']):
        return '灵器'
    return '待分类'

def find_all_occurrences(text, entity_name):
    pattern = re.escape(f'【{entity_name}】')
    return [(m.start(), m.end()) for m in re.finditer(pattern, text)]

def extract_window(text, pos_start, pos_end):
    win_start = max(0, pos_start - CONTEXT_BEFORE)
    win_end = min(len(text), pos_end + CONTEXT_AFTER)
    return text[win_start:win_end], win_start, win_end

def get_chapter_info(text, position):
    """从给定位置往前搜索最近的章节信息"""
    before = text[:position]
    matches = list(re.finditer(r'第(\d+)章[ 　]*([^\n]{0,40})', before))
    if matches:
        m = matches[-1]
        return int(m.group(1)), m.group(2).strip()
    return 0, '未知'

def merge_windows(windows):
    if not windows:
        return []
    merged = []
    current = dict(windows[0])
    current['merged_from'] = 1
    for w in windows[1:]:
        same_or_adjacent = abs(w['chapter'] - current['chapter']) <= 1
        if current['text']:
            cur_set = set(current['text'])
            next_set = set(w['text'])
            overlap = len(cur_set & next_set) / len(cur_set) if cur_set else 0
        else:
            overlap = 0
        if same_or_adjacent and overlap > OVERLAP_THRESHOLD:
            if len(w['text']) > len(current['text']):
                current['text'] = w['text']
                current['chapter'] = w['chapter']
                current['chapter_title'] = w['chapter_title']
            current['merged_from'] += 1
        else:
            merged.append(current)
            current = dict(w)
            current['merged_from'] = 1
    merged.append(current)
    return merged

def extract_one_entity(entity_name, novel_texts, category):
    """提取单个实体的全量上下文"""
    subdir = os.path.join(CONTEXT_DIR, category, entity_name)
    os.makedirs(subdir, exist_ok=True)
    
    all_windows = []
    for filename, text in novel_texts:
        positions = find_all_occurrences(text, entity_name)
        for pos_start, pos_end in positions:
            window_text, win_start, win_end = extract_window(text, pos_start, pos_end)
            ch_num, ch_title = get_chapter_info(text, win_start)
            all_windows.append({
                'chapter': ch_num, 'chapter_title': ch_title,
                'file': filename, 'text': window_text,
                'entity_pos': pos_start - win_start,
            })
    
    all_windows.sort(key=lambda w: w['chapter'])
    merged = merge_windows(all_windows)
    
    # 写context.txt
    ctx_path = os.path.join(subdir, 'context.txt')
    with open(ctx_path, 'w', encoding='utf-8') as f:
        f.write(f"# 《玄鉴仙族》【{entity_name}】全量上下文\n")
        f.write(f"# 总提及: {len(all_windows)}次 | 合并窗口: {len(merged)}个 | 品类: {category}\n")
        f.write(f"# 窗口参数: 前{CONTEXT_BEFORE}字+后{CONTEXT_AFTER}字\n")
        f.write("=" * 60 + "\n\n")
        for i, m in enumerate(merged):
            f.write(f"↕↕↕ 窗口 {i+1}/{len(merged)} | 第{m['chapter']}章《{m['chapter_title']}》")
            if m['merged_from'] > 1:
                f.write(f" | 合并{m['merged_from']}个连续引用")
            f.write(f" ↕↕↕\n\n")
            f.write(m['text'])
            f.write("\n\n" + "—" * 40 + "\n\n")
        f.write("\n" + "=" * 60 + "\n")
        f.write(f"# {entity_name} 出现索引\n")
        for w in all_windows:
            f.write(f"# 第{w['chapter']}章《{w['chapter_title']}》\n")
    
    # 写meta.json
    chapters = set(w['chapter'] for w in all_windows)
    meta = {
        'entity': entity_name, 'category': category,
        'total_occurrences': len(all_windows),
        'merged_windows': len(merged),
        'unique_chapters': len(chapters),
        'total_chars': sum(len(w['text']) for w in all_windows),
        'merged_chars': sum(len(m['text']) for m in merged),
        'first_chapter': all_windows[0]['chapter'] if all_windows else 0,
        'last_chapter': all_windows[-1]['chapter'] if all_windows else 0,
    }
    with open(os.path.join(subdir, 'meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    
    return meta

def load_workstate():
    if os.path.exists(WORKSTATE_PATH):
        with open(WORKSTATE_PATH, 'r') as f:
            return json.load(f)
    return None

def save_workstate(state):
    with open(WORKSTATE_PATH, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def main():
    # 加载实体列表
    entities = get_all_entity_names()
    print(f"📋 全量实体: {len(entities)}个")
    
    # 分类
    categorized = [(name, classify_entity(name)) for name in entities]
    
    # 加载或创建workstate
    state = load_workstate()
    if state is None:
        state = {
            'version': '2.0',
            'created': time.strftime('%Y-%m-%dT%H:%M:%S+08:00'),
            'total_entities': len(entities),
            'entity_registry': {}
        }
        for name, cat in categorized:
            state['entity_registry'][name] = {
                'category': cat,
                'extraction': 'pending',
                'context_path': os.path.join('context', cat, name, 'context.txt'),
                'meta_path': os.path.join('context', cat, name, 'meta.json'),
            }
        save_workstate(state)
    
    # 统计待处理
    pending = [n for n, r in state['entity_registry'].items() if r['extraction'] == 'pending']
    done = [n for n, r in state['entity_registry'].items() if r['extraction'] == 'done']
    print(f"✅ 已完成: {len(done)} | 🔄 待处理: {len(pending)}")
    
    if not pending:
        print("🎉 全部实体已提取!")
        return
    
    # 加载原著（只加载一次）
    print(f"📚 加载原著txt...")
    novel_files = sorted(glob.glob(os.path.join(NOVEL_DIR, '*.txt')))
    novel_texts = []
    for fp in novel_files:
        with open(fp, 'r', encoding='utf-8') as f:
            novel_texts.append((os.path.basename(fp), f.read()))
    print(f"   已加载 {len(novel_texts)} 个文件")
    
    # 批量提取
    start_time = time.time()
    for i, name in enumerate(pending):
        registry = state['entity_registry'][name]
        cat = registry['category']
        
        print(f"[{i+1}/{len(pending)}] {name} ({cat})...", end=' ', flush=True)
        try:
            meta = extract_one_entity(name, novel_texts, cat)
            registry['extraction'] = 'done'
            registry['meta'] = meta
            print(f"✅ {meta['total_occurrences']}次 {meta['merged_windows']}窗 {meta['merged_chars']:,}字")
        except Exception as e:
            registry['extraction'] = 'failed'
            registry['error'] = str(e)
            print(f"❌ {e}")
        
        # 每10个实体保存一次状态
        if (i + 1) % 10 == 0:
            save_workstate(state)
    
    save_workstate(state)
    elapsed = time.time() - start_time
    done_count = len([r for r in state['entity_registry'].values() if r['extraction'] == 'done'])
    print(f"\n🎉 提取完成! {done_count}/{len(entities)} 成功, 耗时 {elapsed:.0f}秒")

if __name__ == '__main__':
    main()
