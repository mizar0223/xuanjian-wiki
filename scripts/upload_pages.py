#!/usr/bin/env python3
"""批量上传本地 .wiki 页面到 MediaWiki。

默认递归上传 `pages/` 下所有 .wiki 文件。
页面标题 = 前缀 + 文件名 stem。

前缀规则（重要）：
  - 通过 --prefix-map（或内置 DEFAULT_PREFIX_MAP）按"目录名→前缀"精确白名单匹配。
  - 命中目录名的文件使用对应前缀；未命中的使用 --prefix（默认空字符串，即不加前缀）。
  - 仙基道统/索引/人物与势力 维度：文件 stem 已自带 "道统-"/"神通-"/"位业-"/"人物-" 类语义前缀，
    因此对应目录前缀均为 ""，避免出现 "造物-道统-XXX" 这种双前缀错误。
  - 造物维度（资料库/造物/pages/）：已统一去前缀，页面标题直接用文件名 stem，不加 "造物-" 前缀。

例：
  python3 upload_pages.py --only pages/仙基道统           # 自动空前缀
  python3 upload_pages.py --only "资料库/造物/pages"      # 造物也已无前缀

可用 `--only` 指定一个或多个目录/文件进行局部上传。
"""

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

import requests
import urllib3

from common.config import AppConfig, require_wiki_password

urllib3.disable_warnings()

CONFIG = AppConfig()
ROOT = CONFIG.project_root
DEFAULT_PAGES_DIR = CONFIG.pages_dir
WIKI_API = CONFIG.wiki_api
WIKI_USER = CONFIG.wiki_user
WIKI_URL = CONFIG.wiki_url or 'http://9433.com.cn/wiki/'
MAX_RETRIES = 3
BOT_SUMMARY_PREFIX = '[bot]'


class WikiSession:
    def __init__(self):
        self.s = requests.Session()
        self.csrf = None

    def login(self):
        password = require_wiki_password(CONFIG)
        r1 = self.s.get(WIKI_API, params={
            'action': 'query', 'meta': 'tokens', 'type': 'login', 'format': 'json'
        }, verify=False, timeout=20)
        login_token = r1.json()['query']['tokens']['logintoken']

        r2 = self.s.post(WIKI_API, data={
            'action': 'clientlogin', 'format': 'json',
            'username': WIKI_USER, 'password': password,
            'logintoken': login_token,
            'loginreturnurl': WIKI_URL.rstrip('/') + '/首页'
        }, verify=False, timeout=20)
        result = r2.json()
        if result.get('clientlogin', {}).get('status') != 'PASS':
            raise RuntimeError(f'Login failed: {result}')
        print(f"Logged in as {result['clientlogin']['username']}")
        self.refresh_csrf()

    def refresh_csrf(self):
        r = self.s.get(WIKI_API, params={
            'action': 'query', 'meta': 'tokens', 'format': 'json'
        }, verify=False, timeout=20)
        self.csrf = r.json()['query']['tokens']['csrftoken']

    def _revision_content(self, revision):
        if '*' in revision:
            return revision['*']
        return revision.get('slots', {}).get('main', {}).get('*', '')

    def get_page_revision(self, title):
        r = self.s.get(WIKI_API, params={
            'action': 'query',
            'prop': 'revisions',
            'rvprop': 'ids|timestamp|user|comment|content',
            'rvslots': 'main',
            'titles': title,
            'format': 'json',
        }, verify=False, timeout=20)
        pages = r.json()['query']['pages']
        page = list(pages.values())[0]
        if 'missing' in page:
            return {'exists': False, 'content': None}
        revision = page.get('revisions', [{}])[0]
        return {
            'exists': True,
            'revid': revision.get('revid'),
            'timestamp': revision.get('timestamp'),
            'user': revision.get('user'),
            'comment': revision.get('comment', ''),
            'content': self._revision_content(revision),
        }

    def upload_page(self, title, text, summary, baserevid=None):
        for attempt in range(MAX_RETRIES):
            try:
                data = {
                    'action': 'edit', 'format': 'json',
                    'title': title, 'text': text,
                    'summary': summary,
                    'token': self.csrf,
                    'bot': '1',
                }
                if baserevid:
                    data['baserevid'] = str(baserevid)
                r = self.s.post(WIKI_API, data=data, verify=False, timeout=60)
                result = r.json()
                if 'error' in result:
                    if result['error'].get('code') == 'badtoken':
                        self.refresh_csrf()
                        continue
                    return False, result['error'].get('info', str(result['error']))
                edit = result.get('edit', {})
                if edit.get('result') == 'Success':
                    return True, f"rev:{edit.get('newrevid', edit.get('oldrevid', '?'))}"
                return False, str(edit)
            except Exception as exc:
                if attempt >= MAX_RETRIES - 1:
                    return False, str(exc)
                time.sleep(2)
        return False, 'Max retries exceeded'


