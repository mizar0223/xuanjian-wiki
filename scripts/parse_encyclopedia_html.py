#!/usr/bin/env python3
"""
玄鉴仙族百科全书 HTML 解析器
- 数据源: 资料库 - 神通/02_加工产出/玄鑒仙族_中文百科全書.html
- 功能:
  1. 从 HTML 中提取 sections JSON 数据
  2. 结构化解析每个角色条目（姓名、修为、仙基、关系、事件）
  3. 与现有 pages/人物与势力/ 中已有页面做 diff
  4. 对已有页面补充"人物关系"和"所属势力"字段（不覆盖）
  5. 生成补充记录日志
"""

import json, os, re, sys
from datetime import datetime
from pathlib import Path

# ============ 路径配置 ============

WIKI_ROOT = Path(__file__).parent.parent
HTML_PATH = WIKI_ROOT / '资料库 - 神通' / '02_加工产出' / '玄鑒仙族_中文百科全書.html'
PAGES_DIR = WIKI_ROOT / 'pages' / '人物与势力'
OUTPUT_DIR = WIKI_ROOT / 'output' / 'encyclopedia_parsed'
LOG_DIR = WIKI_ROOT / 'output' / 'logs'

# ============ 第一步：从 HTML 提取 sections JSON ============

def extract_sections_from_html(html_path):
    """从 HTML 文件中提取 const sections = [...] 的 JSON 数据"""
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 匹配 const sections = [...];
    match = re.search(r'const\s+sections\s*=\s*(\[.*?\]);\s*\n', content, re.DOTALL)
    if not match:
        # 尝试不带分号的匹配
        match = re.search(r'const\s+sections\s*=\s*(\[.*?\])\s*\n', content, re.DOTALL)
    if not match:
        print("❌ 无法从 HTML 中提取 sections JSON")
        sys.exit(1)

    json_str = match.group(1)
    sections = json.loads(json_str)
    print(f"✅ 成功提取 {len(sections)} 个 section 条目")
    return sections


# ============ 第二步：结构化解析角色条目 ============

