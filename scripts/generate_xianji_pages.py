#!/usr/bin/env python3
"""生成并上传仙基/道统/神通独立 Wiki 页面。"""
import argparse
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings()

ROOT = Path('/Users/leoshi/AIBOOK/xuanjian/wiki')
JSON_PATH = ROOT / '资料库 - 神通/04_参考权威/玄鉴仙族_五德位业体系_结构化.json'
AUTHORITY_PATH = ROOT / '资料库 - 神通/04_参考权威/玄鉴仙族_神通仙基汇总.md'
PAGES_DIR = ROOT / 'pages'
API = 'http://leoshixie.devcloud.woa.com/api.php'
USER = 'WikiAdmin'
PASSWORD = 'XuanjianAdmin2026'

TOP_SECTIONS = [
    ('一、阴阳', ['阴阳（五阳）', '五阴']),
    ('二、五德', ['金德', '木德', '水德', '火德', '土德']),
    ('三、十二炁', ['十二炁']),
    ('四、三雷', ['三雷']),
    ('五、并古', ['三巫', '二祝', '并古']),
    ('六、独立与其他', ['独立']),
]
SYSTEM_LABEL = {
    '阴阳（五阳）': '阳', '五阴': '阴',
    '金德': '金德', '木德': '木德', '水德': '水德', '火德': '火德', '土德': '土德',
    '十二炁': '十二炁', '三雷': '三雷', '三巫': '三巫', '二祝': '二祝',
    '并古': '素德其余', '独立': '独立',
}
FIELD_LABELS = [
    ('位置类型', '位置'), ('司辰', '司辰'), ('意象', '意象'), ('外在表现', '外在表现'),
    ('权柄特征', '权柄特征'), ('道统关系/克制关系', '道统关系'), ('金性/金位名', '金性/金位名'),
    ('金位现状/闰走', '金位现状'), ('金位历史', '金位历史'), ('位别', '位别'),
]
EMPTY = {'', '—', '-', '暂无', '无', None}


def clean(value):
    if value is None:
        return ''
    return re.sub(r'\s+', ' ', str(value).strip())


def cell(value):
    value = clean(value)
    if not value or value in EMPTY:
        return '—'
    return value.replace('\n', '<br>')


def title_safe(value):
    value = clean(value).replace('/', '／')
    value = value.replace(':', '：')
    return value


def wiki_link(title, label=None):
    title = title_safe(title)
    label = clean(label) if label is not None else title
    return f'[[{title}|{label}]]' if label != title else f'[[{title}]]'


def visible_name(pos):
    return clean(pos.get('位置名称') or pos.get('道统') or '未命名')


def dao_name(pos):
    return clean(pos.get('道统') or visible_name(pos))


def dao_title(pos_or_name):
    name = dao_name(pos_or_name) if isinstance(pos_or_name, dict) else clean(pos_or_name)
    return '道统-' + title_safe(name)


def shentong_title(name):
    return '神通-' + title_safe(name)


def position_type_name(value):
    value = clean(value)
    if not value or value in EMPTY:
        return ''
    value = re.sub(r'^附[：:]', '', value)
    value = re.sub(r'[（(].*?[）)]', '', value)
    return value.strip()


def position_title(value):
    return '位业-' + title_safe(position_type_name(value))


def short_name(name):
    name = re.sub(r'^\d+(?:\.\d+)?\s*', '', clean(name))
    return name.split('（', 1)[0].split('(', 1)[0].split('·', 1)[0].strip()


def norm(name):
    return short_name(name).replace(' ', '')


def split_names(value):
    value = clean(value)
    if not value or value in EMPTY:
        return []
    value = value.replace('→', '/').replace('／', '/').replace('、', '/')
    out = []
    for part in value.split('/'):
        part = part.strip()
        if part and part not in EMPTY and part not in {'✓', '?', '替参', '备注'}:
            out.append(part)
    return out