def resolve_path(value):
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path

# ========== 前缀映射默认值 ==========
# 将本地子目录名映射到 wiki 页面标题前缀。
# 关键原则：目录里文件 stem 若已自带语义前缀（如 "道统-XXX"），就不要再加前缀。
DEFAULT_PREFIX_MAP = {
    # 人物维度（pages/ 下）—— stem 是裸名，需要加 "人物-"
    '人物与势力': '人物-',        # pages/人物与势力/

    # 仙基道统维度 —— stem 已自带 "道统-"/"神通-"/"位业-" 前缀，不再加前缀
    '仙基道统': '',
    '道统': '',
    '神通': '',
    '位业': '',

    # 索引页 —— 直接用 stem，无前缀
    '索引': '',

    # 造物维度 —— 已统一去前缀（2026-05-12），页面标题直接用 stem
    '造物': '',
    'pages': '',               # 资料库/造物/pages/ 的子目录命中
    '00-体系': '',
    '01-灵气': '',
    '02-灵物': '',
    '03-灵资': '',
    '04-丹药': '',
    '05-法器': '',
    '06-灵器': '',
    '07-灵宝': '',
    '08-法宝': '',
    '09-位别': '',
    '10-仙器': '',
    '11-符箓': '',
    '12-材料': '',
    '13-法术秘法': '',
    '14-待分类': '',
}

def build_prefix_map(args):
    """根据命令行参数构建 (目录名→前缀) 字典和默认前缀。"""
    if args.no_prefix:
        return {}, ''
    prefix_map = dict(DEFAULT_PREFIX_MAP)
    if args.prefix_map:
        user_map = json.loads(args.prefix_map)
        prefix_map.update(user_map)
    default_prefix = args.prefix
    return prefix_map, default_prefix


def get_page_title(path, pages_root, prefix_map, default_prefix):
    """根据文件路径和前缀映射，生成 wiki 页面标题。

    规则：
      1. 在文件路径的所有层级中查找 prefix_map 的键
      2. 命中则用对应前缀 + stem
      3. 未命中则尝试 relative_to pages_root，取第一级子目录查 prefix_map
      4. 最终 fallback 用 default_prefix + stem
    """
    stem = path.stem

    # 方法1: 在路径组件中直接查找已知的目录名
    for part in path.parts:
        if part in prefix_map:
            return prefix_map[part] + stem

    # 方法2: 通过 relative_to 获取子目录
    try:
        rel = path.relative_to(pages_root)
        parts = rel.parts
        if len(parts) > 1:
            subdir = parts[0]
            if subdir in prefix_map:
                return prefix_map[subdir] + stem
    except ValueError:
        pass

    return default_prefix + stem


def collect_wiki_files(base_dir, only_paths, recursive):
    targets = [resolve_path(p) for p in only_paths] if only_paths else [base_dir]
    files = []
    for target in targets:
        if target.is_file():
            if target.suffix == '.wiki':
                files.append(target)
            continue
        if not target.exists():
            raise FileNotFoundError(f'路径不存在: {target}')
        pattern = '**/*.wiki' if recursive else '*.wiki'
        files.extend(target.glob(pattern))
    return sorted(set(files))


def validate_files(files, pages_root=None, prefix_map=None, default_prefix=''):
    """校验页面：标题去重 + 表格闭合检查。"""
    if pages_root and prefix_map is not None:
        titles = [get_page_title(p, pages_root, prefix_map, default_prefix) for p in files]
    else:
        titles = [path.stem for path in files]
    duplicates = sorted(title for title, count in Counter(titles).items() if count > 1)
    if duplicates:
        raise ValueError('发现重复页面标题: ' + ', '.join(duplicates[:50]))

    bad_tables = []
    for path in files:
        text = path.read_text(encoding='utf-8')
        if text.count('{|') != text.count('|}'):
            bad_tables.append(str(path))
    if bad_tables:
        raise ValueError('发现表格未闭合文件: ' + ', '.join(bad_tables[:20]))