def parse_character_entry(text):
    """
    从一行文本中解析角色信息
    格式示例:
      "李玄锋（叔）：筑基巅峰【镂金石·天金胄】，父李项平，母田芸，妻宁和棉，外室江渔女，箓气力贯千均。被青池徵调南疆..."
      "李通崖：筑基前期【浩瀚海】，父李木田，母柳林云，妻柳柔绚..."
    """
    entry = {}

    # 提取姓名（可能带括号标注脉系或道号）
    name_match = re.match(r'^([^：:（(]+?)(?:[（(]([^）)]+)[）)])?(?:[（(]([^）)]+)[）)])?[：:]', text)
    if not name_match:
        # 尝试无冒号的简单格式（如 "贺钧"）
        simple_match = re.match(r'^([^\s：:，。]+)', text)
        if simple_match:
            entry['姓名'] = simple_match.group(1).strip()
            entry['原文'] = text
            return entry
        return None

    entry['姓名'] = name_match.group(1).strip()
    # 括号内容可能是脉系（伯/仲/叔/季）或道号
    bracket_notes = []
    if name_match.group(2):
        bracket_notes.append(name_match.group(2).strip())
    if name_match.group(3):
        bracket_notes.append(name_match.group(3).strip())

    for note in bracket_notes:
        if note in ('伯', '仲', '叔', '季'):
            entry['脉系'] = note
        else:
            entry['道号'] = note

    # 冒号后的内容
    after_colon = text[name_match.end():].strip()

    # 提取修为（在【】之前的部分）
    cultivation_match = re.match(r'^([^【，。\n]+?)(?=【|，|。|$)', after_colon)
    if cultivation_match:
        cult_text = cultivation_match.group(1).strip()
        # 过滤掉非修为的内容（如"父xxx"开头的）
        if cult_text and not re.match(r'^[父母妻夫子女兄弟姐妹]', cult_text):
            # 常见修为关键词
            cult_keywords = ['紫府', '筑基', '练气', '灵初轮', '青元轮', '玉京轮',
                           '周行轮', '承明轮', '玄景轮', '凡人', '胎息', '道胎',
                           '法师', '怜愍', '大欲道']
            if any(kw in cult_text for kw in cult_keywords):
                entry['修为'] = cult_text

    # 提取仙基（【】内的内容）
    xianji_matches = re.findall(r'【([^】]+)】', after_colon)
    if xianji_matches:
        entry['仙基'] = '、'.join(xianji_matches)

    # 提取箓气
    luqi_match = re.search(r'箓气([^，。]+)', after_colon)
    if luqi_match:
        entry['箓气'] = luqi_match.group(1).strip()

    # 提取关系（父、母、妻、夫、子、女、兄、弟、妹、姐、师、徒等）
    relations = {}
    rel_patterns = [
        (r'(?<![大义])父([^，。、]+)', '父'),
        (r'(?<![姑])母([^，。、]+)', '母'),
        (r'妻([^，。、]+)', '妻'),
        (r'(?<![姐])夫([^，。、]+)', '夫'),
        (r'(?<![弟徒])子([^，。、]+)', '子'),
        (r'(?<![孙])女([^，。、]+)', '女'),
        (r'兄([^，。、]+)', '兄'),
        (r'(?<!师)弟(?!子)([^，。、]+)', '弟'),
        (r'妹([^，。、]+)', '妹'),
        (r'姐([^，。、]+)', '姐'),
        (r'(?<!弟)师(?!弟)([^，。、]+)', '师'),
        (r'徒([^，。、]+)', '徒'),
        (r'外室([^，。、]+)', '外室'),
        (r'外甥女([^，。、]+)', '外甥女'),
        (r'姑奶([^，。、]+)', '姑奶'),
        (r'姑姑([^，。、]+)', '姑姑'),
        (r'舅舅?([^，。、]+)', '舅'),
        (r'义父([^，。、]+)', '义父'),
        (r'大父([^，。、]+)', '大父'),
    ]
    for pattern, rel_type in rel_patterns:
        matches = re.findall(pattern, after_colon)
        if matches:
            # 清理人名（去掉多余描述）
            cleaned = []
            for m in matches:
                # 只取人名部分（2-4个汉字通常是人名）
                name_part = re.match(r'^[\u4e00-\u9fff]{1,5}', m.strip())
                if name_part:
                    cleaned.append(name_part.group(0))
            if cleaned:
                relations[rel_type] = cleaned

    if relations:
        entry['关系'] = relations

    # 提取事件/结局（最后的描述性文字）
    # 去掉已解析的关系和修为部分，剩余的是事件描述
    event_text = after_colon
    # 移除修为和仙基部分
    event_text = re.sub(r'^[^，]*【[^】]*】，?', '', event_text)
    # 移除关系描述
    event_text = re.sub(r'[父母妻夫子女兄弟姐妹师徒][\u4e00-\u9fff]{1,5}[，、]?', '', event_text)
    event_text = re.sub(r'外室[\u4e00-\u9fff]{1,5}[，、]?', '', event_text)
    event_text = re.sub(r'箓气[^，。]+[，。]?', '', event_text)
    # 清理开头的逗号
    event_text = re.sub(r'^[，、\s]+', '', event_text).strip()
    if event_text and len(event_text) > 2:
        entry['事件'] = event_text

    entry['原文'] = text
    return entry


