#!/usr/bin/env python3
"""扫描本地 wiki 文件中的红链（broken links）"""
import re
import os
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path("/data/workspace/rq0rlzeg/xuanjian-wiki/资料库/造物/pages")

def collect_local_pages():
    """收集本地所有存在的页面标题（线上标题格式）"""
    pages = set()
    for wiki_file in ROOT.rglob("*.wiki"):
        rel = wiki_file.relative_to(ROOT)
        parts = rel.parts
        if len(parts) < 2:
            continue
        dir_name = parts[0]
        filename = wiki_file.stem  # 不含 .wiki

        if dir_name == "00-体系":
            title = filename
        elif dir_name == "20-人物":
            title = f"人物-{filename}"
        else:
            title = f"造物-{filename}"
        pages.add(title)
    return pages

def extract_links(text):
    """提取 [[目标|显示文本]] 或 [[目标]] 中的目标部分"""
    pattern = r'\[\[(.*?)\]\]'
    for match in re.finditer(pattern, text):
        content = match.group(1)
        # 取 | 之前的部分作为链接目标
        target = content.split('|')[0].strip()
        # 忽略空目标和特殊链接（如 Category:, File:, Template: 等）
        if not target or target.startswith('Category:') or target.startswith('File:') or target.startswith('Image:') or target.startswith('Template:'):
            continue
        # 忽略 URL（http/https）
        if target.startswith('http://') or target.startswith('https://'):
            continue
        yield target

def main():
    local_pages = collect_local_pages()
    print(f"本地页面总数: {len(local_pages)}")

    # 红链统计: target -> [(file, line_no)]
    red_links = defaultdict(list)
    all_links_counter = Counter()

    for wiki_file in sorted(ROOT.rglob("*.wiki")):
        rel = wiki_file.relative_to(ROOT)
        try:
            with open(wiki_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"读取失败: {rel}: {e}")
            continue

        for line_no, line in enumerate(lines, 1):
            for target in extract_links(line):
                all_links_counter[target] += 1
                if target not in local_pages:
                    red_links[target].append((str(rel), line_no))

    print(f"\n总链接数: {sum(all_links_counter.values())}")
    print(f"唯一链接目标数: {len(all_links_counter)}")
    print(f"红链目标数: {len(red_links)}")
    print(f"红链出现次数: {sum(len(v) for v in red_links.values())}")

    # 按出现次数排序
    sorted_red = sorted(red_links.items(), key=lambda x: len(x[1]), reverse=True)

    # 按命名空间分组统计
    ns_counter = Counter()
    for target, refs in sorted_red:
        if '-' in target:
            ns = target.split('-', 1)[0]
        else:
            ns = "(无命名空间)"
        ns_counter[ns] += len(refs)

    print("\n=== 按命名空间分布 ===")
    for ns, count in ns_counter.most_common():
        print(f"  {ns}: {count} 次")

    print("\n=== TOP 50 红链（按出现次数排序）===")
    for target, refs in sorted_red[:50]:
        files = set(f for f, _ in refs)
        print(f"  {target}: {len(refs)} 次, 涉及 {len(files)} 个文件")

    # 输出详细报告到文件
    report_path = Path("/data/workspace/rq0rlzeg/xuanjian-wiki/资料库/造物/.workbuddy/red_links_report.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# 红链扫描报告\n\n")
        f.write(f"- 扫描时间: 2026-05-11\n")
        f.write(f"- 本地页面总数: {len(local_pages)}\n")
        f.write(f"- 总链接数: {sum(all_links_counter.values())}\n")
        f.write(f"- 唯一链接目标数: {len(all_links_counter)}\n")
        f.write(f"- 红链目标数: {len(red_links)}\n")
        f.write(f"- 红链出现次数: {sum(len(v) for v in red_links.values())}\n\n")

        f.write("## 按命名空间分布\n\n")
        f.write("| 命名空间 | 出现次数 |\n")
        f.write("|---------|---------|\n")
        for ns, count in ns_counter.most_common():
            f.write(f"| {ns} | {count} |\n")

        f.write("\n## 全部红链（按频次降序）\n\n")
        f.write("| 排名 | 链接目标 | 出现次数 | 涉及文件数 | 样例来源 |\n")
        f.write("|-----|---------|---------|----------|---------|\n")
        for rank, (target, refs) in enumerate(sorted_red, 1):
            files = sorted(set(f for f, _ in refs))
            sample = files[0] if files else ""
            f.write(f"| {rank} | {target} | {len(refs)} | {len(files)} | {sample} |\n")

    print(f"\n详细报告已写入: {report_path}")

if __name__ == "__main__":
    main()
