#!/usr/bin/env python3
"""一次性清理脚本：把"造物-"前缀错传的仙基道统页改为重定向。

背景：
  历史上 upload_pages.py 默认前缀为 "造物-"，且未把 pages/仙基道统/ 加入白名单，
  导致 274 个仙基道统页被错传到 "造物-XXX" 标题。修复脚本后已经把它们重新
  上传到了正确标题（如 道统-太阳、神通-分阳钗、位业-显位、道统丨神通丨仙基 等），
  但旧的错误标题页仍残留在线上。本脚本把每个"造物-XXX"幽灵页内容改为：

      #REDIRECT [[XXX]]

  保留旧链接的兼容性，避免外部书签 404。

来源识别：
  线上 "造物-" 前缀页中，去掉前缀后的 stem 若与 pages/仙基道统/ 下任意 .wiki
  文件 stem 相同，即视为幽灵页。

用法：
  python3 scripts/cleanup_zaowu_ghost_redirects.py [--dry-run]
"""
import argparse
import json
import sys
import time
from pathlib import Path

import requests
import urllib3

from common.config import AppConfig, require_wiki_password

urllib3.disable_warnings()

CONFIG = AppConfig()
ROOT = CONFIG.project_root
WIKI_API = CONFIG.wiki_api
WIKI_USER = CONFIG.wiki_user
SUMMARY = '[bot] cleanup: 错传的造物-前缀仙基道统幽灵页改为重定向到正确标题'


def login(s):
    pwd = require_wiki_password(CONFIG)
    tok = s.get(WIKI_API, params={
        'action': 'query', 'meta': 'tokens', 'type': 'login', 'format': 'json'
    }, verify=False, timeout=20).json()['query']['tokens']['logintoken']
    r = s.post(WIKI_API, data={
        'action': 'login', 'lgname': WIKI_USER, 'lgpassword': pwd,
        'lgtoken': tok, 'format': 'json',
    }, verify=False, timeout=20).json()
    if r.get('login', {}).get('result') != 'Success':
        raise RuntimeError(f'Login failed: {r}')
    csrf = s.get(WIKI_API, params={
        'action': 'query', 'meta': 'tokens', 'format': 'json'
    }, verify=False, timeout=20).json()['query']['tokens']['csrftoken']
    return csrf


def list_zaowu_pages(s):
    """枚举所有线上以 '造物-' 开头的页面标题。"""
    titles = []
    apcontinue = None
    while True:
        params = {
            'action': 'query', 'list': 'allpages', 'apprefix': '造物-',
            'aplimit': '500', 'format': 'json',
        }
        if apcontinue:
            params['apcontinue'] = apcontinue
        r = s.get(WIKI_API, params=params, verify=False, timeout=20).json()
        titles.extend(p['title'] for p in r['query']['allpages'])
        if 'continue' in r:
            apcontinue = r['continue']['apcontinue']
        else:
            break
    return titles


def edit_page(s, csrf, title, text, summary):
    for attempt in range(3):
        r = s.post(WIKI_API, data={
            'action': 'edit', 'format': 'json',
            'title': title, 'text': text, 'summary': summary,
            'token': csrf, 'bot': '1',
        }, verify=False, timeout=60).json()
        if 'error' in r:
            if r['error'].get('code') == 'badtoken' and attempt < 2:
                csrf = s.get(WIKI_API, params={
                    'action': 'query', 'meta': 'tokens', 'format': 'json'
                }, verify=False, timeout=20).json()['query']['tokens']['csrftoken']
                continue
            return False, r['error'].get('info', str(r['error'])), csrf
        edit = r.get('edit', {})
        if edit.get('result') == 'Success':
            return True, f"rev:{edit.get('newrevid', edit.get('oldrevid', '?'))}", csrf
        return False, str(edit), csrf
    return False, 'max retries', csrf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--delay', type=float, default=0.05)
    args = ap.parse_args()

    # 本地仙基道统的合法 stem 集合
    xianji_stems = {p.stem for p in (ROOT / 'pages' / '仙基道统').rglob('*.wiki')}
    print(f'本地仙基道统 stem 数: {len(xianji_stems)}')

    s = requests.Session()
    csrf = login(s)
    print('Logged in')

    online_zaowu = list_zaowu_pages(s)
    print(f'线上 "造物-" 前缀页总数: {len(online_zaowu)}')

    # 找出幽灵
    ghosts = []
    for title in online_zaowu:
        stem = title[len('造物-'):]
        if stem in xianji_stems:
            ghosts.append((title, stem))
    print(f'识别为幽灵页: {len(ghosts)}')

    if args.dry_run:
        print('--- DRY RUN preview (前 30) ---')
        for title, stem in ghosts[:30]:
            print(f'  {title} -> #REDIRECT [[{stem}]]')
        if len(ghosts) > 30:
            print(f'  ... +{len(ghosts) - 30} more')
        return

    success = 0
    skipped = 0
    failed = []
    start = time.time()
    for i, (title, stem) in enumerate(ghosts, 1):
        # 先看当前内容是否已是重定向到该 stem，是则跳过
        rv = s.get(WIKI_API, params={
            'action': 'query', 'titles': title, 'format': 'json',
            'prop': 'revisions', 'rvprop': 'content', 'rvslots': 'main',
        }, verify=False, timeout=20).json()
        page = list(rv['query']['pages'].values())[0]
        cur = page.get('revisions', [{}])[0].get('slots', {}).get('main', {}).get('*', '')
        target_text = f'#REDIRECT [[{stem}]]\n'
        if cur.strip() == target_text.strip():
            skipped += 1
            print(f'[{i}/{len(ghosts)}] SKIP already redirect {title}')
        else:
            ok, msg, csrf = edit_page(s, csrf, title, target_text, SUMMARY)
            if ok:
                success += 1
            else:
                failed.append((title, msg))
                print(f'[{i}/{len(ghosts)}] FAILED {title}: {msg[:120]}')
        if i % 50 == 0 or i == len(ghosts):
            elapsed = max(time.time() - start, 0.001)
            print(f'[{i}/{len(ghosts)}] success={success} skipped={skipped} failed={len(failed)} rate={i/elapsed:.1f}/s')
        time.sleep(args.delay)

    print(json.dumps({
        'total': len(ghosts), 'success': success, 'skipped': skipped,
        'failed': len(failed), 'elapsed_sec': round(time.time() - start, 1),
        'errors': failed[:10],
    }, ensure_ascii=False, indent=2))
    if failed:
        sys.exit(1)


if __name__ == '__main__':
    main()