def parse_sections_to_characters(sections):
    """
    将 sections 列表解析为结构化的角色数据
    返回: {角色名: {字段...}, ...}
    """
    characters = {}
    current_h2 = ''
    current_h3 = ''

    for item in sections:
        if item['type'] == 'h2':
            current_h2 = item['content']
            current_h3 = ''
        elif item['type'] == 'h3':
            current_h3 = item['content']
        elif item['type'] == 'text' and current_h2 in ('角色演员介绍', '势力'):
            # 跳过章节说明性文字
            if current_h3 == '' and current_h2 == '角色演员介绍':
                continue

            text = item['content'].strip()
            if not text:
                continue

            # 特殊处理：陆江仙的多行信息
            if current_h3 == '陆江仙' and '：' in text and len(text) < 50:
                # 这是陆江仙的属性行，合并处理
                if '陆江仙' not in characters:
                    characters['陆江仙'] = {
                        '姓名': '陆江仙',
                        '所属分组': current_h3,
                        '所属大类': current_h2,
                        '原文_lines': []
                    }
                characters['陆江仙']['原文_lines'].append(text)
                # 解析属性
                if text.startswith('身份：'):
                    characters['陆江仙']['身份'] = text[3:]
                elif text.startswith('境界：'):
                    characters['陆江仙']['修为'] = text[3:]
                elif text.startswith('道号：'):
                    characters['陆江仙']['道号'] = text[3:]
                elif text.startswith('仙器：'):
                    characters['陆江仙']['仙器'] = text[3:]
                elif text.startswith('当前状态：'):
                    characters['陆江仙']['当前状态'] = text[5:]
                continue
            elif current_h3 == '陆江仙' and text.startswith('简介：'):
                if '陆江仙' in characters:
                    characters['陆江仙']['事件'] = text[3:]
                    characters['陆江仙']['原文_lines'].append(text)
                continue
            elif current_h3 == '陆江仙' and '陆江仙' in characters and '金性果位' in text:
                characters['陆江仙']['原文_lines'].append(text)
                continue

            # 普通角色条目解析
            entry = parse_character_entry(text)
            if entry and '姓名' in entry:
                name = entry['姓名']
                entry['所属分组'] = current_h3
                entry['所属大类'] = current_h2

                # 推断所属势力
                if current_h2 == '势力':
                    entry['所属势力'] = current_h3
                elif '望姓' in current_h3:
                    entry['所属势力'] = current_h3.replace('望姓 ', '')
                elif current_h3 in ('小宗及支脉', '李家其他'):
                    entry['所属势力'] = '李家'
                elif '世' in current_h3 or current_h3 == '陆江仙':
                    entry['所属势力'] = '李家'

                # 推断世代
                gen_match = re.match(r'(七|八|九|十[一二三四五六]?)世', current_h3)
                if gen_match:
                    entry['世代'] = gen_match.group(0)

                # 处理重复角色（合并信息，保留所有分组）
                if name in characters:
                    existing = characters[name]
                    # 记录多重归属
                    if '多重归属' not in existing:
                        existing['多重归属'] = [existing.get('所属分组', '')]
                    existing['多重归属'].append(current_h3)
                    # 补充缺失字段
                    for key, val in entry.items():
                        if key not in existing or existing[key] == '':
                            existing[key] = val
                else:
                    characters[name] = entry

    print(f"✅ 解析出 {len(characters)} 个角色条目")
    return characters


# ============ 第三步：与现有 wiki 页面做 diff ============

def get_existing_pages(pages_dir):
    """获取现有 wiki 页面列表"""
    existing = {}
    if not pages_dir.exists():
        return existing

    for f in pages_dir.glob('*.wiki'):
        name = f.stem  # 文件名即角色名
        existing[name] = f
    return existing