def shentong_rows(pos):
    rows = []
    for item in pos.get('神通', []):
        name = clean(item.get('神通名称'))
        if name and name not in EMPTY:
            rows.append(item)
    return rows


def parse_authority(text):
    authority = {}
    gold = {}
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        m = re.match(r'^(#{3,4})\s+(.+)$', line)
        if m:
            current = short_name(m.group(2))
            authority.setdefault(norm(current), set())
            continue
        if current and line.startswith('> 金性:'):
            gold[norm(current)] = line.split('金性:', 1)[1].strip()
            continue
        if not current or not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if not cells or set(cells[0]) <= {'-'} or cells[0] in {'神通', '体系', '仙基'}:
            continue
        for idx in (0, 1):
            if idx < len(cells):
                for name in split_names(cells[idx]):
                    authority.setdefault(norm(current), set()).add(norm(name))
    return authority, gold


def authority_set(pos, state):
    keys = {norm(dao_name(pos)), norm(visible_name(pos))}
    found = set()
    for key in keys:
        found |= state['authority'].get(key, set())
    return found


def shentong_status(pos, item, state):
    auth = authority_set(pos, state)
    if not auth:
        return '汇总未列'
    name = norm(item.get('神通名称', ''))
    aliases = {norm(x) for x in split_names(item.get('下位/古称/别称', ''))}
    if name in auth:
        return '已收录'
    if aliases & auth:
        return '别名匹配'
    return '补充/待复核'


def auth_status(pos, state):
    rows = shentong_rows(pos)
    if not rows:
        return '无神通条目'
    auth = authority_set(pos, state)
    if not auth:
        return '汇总未列'
    matched = sum(1 for row in rows if norm(row.get('神通名称', '')) in auth)
    if matched == len(rows):
        return '全量匹配'
    if matched:
        return f'部分匹配 {matched}/{len(rows)}'
    return '待复核'


def gold_for(pos, state):
    for key in (norm(dao_name(pos)), norm(visible_name(pos))):
        if key in state['gold']:
            return state['gold'][key]
    raw = clean(pos.get('金性/金位名'))
    if raw and raw not in EMPTY and ('性' in raw or '｛' in raw):
        return raw
    return ''


def load_data():
    data = json.loads(JSON_PATH.read_text(encoding='utf-8'))
    authority, gold = parse_authority(AUTHORITY_PATH.read_text(encoding='utf-8'))
    return data, {'authority': authority, 'gold': gold}


def iter_positions(data):
    for system in data['体系列表']:
        for pos in system.get('位置列表', []):
            yield system['体系名称'], pos


def build_indexes(data):
    dao_entries = defaultdict(list)
    shentong_entries = defaultdict(list)
    position_entries = defaultdict(list)
    for system_name, pos in iter_positions(data):
        dao_entries[dao_title(pos)].append((system_name, pos))
        ptype = position_type_name(pos.get('位置类型'))
        if ptype:
            position_entries[position_title(ptype)].append((system_name, pos))
        for item in shentong_rows(pos):
            shentong_entries[shentong_title(item['神通名称'])].append((system_name, pos, item))
    return dao_entries, shentong_entries, position_entries


def add_shentong_table(lines, pos, state, linked=True):
    rows = shentong_rows(pos)
    if not rows:
        lines += ['暂无已知神通条目。', '']
        return
    lines += ['{| class="wikitable sortable"', '|-', '! 神通 !! 类别 !! 下位／古称／别称／替参 !! 校验']
    for item in rows:
        name = clean(item.get('神通名称'))
        name_text = wiki_link(shentong_title(name), name) if linked else name
        lines += ['|-', '| ' + ' || '.join([
            cell(name_text), cell(item.get('神通类别')), cell(item.get('下位/古称/别称')), cell(shentong_status(pos, item, state))
        ])]
    lines += ['|}', '']


