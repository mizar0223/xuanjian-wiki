#!/usr/bin/env python3
"""
玄鉴仙族 Wiki 批量页面生成器
- 数据源: 人物年鉴进度.json + 望月李氏家谱.md + NotebookLM素材 + 角色.md + 出场群像.md
- 输出: MediaWiki XML import 文件
"""

import json, os, re, sys, html
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

DATA_DIR = '/Users/leoshi/WorkBuddy/20260323190937'
CHAR_DIR = f'{DATA_DIR}/characters'
REF_DIR = f'{DATA_DIR}/玄鉴图册'
OUTPUT_DIR = '/tmp/wiki_pages'

# ============ 数据加载 ============

def load_progress():
    """加载人物年鉴进度JSON"""
    with open(f'{CHAR_DIR}/人物年鉴进度.json', 'r') as f:
        return json.load(f)

def load_genealogy():
    """加载家谱MD"""
    with open(f'{CHAR_DIR}/望月李氏家谱.md', 'r') as f:
        return f.read()

def load_setting_characters():
    """加载设定集角色数据"""
    with open(f'{REF_DIR}/角色.md', 'r') as f:
        return f.read()

def load_cast():
    """加载出场群像"""
    with open(f'{REF_DIR}/出场群像.md', 'r') as f:
        return f.read()

def load_notebooklm(name):
    """加载角色的NotebookLM素材"""
    path = f'{CHAR_DIR}/{name}/content/{name}_NotebookLM素材.md'
    if os.path.exists(path):
        with open(path, 'r') as f:
            return f.read()
    return ''

# ============ 家谱解析 ============

def parse_genealogy_entries(text):
    """从家谱MD中解析每个角色的详细条目"""
    entries = {}
    # 按 "- **名字**，" 模式分割
    parts = re.split(r'\n(?=- \*\*)', text)
    for part in parts[1:]:
        name_match = re.match(r'- \*\*(.+?)\*\*，', part)
        if name_match:
            name = name_match.group(1).strip()
            entries[name] = part.strip()
    return entries

def extract_genealogy_fields(entry):
    """从家谱条目中提取结构化字段"""
    fields = {}

    # 修为
    m = re.search(r'修为[：:]\s*(?:\*\*)?([^，。\n\*]+)', entry)
    if m:
        fields['修为'] = m.group(1).strip()

    # 仙基
    m = re.search(r'仙基[：:]\s*([^，。\n]+)', entry)
    if m:
        fields['仙基'] = m.group(1).strip()

    # 称号
    m = re.search(r'称号[：:]\s*["""]?([^，。\n"""]+)', entry)
    if m:
        fields['称号'] = m.group(1).strip()

    # 妻子/夫婿 - 只取人名，不要括号内的描述
    # 策略：提取冒号后到第一个逗号/括号/句号之间的名字，并去掉星号
    for label in ['妻子', '正妻', '夫婿']:
        m = re.search(rf'{label}[：:]\s*\*{{0,2}}([^，（(。\n\*]+)', entry)
        if m:
            fields['配偶'] = m.group(1).strip()
            break
        m = re.search(r'正妻[：:]\s*\*\*([^*]+?)\*\*', entry)
        if m:
            fields['配偶'] = m.group(1).strip()

    # 子嗣 - 只取人名，去掉描述
    m = re.search(r'子嗣[：:]\s*([^。\n]+)', entry)
    if m:
        offspring = m.group(1).strip().rstrip('，')
        # 只保留粗体人名部分
        names = re.findall(r'\*\*([^*]+?)\*\*', offspring)
        if names:
            fields['子嗣'] = '、'.join(names)
        else:
            # 没有粗体标记，按括号前取纯人名
            # 例如 "李渊修（嫡长，窦氏生）、李渊平（嫡次，窦氏生）、李渊蛟（庶出，木芽鹿生，过继季脉）"
            # 只取每个括号前的人名
            clean_names = []
            # 按顿号或逗号分割，然后对每段取括号前的名字
            parts = re.split(r'[，、；]', offspring)
            for p in parts:
                p = p.strip()
                # 跳过"字辈"之类的字段
                if '字辈' in p or '备注' in p:
                    continue
                # 取括号前的人名
                name_match = re.match(r'([^（(]+)', p)
                if name_match:
                    name = name_match.group(1).strip()
                    # 跳过空字符串、明显不是人名的文本、和括号残留
                    if (name and len(name) <= 6
                        and '生' not in name and '出' not in name
                        and '过继' not in name and '）' not in name and ')' not in name
                        and not name.startswith('字辈')
                        and not re.search(r'[（(）)]', name)):
                        clean_names.append(name)
            if clean_names:
                fields['子嗣'] = '、'.join(clean_names[:5])

    # 最终清理：子嗣字段去掉所有括号内容
    if '子嗣' in fields:
        fields['子嗣'] = re.sub(r'[（(][^）)]*[）)]', '', fields['子嗣']).strip('、，')

    # 父亲/母亲
    m = re.search(r'父亲[：:]\s*([^，。\n]+)', entry)
    if m:
        fields['父亲'] = m.group(1).strip().rstrip('，')
    m = re.search(r'母亲[：:]\s*([^，。\n]+)', entry)
    if m:
        fields['母亲'] = m.group(1).strip().rstrip('，')

    # 字辈
    m = re.search(r'字辈[：:]\s*(\S+)', entry)
    if m:
        fields['字辈'] = m.group(1).strip()

    # 世代
    m = re.search(r'(\S+世)·', entry)
    if m:
        fields['世代'] = m.group(1)

    # 脉系
    m = re.search(r'脉系[：:]\s*\*\*(.+?)\*\*', entry)
    if m:
        fields['族系'] = m.group(1).strip()
    else:
        m = re.search(r'脉系[：:]\s*([^，。\n]+)', entry)
        if m:
            fields['族系'] = m.group(1).strip()

    # 结局
    m = re.search(r'结局[：:]\s*([^。\n]+)', entry)
    if m:
        fields['结局'] = m.group(1).strip().rstrip('。')

    # 备注
    m = re.search(r'备注[：:]\s*([^。\n]+)', entry)
    if m:
        fields['备注'] = m.group(1).strip()

    return fields