def parse_args():
    parser = argparse.ArgumentParser(description='上传本地 .wiki 页面到 MediaWiki')
    parser.add_argument('--dir', default=str(DEFAULT_PAGES_DIR), help='页面根目录，默认 pages/')
    parser.add_argument('--only', action='append', default=[], help='只上传指定目录或文件；可重复传入')
    parser.add_argument('--no-recursive', action='store_true', help='不递归扫描子目录')
    parser.add_argument('--dry-run', action='store_true', help='只预览，不上传')
    parser.add_argument('--delay', type=float, default=0.05, help='每次编辑间隔秒数，默认 0.05')
    parser.add_argument('--limit', type=int, default=0, help='最多上传 N 个页面，默认不限制')
    parser.add_argument('--skip-validate', action='store_true', help='跳过重复标题和表格闭合校验')
    parser.add_argument('--summary', default='批量上传本地 wiki 页面', help='编辑摘要')
    parser.add_argument('--force', action='store_true', help='强制覆盖远端不同内容')
    parser.add_argument('--bot-summary-prefix', default=BOT_SUMMARY_PREFIX, help='识别脚本编辑的摘要前缀')
    parser.add_argument('--conflict-log', default='/tmp/wiki_upload_conflicts.json', help='冲突日志路径')
    parser.add_argument('--prefix', default='', help='默认页面标题前缀（未命中 prefix_map 时使用）。默认空字符串，造物维度需显式传 --prefix=造物-')
    parser.add_argument('--prefix-map', default=None, help='目录→前缀映射JSON，如 \'{"20-人物":"人物-"}\'')
    parser.add_argument('--no-prefix', action='store_true', help='禁用前缀，直接用 stem 作标题（兼容旧行为）')
    return parser.parse_args()


def main():
    args = parse_args()
    base_dir = resolve_path(args.dir)
    recursive = not args.no_recursive

    # 构建前缀映射
    prefix_map, default_prefix = build_prefix_map(args)

    try:
        wiki_files = collect_wiki_files(base_dir, args.only, recursive)
        if args.limit > 0:
            wiki_files = wiki_files[:args.limit]
        if not wiki_files:
            print(f'No .wiki files found under {base_dir}')
            sys.exit(1)
        if not args.skip_validate:
            validate_files(wiki_files, base_dir, prefix_map, default_prefix)
    except Exception as exc:
        print(f'预检失败: {exc}', file=sys.stderr)
        sys.exit(1)

    print(f'Found {len(wiki_files)} wiki pages')
    if args.only:
        print('Only paths:')
        for item in args.only:
            print(f'  - {item}')
    if not args.no_prefix:
        print(f'Prefix: default="{default_prefix}", map={json.dumps(prefix_map, ensure_ascii=False)}')

    if args.dry_run:
        print('DRY RUN preview:')
        for path in wiki_files[:20]:
            title = get_page_title(path, base_dir, prefix_map, default_prefix)
            rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
            print(f'  {title} <- {rel} ({path.stat().st_size} bytes)')
        if len(wiki_files) > 20:
            print(f'  ... and {len(wiki_files) - 20} more')
        return

    wiki = WikiSession()
    wiki.login()

    success = 0
    skipped = 0
    conflicts = []
    errors = []
    start_time = time.time()
    summary = args.summary
    if args.bot_summary_prefix and not summary.startswith(args.bot_summary_prefix):
        summary = f'{args.bot_summary_prefix} {summary}'

    for index, path in enumerate(wiki_files, 1):
        title = get_page_title(path, base_dir, prefix_map, default_prefix)
        text = path.read_text(encoding='utf-8')
        remote = wiki.get_page_revision(title)
        if remote['exists'] and remote['content'] == text:
            skipped += 1
            print(f'[{index}/{len(wiki_files)}] SKIP unchanged {title}')
        else:
            is_bot_edit = (not remote['exists']) or remote.get('comment', '').startswith(args.bot_summary_prefix)
            if remote['exists'] and not is_bot_edit and not args.force:
                conflicts.append({
                    'title': title,
                    'revid': remote.get('revid'),
                    'timestamp': remote.get('timestamp'),
                    'user': remote.get('user'),
                    'comment': remote.get('comment', ''),
                    'path': str(path),
                })
                print(f'[{index}/{len(wiki_files)}] CONFLICT {title}: last editor={remote.get("user")} revid={remote.get("revid")}')
            else:
                ok, message = wiki.upload_page(title, text, summary=summary, baserevid=remote.get('revid'))
                if ok:
                    success += 1
                else:
                    errors.append((title, message))
                    print(f'[{index}/{len(wiki_files)}] FAILED {title}: {message[:120]}')
        if index % 50 == 0 or index == len(wiki_files):
            elapsed = max(time.time() - start_time, 0.001)
            print(f'[{index}/{len(wiki_files)}] success={success} skipped={skipped} conflicts={len(conflicts)} failed={len(errors)} rate={index / elapsed:.1f}/s')
        time.sleep(args.delay)

    elapsed = time.time() - start_time
    print(json.dumps({
        'total': len(wiki_files),
        'success': success,
        'skipped': skipped,
        'conflicts': len(conflicts),
        'failed': len(errors),
        'elapsed_sec': round(elapsed, 1),
        'errors': errors[:20],
    }, ensure_ascii=False, indent=2))

    if conflicts:
        conflict_log = Path(args.conflict_log)
        conflict_log.write_text(json.dumps(conflicts, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'Conflict log saved to {conflict_log}')
    if errors:
        error_log = Path('/tmp/wiki_import_errors.json')
        error_log.write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'Error log saved to {error_log}')
    if errors or conflicts:
        sys.exit(1)


if __name__ == '__main__':
    main()