def add_details(lines, pos, state, linked_position=True):
    gold = gold_for(pos, state)
    if gold:
        lines += [f': <span style="color:#8b5a2b;font-style:italic">金性: {cell(gold)}</span>', '']
    lines.append("'''位业详情'''")
    for key, label in FIELD_LABELS:
        val = clean(pos.get(key))
        if not val or val in EMPTY or '文档整理完毕' in val or val.startswith('### '):
            continue
        if key == '金性/金位名' and gold and val == gold:
            continue
        if key == '位置类型' and linked_position:
            ptype = position_type_name(val)
            val = wiki_link(position_title(ptype), ptype) if ptype else val
        lines += [f'; {label}', f': {cell(val)}']
    lines += ['; 汇总校验', ': ' + auth_status(pos, state), '']


def generate_overview(data, state):
    systems = {s['体系名称']: s for s in data['体系列表']}
    source_title = clean(data.get('元数据', {}).get('标题', '《玄鉴仙族》五德位业体系梳理'))
    lines = [
        '{{导航栏}}', '',
        "'''仙基与道统'''收录《玄鉴仙族》中已知仙基、道统、神通、位业与金位信息。", '',
        f'本页由结构化资料生成，主数据源为{source_title}，校验源为《玄鉴仙族·神通仙基汇总》（崇宫白 B 站专栏 cv41820802，2026-05-04）。', '',
        '说明：神通表中的“校验”表示该神通名是否能在汇总校验源中找到；“补充/待复核”表示来自主结构化数据，但未在汇总源中完全匹配。', '',
        '__TOC__', '',
    ]
    seen_titles = set()
    for top_title, sys_names in TOP_SECTIONS:
        lines += [f'== {top_title} ==', '']
        for sys_name in sys_names:
            system = systems.get(sys_name)
            if not system:
                continue
            label = SYSTEM_LABEL.get(sys_name, sys_name)
            if len(sys_names) > 1 or top_title in {'二、五德', '五、并古'}:
                lines += [f'=== {label} ===', '']
                level = 4
            else:
                level = 3
            for pos in system.get('位置列表', []):
                title = visible_name(pos)
                if title in seen_titles:
                    suffix = position_type_name(pos.get('位置类型')) or dao_name(pos) or '补充'
                    title = f'{title}（{suffix}）'
                seen_titles.add(title)
                mark = '=' * level
                lines += [f'{mark} {title} {mark}', '', f'主页面：{wiki_link(dao_title(pos), dao_name(pos))}', '']
                add_shentong_table(lines, pos, state, linked=True)
                lines.append('----')
                add_details(lines, pos, state, linked_position=True)
    lines += ['== 七、统计总览 ==', '', '{| class="wikitable sortable"', '|-', '! 体系 !! 位置数 !! 神通数 !! 道统/位置']
    for system in data['体系列表']:
        positions = system.get('位置列表', [])
        names = '、'.join(wiki_link(dao_title(pos), visible_name(pos)) for pos in positions)
        count = sum(len(shentong_rows(pos)) for pos in positions)
        lines += ['|-', f'| {cell(system["体系名称"])} || {len(positions)} || {count} || {names}']
    total_pos = sum(len(s.get('位置列表', [])) for s in data['体系列表'])
    total_st = sum(len(shentong_rows(pos)) for _, pos in iter_positions(data))
    lines += ['|}', '', f'全表合计：{len(data["体系列表"])} 个体系，{total_pos} 个位置/道统，{total_st} 条神通记录。', '', '[[Category:修炼体系]]', '']
    return '\n'.join(lines)