# ============ 设定集解析 ============

def parse_setting_characters(text):
    """从角色.md中解析非李家角色"""
    characters = {}
    # Split by "## " headings
    sections = re.split(r'\n## ', text)
    for section in sections[1:]:
        name_match = re.match(r'(.+)\n', section)
        if name_match:
            name = name_match.group(1).strip()
            characters[name] = section.strip()

    return characters

def extract_setting_fields(section):
    """从设定集角色条目中提取字段"""
    fields = {}

    # 定位
    m = re.search(r'\*\*定位\*\*:\s*(.+)', section)
    if m:
        fields['定位'] = m.group(1).strip()

    # 性格
    m = re.search(r'性格[：:]\s*(.+)', section)
    if m:
        fields['性格'] = m.group(1).strip()

    # 境界/修为
    m = re.search(r'(?:境界|修为)[：:]\s*(.+)', section)
    if m:
        fields['修为'] = m.group(1).strip()

    # 神通
    m = re.search(r'神通[：:]\s*(.+)', section)
    if m:
        fields['神通'] = m.group(1).strip()

    # 角色/人物关系
    m = re.search(r'(?:角色|人物)关系\n(.+?)(?=\n###|\n---|\Z)', section, re.DOTALL)
    if m:
        fields['关系'] = m.group(1).strip()

    # 角色经历/生平
    m = re.search(r'(?:角色经历|生平)\n(.+?)(?=\n###|\n---|\Z)', section, re.DOTALL)
    if m:
        fields['经历'] = m.group(1).strip()

    return fields

# ============ NotebookLM素材解析 ============

def parse_notebooklm(text):
    """解析NotebookLM素材为结构化段落"""
    sections = {}
    current_section = None
    current_content = []

    for line in text.split('\n'):
        # Section headers
        m = re.match(r'##\s+(.+)', line)
        if m:
            if current_section:
                sections[current_section] = '\n'.join(current_content).strip()
            current_section = m.group(1).strip()
            current_content = []
        elif current_section:
            current_content.append(line)

    if current_section:
        sections[current_section] = '\n'.join(current_content).strip()

    return sections

# ============ Wiki页面生成 ============