def parse_existing_wiki_page(filepath):
    """解析现有 wiki 页面，提取模板字段和内容"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    page_data = {
        'raw': content,
        'template_fields': {},
        'has_relations': False,
        'has_faction': False,
        'categories': [],
    }

    # 提取 {{角色 ... }} 模板字段
    tmpl_match = re.search(r'\{\{角色\s*\n(.*?)\}\}', content, re.DOTALL)
    if tmpl_match:
        for line in tmpl_match.group(1).split('\n'):
            field_match = re.match(r'\|(.+?)=(.+)', line.strip())
            if field_match:
                page_data['template_fields'][field_match.group(1)] = field_match.group(2)

    # 检查是否已有人物关系章节
    if re.search(r'==+\s*人物关系\s*==+', content):
        page_data['has_relations'] = True

    # 检查是否已有所属势力字段
    if '所属势力' in content or '|势力=' in content or '|所属=' in content:
        page_data['has_faction'] = True

    # 提取分类
    page_data['categories'] = re.findall(r'\[\[Category:(.+?)\]\]', content)

    return page_data


def diff_characters_with_pages(characters, existing_pages):
    """
    对比解析出的角色与现有页面
    返回:
      - missing: 缺失的角色（需要新建页面）
      - to_supplement: 已有页面但可补充信息的角色
    """
    missing = {}
    to_supplement = {}

    for name, char_data in characters.items():
        if name in existing_pages:
            # 已有页面，检查是否需要补充
            page_data = parse_existing_wiki_page(existing_pages[name])
            supplements = {}

            # 检查是否需要补充关系
            if not page_data['has_relations'] and '关系' in char_data:
                supplements['关系'] = char_data['关系']

            # 检查是否需要补充所属势力
            if not page_data['has_faction'] and '所属势力' in char_data:
                supplements['所属势力'] = char_data['所属势力']

            # 检查模板字段是否缺失
            tmpl = page_data['template_fields']
            if '修为' not in tmpl and '修为' in char_data:
                supplements['修为'] = char_data['修为']
            if '仙基' not in tmpl and '仙基' in char_data:
                supplements['仙基'] = char_data['仙基']
            if '世代' not in tmpl and '字辈' not in tmpl and '世代' in char_data:
                supplements['世代'] = char_data['世代']

            if supplements:
                to_supplement[name] = {
                    'page_path': existing_pages[name],
                    'page_data': page_data,
                    'char_data': char_data,
                    'supplements': supplements,
                }
        else:
            missing[name] = char_data

    print(f"📊 对比结果:")
    print(f"   - 已有页面: {len(existing_pages)} 个")
    print(f"   - 百科角色: {len(characters)} 个")
    print(f"   - 缺失角色（需新建）: {len(missing)} 个")
    print(f"   - 可补充信息: {len(to_supplement)} 个")

    return missing, to_supplement


# ============ 第四步：补充已有页面 ============

def supplement_existing_page(name, supplement_info):
    """
    对已有页面进行补充（不覆盖已有内容）
    返回: (新内容, 变更描述列表)
    """
    page_data = supplement_info['page_data']
    char_data = supplement_info['char_data']
    supplements = supplement_info['supplements']
    content = page_data['raw']
    changes = []

    # 1. 补充模板字段
    tmpl_additions = []
    if '修为' in supplements:
        tmpl_additions.append(f"|修为={supplements['修为']}")
        changes.append(f"补充修为: {supplements['修为']}")
    if '仙基' in supplements:
        tmpl_additions.append(f"|仙基={supplements['仙基']}")
        changes.append(f"补充仙基: {supplements['仙基']}")
    if '世代' in supplements:
        tmpl_additions.append(f"|字辈={supplements['世代']}")
        changes.append(f"补充字辈: {supplements['世代']}")
    if '所属势力' in supplements:
        tmpl_additions.append(f"|所属={supplements['所属势力']}")
        changes.append(f"补充所属: {supplements['所属势力']}")

    if tmpl_additions:
        # 在 }} 之前插入新字段
        additions_str = '\n'.join(tmpl_additions)
        content = content.replace('}}', additions_str + '\n}}', 1)

    # 2. 补充人物关系章节
    if '关系' in supplements:
        relations = supplements['关系']
        rel_section = "\n\n===人物关系（百科补充）===\n\n"
        for rel_type, names in relations.items():
            for n in names:
                rel_section += f"* {rel_type}：[[{n}]]\n"
        changes.append(f"补充人物关系: {relations}")

        # 在 [[Category: 之前插入
        cat_pos = content.find('[[Category:')
        if cat_pos > 0:
            content = content[:cat_pos] + rel_section + '\n' + content[cat_pos:]
        else:
            content += rel_section

    return content, changes


# ============ 第五步：生成新页面 ============

def generate_new_page(name, char_data):
    """为缺失角色生成新的 wiki 页面"""
    lines = []

    # 模板
    tmpl_fields = []
    if '修为' in char_data:
        tmpl_fields.append(f"|修为={char_data['修为']}")
    if '仙基' in char_data:
        tmpl_fields.append(f"|仙基={char_data['仙基']}")
    if '所属势力' in char_data:
        tmpl_fields.append(f"|所属={char_data['所属势力']}")
    if '世代' in char_data:
        tmpl_fields.append(f"|字辈={char_data['世代']}")
    if '脉系' in char_data:
        tmpl_fields.append(f"|族系={char_data['脉系']}脉")
    if '道号' in char_data:
        tmpl_fields.append(f"|道号={char_data['道号']}")
    if '箓气' in char_data:
        tmpl_fields.append(f"|箓气={char_data['箓气']}")

    lines.append("{{角色")
    for field in tmpl_fields:
        lines.append(field)
    lines.append("}}")
    lines.append("")

    # 简介
    if '事件' in char_data:
        lines.append(f"{name}，{char_data.get('事件', '')}")
    else:
        # 用原文作为简介
        original = char_data.get('原文', '')
        if original:
            lines.append(f"{original}")
    lines.append("")

    # 人物关系
    if '关系' in char_data:
        lines.append("===人物关系===")
        lines.append("")
        for rel_type, names in char_data['关系'].items():
            for n in names:
                lines.append(f"* {rel_type}：[[{n}]]")
        lines.append("")

    # 分类
    lines.append("---")
    lines.append("")
    lines.append("[[Category:角色]]")

    # 根据所属势力添加分类
    if '所属势力' in char_data:
        faction = char_data['所属势力']
        lines.append(f"[[Category:{faction}]]")

    # 根据世代添加分类
    if '世代' in char_data:
        lines.append(f"[[Category:{char_data['世代']}角色]]")

    return '\n'.join(lines)


# ============ 主流程 ============

def main():
    print("=" * 60)
    print("  玄鉴仙族百科全书 HTML 解析器")
    print("=" * 60)
    print()

    # 确保输出目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # 第一步：提取 JSON
    print("📖 第一步：从 HTML 提取 sections JSON...")
    sections = extract_sections_from_html(HTML_PATH)

    # 保存原始 JSON（供调试）
    json_output = OUTPUT_DIR / 'sections_raw.json'
    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump(sections, f, ensure_ascii=False, indent=2)
    print(f"   → 已保存原始 JSON: {json_output}")
    print()

    # 第二步：结构化解析
    print("🔍 第二步：结构化解析角色条目...")
    characters = parse_sections_to_characters(sections)

    # 保存解析结果
    chars_output = OUTPUT_DIR / 'characters_parsed.json'
    # 清理不可序列化的字段
    chars_serializable = {}
    for name, data in characters.items():
        clean = {k: v for k, v in data.items() if k != 'page_data'}
        chars_serializable[name] = clean
    with open(chars_output, 'w', encoding='utf-8') as f:
        json.dump(chars_serializable, f, ensure_ascii=False, indent=2)
    print(f"   → 已保存解析结果: {chars_output}")
    print()

    # 第三步：与现有页面做 diff
    print("📊 第三步：与现有 wiki 页面做 diff...")
    existing_pages = get_existing_pages(PAGES_DIR)
    missing, to_supplement = diff_characters_with_pages(characters, existing_pages)
    print()

    # 第四步：补充已有页面
    print("✏️  第四步：补充已有页面...")
    supplement_dir = OUTPUT_DIR / 'supplemented'
    supplement_dir.mkdir(parents=True, exist_ok=True)

    changelog = []
    changelog.append(f"# 百科全书数据补充记录")
    changelog.append(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    changelog.append(f"# 数据源: {HTML_PATH.name}")
    changelog.append("")
    changelog.append(f"## 统计")
    changelog.append(f"- 百科角色总数: {len(characters)}")
    changelog.append(f"- 已有 wiki 页面: {len(existing_pages)}")
    changelog.append(f"- 需新建页面: {len(missing)}")
    changelog.append(f"- 已补充页面: {len(to_supplement)}")
    changelog.append("")

    supplemented_count = 0
    changelog.append("## 已补充的页面")
    changelog.append("")

    for name, info in to_supplement.items():
        new_content, changes = supplement_existing_page(name, info)
        if changes:
            # 写入补充后的页面到输出目录（不直接覆盖原文件）
            out_path = supplement_dir / f"{name}.wiki"
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            supplemented_count += 1

            changelog.append(f"### {name}")
            for c in changes:
                changelog.append(f"  - {c}")
            changelog.append("")

    print(f"   → 已补充 {supplemented_count} 个页面（输出到 {supplement_dir}）")
    print()

    # 第五步：生成缺失角色的新页面
    print("📝 第五步：生成缺失角色的新页面...")
    new_pages_dir = OUTPUT_DIR / 'new_pages'
    new_pages_dir.mkdir(parents=True, exist_ok=True)

    changelog.append("## 新建的页面")
    changelog.append("")

    for name, char_data in missing.items():
        page_content = generate_new_page(name, char_data)
        out_path = new_pages_dir / f"{name}.wiki"
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(page_content)
        changelog.append(f"- {name} ({char_data.get('修为', '未知')})")

    print(f"   → 已生成 {len(missing)} 个新页面（输出到 {new_pages_dir}）")
    print()

    # 保存变更日志
    log_path = LOG_DIR / f"encyclopedia_supplement_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(changelog))
    print(f"📋 变更日志已保存: {log_path}")
    print()

    # 最终总结
    print("=" * 60)
    print("  处理完成！")
    print("=" * 60)
    print()
    print("⚠️  注意事项:")
    print("  1. 补充后的页面保存在 output/encyclopedia_parsed/supplemented/")
    print("  2. 新建的页面保存在 output/encyclopedia_parsed/new_pages/")
    print("  3. 请人工审核后再将文件复制到 pages/人物与势力/ 目录")
    print("  4. 变更日志记录了所有修改，供后续校正参考")
    print()
    print("📌 后续操作:")
    print("  - 审核补充内容是否准确")
    print("  - 将确认无误的页面复制到 pages/人物与势力/")
    print("  - 使用 upload_pages.py 上传到 wiki")


if __name__ == '__main__':
    main()