def generate_dao_page(title, entries, state):
    system_name, pos = entries[0]
    name = dao_name(pos)
    ptype = position_type_name(pos.get('位置类型'))
    lines = ['{{导航栏}}', '', f"'''{name}'''是《玄鉴仙族》中的道统/仙基体系之一。", '', '== 基本信息 ==', '', '{| class="wikitable"', '|-', '! 字段 !! 内容']
    rows = [
        ('体系', system_name),
        ('道统', name),
        ('位置类型', wiki_link(position_title(ptype), ptype) if ptype else '—'),
        ('总览', wiki_link('仙基与道统')),
    ]
    for label, value in rows:
        lines += ['|-', f'| {label} || {cell(value)}']
    lines += ['|}', '']
    add_shentong_table(lines, pos, state, linked=True)
    lines.append('== 位业详情 ==')
    lines.append('')
    add_details(lines, pos, state, linked_position=True)
    lines += ['== 相关页面 ==', '', f'* {wiki_link("仙基与道统")}', f'* {wiki_link(position_title(ptype), ptype) if ptype else "—"}', '', '[[Category:道统]]', '[[Category:修炼体系]]', f'[[Category:{system_name}]]', '']
    return '\n'.join(lines)


def generate_shentong_page(title, entries):
    name = title.removeprefix('神通-')
    lines = ['{{导航栏}}', '', f"'''{name}'''是《玄鉴仙族》中的神通条目。", '', '== 基本信息 ==', '', '{| class="wikitable sortable"', '|-', '! 所属体系 !! 所属道统 !! 位置类型 !! 类别 !! 下位／古称／别称／替参']
    for system_name, pos, item in entries:
        ptype = position_type_name(pos.get('位置类型'))
        ptype_link = wiki_link(position_title(ptype), ptype) if ptype else '—'
        lines += ['|-', '| ' + ' || '.join([
            cell(system_name), wiki_link(dao_title(pos), dao_name(pos)), cell(ptype_link), cell(item.get('神通类别')), cell(item.get('下位/古称/别称'))
        ])]
    lines += ['|}', '']
    lines += ['== 所属道统摘要 ==', '']
    for system_name, pos, item in entries:
        lines += [f'=== {dao_name(pos)} ===', '', f'* 所属体系：{system_name}', f'* 道统页面：{wiki_link(dao_title(pos), dao_name(pos))}']
        relation = clean(pos.get('道统关系/克制关系'))
        feature = clean(pos.get('权柄特征'))
        if feature and feature not in EMPTY:
            lines += [f'* 权柄特征：{cell(feature)}']
        if relation and relation not in EMPTY:
            lines += [f'* 道统关系：{cell(relation)}']
        lines.append('')
    lines += ['== 相关页面 ==', '', f'* {wiki_link("仙基与道统")}']
    for _, pos, _ in entries:
        lines.append(f'* {wiki_link(dao_title(pos), dao_name(pos))}')
    lines += ['', '[[Category:神通]]', '[[Category:修炼体系]]']
    for system_name, _, _ in entries:
        lines.append(f'[[Category:{system_name}]]')
    lines.append('')
    return '\n'.join(lines)


def generate_position_page(title, entries):
    name = title.removeprefix('位业-')
    lines = ['{{导航栏}}', '', f"'''{name}'''是《玄鉴仙族》仙基/道统体系中的位置类型。", '', '== 包含道统 ==', '', '{| class="wikitable sortable"', '|-', '! 体系 !! 道统 !! 代表神通']
    for system_name, pos in entries:
        st_links = '、'.join(wiki_link(shentong_title(item['神通名称']), item['神通名称']) for item in shentong_rows(pos)[:5]) or '—'
        lines += ['|-', '| ' + ' || '.join([cell(system_name), wiki_link(dao_title(pos), dao_name(pos)), st_links])]
    lines += ['|}', '', '== 相关页面 ==', '', f'* {wiki_link("仙基与道统")}', '', '[[Category:位业]]', '[[Category:修炼体系]]', '']
    return '\n'.join(lines)


def validate_page(title, text):
    if text.count('{|') != text.count('|}'):
        raise ValueError(f'{title}: table mismatch')
    headings = re.findall(r'^(=+)\s*(.*?)\s*\1\s*$', text, re.M)
    if any(not h[1].strip() for h in headings):
        raise ValueError(f'{title}: empty heading')
    if '\u6682\u77bb\u8eab' in text:
        raise ValueError(f'{title}: old term remains')