def make_infobox(progress_data, genealogy_fields, setting_fields):
    """生成{{角色}} Infobox wikitext"""
    params = {}

    # From progress data (highest priority)
    if progress_data:
        params['姓名'] = progress_data.get('name', '')
        params['字辈'] = progress_data.get('generation', '')
        # 族系：优先用branch，补充lineage
        branch = progress_data.get('branch', '')
        lineage = progress_data.get('lineage', '')
        if branch:
            params['族系'] = branch
        elif lineage:
            params['族系'] = lineage
        # 身份：用title，但要清理掉描述性文字；如果太长或不像身份就跳过
        title = progress_data.get('title', '')
        if title:
            # 排除明显是性格描述而非身份的词
            non_identity = ['隐忍', '自保', '稳如', '温厚', '谨慎']
            if not any(w in title for w in non_identity) and len(title) <= 8:
                params['身份'] = title

    # Override/补充 from genealogy fields
    for key in ['修为', '仙基', '配偶', '子嗣', '族系']:
        if key in genealogy_fields and not params.get(key):
            params[key] = genealogy_fields[key]

    # 修为 - 清理，只取核心级别
    if '修为' in params:
        xiwei = params['修为']
        # 去掉括号内的补充说明
        xiwei = re.sub(r'[（(].+?[）)]', '', xiwei).strip()
        params['修为'] = xiwei

    # Special: 父母字段从家谱的父母字段组合
    father = genealogy_fields.get('父亲', '')
    mother = genealogy_fields.get('母亲', '')
    if father or mother:
        parents_parts = []
        if father:
            father = re.sub(r'[（(].+?[）)]', '', father).strip()
            parents_parts.append(father)
        if mother:
            mother = re.sub(r'[（(].+?[）)]', '', mother).strip()
            parents_parts.append(mother)
        params['父母'] = '、'.join(parents_parts)

    # 师承
    if '师承' in genealogy_fields and not params.get('师承'):
        params['师承'] = genealogy_fields['师承']

    # From setting fields
    if setting_fields:
        if '修为' in setting_fields and '修为' not in params:
            params['修为'] = setting_fields['修为']

    # Build wikitext
    lines = ['{{角色']
    for key, val in params.items():
        if val and len(str(val)) < 50:  # 限制字段长度，避免截断问题
            lines.append(f'|{key}={val}')
    lines.append('}}')
    return '\n'.join(lines)

def make_body_genealogy(entry_text):
    """从家谱条目生成页面正文"""
    # 清理条目文本，去掉开头的 "- **名字**，" 前缀
    cleaned = re.sub(r'^- \*\*.+?\*\*，\s*', '', entry_text)
    # 转为wiki格式
    cleaned = re.sub(r'\*\*([^*]+?)\*\*', r"'''\1'''", cleaned)

    # 将紧凑的条目拆分为列表格式
    # 例如: "妻子：XXX。子嗣：XXX。修为：XXX。"
    # 先按句号分段
    segments = re.split(r'。\s*', cleaned)
    lines = []
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        # 检查是否是"标签：值"格式
        m = re.match(r"^'''(.+?)'''[：:]\s*(.+)", seg)
        if m:
            label = m.group(1)
            value = m.group(2)
            lines.append(f"* '''{label}'''：{value}")
        else:
            lines.append(seg)

    return '\n'.join(lines)

def make_body_notebooklm(sections):
    """从NotebookLM素材生成页面正文"""
    lines = []
    # 需要跳过的自动生成章节（自检/引用汇总等）
    skip_sections = {'7 维度自检结果', '原文引用汇总'}

    for title, content in sections.items():
        # 检查是否应该跳过
        clean_title = re.sub(r'^[一二三四五六七八九十]+、\s*', '', title).strip()
        if clean_title in skip_sections or any(s in title for s in ['自检', '维度', '引用汇总']):
            continue

        if re.match(r'^[一二三四五六七八九十]+、', title):
            wiki_title = clean_title
        else:
            wiki_title = title
        lines.append(f'=={wiki_title}==')
        lines.append('')
        # 清理内容
        for line in content.split('\n'):
            # 跳过水平分隔线
            if re.match(r'^---+\s*$', line):
                continue
            # 跳过空行（保留一个）
            if line.strip() == '':
                lines.append('')
                continue
            # 将 ### 子标题转为 === ===
            m = re.match(r'^###\s+(.+)', line)
            if m:
                lines.append(f'==={m.group(1).strip()}===')
                continue
            # 将 - **text** 转为 * '''text'''
            if line.strip().startswith('- **'):
                line = re.sub(r'^-\s+\*\*([^*]+?)\*\*', r"* '''\1'''", line)
            elif line.strip().startswith('- '):
                line = '* ' + line.strip()[2:]
            lines.append(line)
        lines.append('')

    return '\n'.join(lines)

def make_body_setting(section_text):
    """从设定集角色条目生成页面正文"""
    cleaned = section_text
    # Convert markdown to wikitext
    cleaned = re.sub(r'\*\*([^*]+?)\*\*', r"'''\1'''", cleaned)
    cleaned = re.sub(r'^###\s+(.+)', r'===\1===', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'^##\s+(.+)', r'==\1==', cleaned, flags=re.MULTILINE)
    # Convert markdown image links
    cleaned = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'[[File:\2|thumb|\1]]', cleaned)
    return cleaned.strip()