def build_pages(data, state):
    dao_entries, shentong_entries, position_entries = build_indexes(data)
    pages = {'仙基与道统': generate_overview(data, state)}
    for title, entries in sorted(position_entries.items()):
        pages[title] = generate_position_page(title, entries)
    for title, entries in sorted(dao_entries.items()):
        pages[title] = generate_dao_page(title, entries, state)
    for title, entries in sorted(shentong_entries.items()):
        pages[title] = generate_shentong_page(title, entries)
    for title, text in pages.items():
        validate_page(title, text)
    return pages, dao_entries, shentong_entries, position_entries


def page_path(title):
    safe_title = title_safe(title)
    if title == '仙基与道统':
        return PAGES_DIR / '仙基道统' / f'{safe_title}.wiki'
    if title.startswith('位业-'):
        return PAGES_DIR / '仙基道统' / '位业' / f'{safe_title}.wiki'
    if title.startswith('道统-'):
        return PAGES_DIR / '仙基道统' / '道统' / f'{safe_title}.wiki'
    if title.startswith('神通-'):
        return PAGES_DIR / '仙基道统' / '神通' / f'{safe_title}.wiki'
    return PAGES_DIR / f'{safe_title}.wiki'


def write_pages(pages):
    for title, text in pages.items():
        path = page_path(title)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')


def existing_titles():
    return {path.stem for path in PAGES_DIR.rglob('*.wiki')}


def upload_pages(pages):
    session = requests.Session()
    login_token = session.get(API, params={'action': 'query', 'meta': 'tokens', 'type': 'login', 'format': 'json'}, verify=False, timeout=20).json()['query']['tokens']['logintoken']
    login = session.post(API, data={'action': 'clientlogin', 'format': 'json', 'username': USER, 'password': PASSWORD, 'logintoken': login_token, 'loginreturnurl': 'http://leoshixie.devcloud.woa.com/wiki/首页'}, verify=False, timeout=20).json()
    if login.get('clientlogin', {}).get('status') != 'PASS':
        raise RuntimeError('login failed: ' + json.dumps(login, ensure_ascii=False))
    csrf = session.get(API, params={'action': 'query', 'meta': 'tokens', 'format': 'json'}, verify=False, timeout=20).json()['query']['tokens']['csrftoken']
    success = 0
    failures = []
    for index, (title, text) in enumerate(sorted(pages.items()), 1):
        response = session.post(API, data={
            'action': 'edit', 'format': 'json', 'title': title, 'text': text,
            'summary': '生成仙基/道统/神通独立页面', 'token': csrf, 'bot': '1',
        }, verify=False, timeout=60).json()
        if response.get('edit', {}).get('result') == 'Success':
            success += 1
        else:
            failures.append((title, response))
        if index % 50 == 0:
            print(f'uploaded {index}/{len(pages)}', flush=True)
        time.sleep(0.05)
    session.post(API, data={'action': 'purge', 'format': 'json', 'titles': '|'.join(list(pages)[:50]), 'forcelinkupdate': '1'}, verify=False, timeout=30)
    return success, failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--upload', action='store_true')
    args = parser.parse_args()

    data, state = load_data()
    pages, dao_entries, shentong_entries, position_entries = build_pages(data, state)
    planned = set(pages)
    overwrites = sorted(planned & existing_titles())
    duplicate_shentong_records = {title: len(entries) for title, entries in shentong_entries.items() if len(entries) > 1}
    summary = {
        'planned_pages': len(pages),
        'overview_pages': 1,
        'position_pages': len(position_entries),
        'dao_pages': len(dao_entries),
        'shentong_pages': len(shentong_entries),
        'overwritten_existing_pages': len(overwrites),
        'duplicate_shentong_pages': duplicate_shentong_records,
    }
    if args.write or args.upload:
        write_pages(pages)
        summary['written_pages'] = len(pages)
    if args.upload:
        success, failures = upload_pages(pages)
        summary['uploaded_pages'] = success
        summary['upload_failures'] = failures[:5]
        if failures:
            raise SystemExit(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