def make_categories(progress_data, genealogy_fields):
    """生成分类标签"""
    cats = ['角色']
    if progress_data:
        gen = progress_data.get('generation', '')
        if gen:
            cats.append(f'{gen}角色')
        branch = progress_data.get('branch', '')
        if branch:
            # 只取前两个字（如"伯脉""仲脉""叔脉""季脉"）
            short_branch = re.match(r'^(.{2,3}脉)', branch)
            if short_branch:
                cats.append(short_branch.group(1))
    if genealogy_fields:
        xiwei = genealogy_fields.get('字辈', '')
        if xiwei and len(xiwei) <= 2 and '无' not in xiwei:
            cats.append(f'{xiwei}字辈')
    return '\n'.join(f'[[Category:{c}]]' for c in cats)

def generate_character_page(name, progress_data, genealogy_fields, genealogy_entry,
                             notebooklm_sections, setting_section, setting_fields):
    """生成单个角色的完整wiki页面内容"""
    parts = []

    # 1. Infobox
    infobox = make_infobox(progress_data, genealogy_fields, setting_fields)
    parts.append(infobox)
    parts.append('')

    # 2. 简介 (如果有NotebookLM素材的"出身背景"段落，提取第一段)
    if notebooklm_sections:
        bg = notebooklm_sections.get('一、出身背景', '')
        if not bg:
            for key, val in notebooklm_sections.items():
                if '背景' in key or '出身' in key:
                    bg = val
                    break
        if bg:
            # 提取纯文本简介（去掉列表标记）
            intro_lines = []
            for line in bg.split('\n'):
                line = line.strip()
                if line.startswith('- '):
                    line = line[2:]
                line = re.sub(r'\*\*([^*]+?)\*\*', r"'''\1'''", line)
                if line:
                    intro_lines.append(line)
            parts.append(' '.join(intro_lines[:3]))  # 取前3条作为简介
            parts.append('')

    # 3. 正文 - 优先使用NotebookLM素材，补充家谱数据
    if notebooklm_sections:
        body = make_body_notebooklm(notebooklm_sections)
        parts.append(body)
    elif genealogy_entry:
        body = make_body_genealogy(genealogy_entry)
        if body:
            parts.append('==生平==')
            parts.append('')
            parts.append(body)
            parts.append('')

    if setting_section and not notebooklm_sections:
        body = make_body_setting(setting_section)
        if body:
            parts.append(body)
            parts.append('')

    # 4. 家谱数据补充（如果NotebookLM没有覆盖到的家谱信息）
    if genealogy_entry and notebooklm_sections:
        # 补充家谱中的结局等NotebookLM可能没有的信息
        ending = genealogy_fields.get('结局', '')
        if ending and '结局' not in ' '.join(notebooklm_sections.keys()):
            parts.append('==结局==')
            parts.append('')
            parts.append(ending)
            parts.append('')

    # 5. 分类
    cats = make_categories(progress_data, genealogy_fields)
    parts.append(cats)

    return '\n'.join(parts)


# ============ 主流程 ============

def main():
    print("=== 玄鉴仙族 Wiki 批量页面生成器 ===\n")

    # Load data
    progress = load_progress()
    genealogy = load_genealogy()
    setting_text = load_setting_characters()
    cast_text = load_cast()

    # Parse data
    genealogy_entries = parse_genealogy_entries(genealogy)
    setting_chars = parse_setting_characters(setting_text)

    print(f"数据加载完成:")
    print(f"  家谱条目: {len(genealogy_entries)}")
    print(f"  设定集角色: {len(setting_chars)}")

    # Build progress index
    progress_index = {}
    all_progress = []
    for c in progress.get('completed', []):
        all_progress.append(c)
    for c in progress.get('inProgress', []):
        all_progress.append(c)
    for c in progress.get('pending', []):
        all_progress.append(c)
    for c in all_progress:
        progress_index[c['name']] = c
    print(f"  进度条目: {len(progress_index)}")

    # Generate pages
    pages = {}  # title -> content

    # ---- Phase 1: 李家角色 (from progress + genealogy) ----
    for name, pdata in progress_index.items():
        genealogy_entry = genealogy_entries.get(name, '')
        genealogy_fields = extract_genealogy_fields(genealogy_entry) if genealogy_entry else {}
        nbml = load_notebooklm(name)
        nbml_sections = parse_notebooklm(nbml) if nbml else {}

        content = generate_character_page(
            name=name,
            progress_data=pdata,
            genealogy_fields=genealogy_fields,
            genealogy_entry=genealogy_entry,
            notebooklm_sections=nbml_sections,
            setting_section='',
            setting_fields={}
        )
        pages[name] = content
        print(f"  ✓ {name}")

    # ---- Phase 2: 非李家角色 (from setting + cast) ----
    # Combine setting_chars and cast
    all_setting = {**setting_chars}

    # Parse cast entries
    cast_entries = {}
    cast_sections = re.split(r'\n### ', cast_text)
    for section in cast_sections[1:]:
        name_match = re.match(r'(.+)\n', section)
        if name_match:
            cast_name = name_match.group(1).strip()
            cast_entries[cast_name] = section.strip()

    # Merge cast entries that aren't already in setting_chars
    for name, entry in cast_entries.items():
        if name not in all_setting:
            all_setting[name] = entry

    print(f"\n  非李家角色: {len(all_setting)}")

    for name, section_text in all_setting.items():
        if name in progress_index:  # Already processed
            continue

        setting_fields = extract_setting_fields(section_text)
        content = generate_character_page(
            name=name,
            progress_data=None,
            genealogy_fields={},
            genealogy_entry='',
            notebooklm_sections={},
            setting_section=section_text,
            setting_fields=setting_fields
        )
        pages[name] = content

    # ---- Phase 3: 更新角色索引页 ----
    index_lines = ['本维基收录的所有角色列表。', '']
    # Group by generation
    gen_groups = {}
    for name, pdata in progress_index.items():
        gen = pdata.get('generation', '未知')
        if gen not in gen_groups:
            gen_groups[gen] = []
        gen_groups[gen].append(name)

    for gen in ['八世', '九世', '十世', '十一世', '十二世', '十三世', '十四世', '十五世', '十六世', '十七世', '未知']:
        if gen in gen_groups:
            index_lines.append(f'=={gen}==')
            index_lines.append('')
            for name in sorted(gen_groups[gen]):
                pdata = progress_index[name]
                title = pdata.get('title', '')
                if title:
                    index_lines.append(f'* [[{name}]] — {title}')
                else:
                    index_lines.append(f'* [[{name}]]')
            index_lines.append('')

    # Non-李 family characters
    non_li = [n for n in all_setting if not n.startswith('李')]
    if non_li:
        index_lines.append('==其他角色==')
        index_lines.append('')
        for name in sorted(non_li):
            index_lines.append(f'* [[{name}]]')
        index_lines.append('')

    pages['角色索引'] = '\n'.join(index_lines)

    print(f"\n共生成 {len(pages)} 个页面")

    # ---- Output as individual files for inspection ----
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for title, content in pages.items():
        # Replace / in title for filename safety
        safe_name = title.replace('/', '_')
        with open(f'{OUTPUT_DIR}/{safe_name}.wiki', 'w') as f:
            f.write(content)

    print(f"页面文件已保存到 {OUTPUT_DIR}/")

    # ---- Output as MediaWiki XML import ----
    xml_path = f'{OUTPUT_DIR}/xuanjian_import.xml'
    generate_xml_import(pages, xml_path)
    print(f"XML导入文件已保存到 {xml_path}")

    return pages

def generate_xml_import(pages, filepath):
    """生成MediaWiki XML import文件"""
    # MediaWiki XML import format
    now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<mediawiki xmlns="http://www.mediawiki.org/xml/export-0.10/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xsi:schemaLocation="http://www.mediawiki.org/xml/export-0.10/ '
        'http://www.mediawiki.org/xml/export-0.10.xsd" '
        'version="0.10" xml:lang="zh-hans">',
        '',
    ]

    for title, content in pages.items():
        lines.append('  <page>')
        lines.append(f'    <title>{html.escape(title)}</title>')
        lines.append('    <ns>0</ns>')
        lines.append('    <revision>')
        lines.append(f'      <timestamp>{now}</timestamp>')
        lines.append('      <contributor>')
        lines.append('        <username>WikiAdmin</username>')
        lines.append('      </contributor>')
        lines.append(f'      <text xml:space="preserve">{html.escape(content)}</text>')
        lines.append('    </revision>')
        lines.append('  </page>')
        lines.append('')

    lines.append('</mediawiki>')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

if __name__ == '__main__':
    main()
