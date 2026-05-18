#!/usr/bin/env python3
"""
批量生成玄鉴仙族Wiki专题页
输入: pages/ 目录下各品类子目录
输出: pages/00-体系/ 下的专题页 .wiki 文件
"""

import os
import re
import sys
from pathlib import Path
from collections import defaultdict, Counter

# 公共路径模块（兼容直接执行与作为模块导入）
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import PAGES_DIR  # noqa: E402

OUTPUT_DIR = PAGES_DIR / "00-体系"

# ============================================================
# 品类定义：目录 → 专题页配置
# ============================================================
CATEGORIES = {
    "灵气": {
        "dir": "01-灵气",
        "prefix": "造物",
        "overview": (
            "'''灵气'''是《玄鉴仙族》世界观中天地自然孕育的精华之气，"
            "是修士修炼、炼器、炼丹的基础资源。灵气按品阶从低到高可分为灵气、"
            "紫府灵火/灵水、极品灵气等，其中极品灵气蕴含充足的「法性」，"
            "在性命上甚至能媲美灵资。"
        ),
        "definition": (
            "在玄鉴仙族品阶体系中，灵气属于'''资源类'''造物，位于造物品阶体系的底层，"
            "是筑基修士修炼的基础资粮：\n\n"
            "* '''类型'''：灵气\n"
            "* '''层级'''：筑基 → 紫府\n"
            "* '''品质'''：普通灵气 / 紫府灵火·灵水 / 极品灵气\n\n"
            "灵气与灵物的核心区别：灵气是修炼采摄的气态资源，灵物则是蕴含灵气的固态实体。"
        ),
        "related": [
            ("灵物", "灵气的固态凝聚态"),
            ("灵资", "紫府级修炼资源"),
            ("丹药", "以灵气灵物炼制的丹剂"),
            ("玄鉴仙族品阶体系", "完整品阶体系"),
        ],
    },
    "灵物": {
        "dir": "02-灵物",
        "prefix": "造物",
        "overview": (
            "'''灵物'''是《玄鉴仙族》世界观中数量最多、覆盖最广的造物品类，"
            "涵盖了从筑基级到紫府级的各类天然灵材。灵物既可以是修炼的辅材，"
            "也可以是炼器、布阵、炼丹的核心素材，在整个造物体系中占据枢纽地位。"
        ),
        "definition": (
            "在玄鉴仙族品阶体系中，灵物属于'''资源类'''造物，品阶跨度大、种类繁多：\n\n"
            "* '''类型'''：灵物（含紫府灵物、筑基灵物、宝药等子类）\n"
            "* '''层级'''：筑基 → 紫府\n"
            "* '''品质'''：灵物 / 紫府灵物 / 筑基灵物 / 宝药 / 特殊灵物\n\n"
            "灵物与灵气的区别：灵物是蕴含灵气的固态实体，灵气则是气态的修炼资源。"
            "灵物与灵资的区别：灵资特指紫府级修炼核心资源，灵物范围更广。"
        ),
        "related": [
            ("灵气", "灵物的气态对应物"),
            ("灵资", "紫府级修炼核心资源"),
            ("材料", "炼器辅材"),
            ("丹药", "以灵物炼制的丹剂"),
            ("玄鉴仙族品阶体系", "完整品阶体系"),
        ],
    },
    "灵资": {
        "dir": "03-灵资",
        "prefix": "造物",
        "overview": (
            "'''灵资'''是《玄鉴仙族》世界观中紫府修士修炼的核心资源，"
            "品阶高于普通灵物，是突破仙基、温养紫府不可或缺的珍稀之物。"
            "灵资包括各类灵水、灵砂、灵火等，往往与特定道统深度绑定。"
        ),
        "definition": (
            "在玄鉴仙族品阶体系中，灵资属于'''资源类'''造物，品阶高于灵物：\n\n"
            "* '''类型'''：灵资（含紫府灵资）\n"
            "* '''层级'''：紫府\n"
            "* '''品质'''：灵资 / 紫府灵资\n\n"
            "灵资与灵物的关系：灵资可视为灵物的高阶子集，品阶更高、更稀有、更珍贵。"
            "原著中「部分极品灵气蕴含充足的『法性』，在性命上甚至能媲美灵资」"
            "——可见灵资在品阶体系中位于极品灵气之上。"
        ),
        "related": [
            ("灵物", "灵资的低阶对应物"),
            ("灵气", "气态修炼资源"),
            ("丹药", "以灵资为丹体的丹剂"),
            ("玄鉴仙族品阶体系", "完整品阶体系"),
        ],
    },
    "丹药": {
        "dir": "04-丹药",
        "prefix": "造物",
        "overview": (
            "'''丹药'''是《玄鉴仙族》世界观中以灵气、灵物、灵资为原料，"
            "经修士炼丹术精炼而成的造物。丹药品阶从低到高分为散剂、丹药、紫府灵丹，"
            "其中紫府灵丹可「生死人而肉白骨」，功效远超筑基级丹药。"
        ),
        "definition": (
            "在玄鉴仙族品阶体系中，丹药属于'''消耗品类'''造物：\n\n"
            "* '''类型'''：丹药（含紫府灵丹、散剂）\n"
            "* '''层级'''：筑基 → 紫府\n"
            "* '''品质'''：散剂 / 丹药 / 紫府灵丹\n\n"
            "丹药与灵物的区别：丹药是人工炼制产物，灵物是天然存在之物。"
            "紫府灵丹以紫府灵水为丹体、紫府灵物为调和，精炼动辄万次以上。"
        ),
        "related": [
            ("灵物", "丹药的原料之一"),
            ("灵资", "紫府灵丹的核心丹体"),
            ("灵气", "丹药的灵力来源"),
            ("玄鉴仙族品阶体系", "完整品阶体系"),
        ],
    },
    "法器": {
        "dir": "05-法器",
        "prefix": "造物",
        "overview": (
            "'''法器'''是《玄鉴仙族》世界观中筑基修士所使用的基本兵器与器具，"
            "品阶低于灵器。法器按形制可分为法剑、法枪等，按品质可分为下品、中品、上品。"
            "筑基修士以法器为战斗主器，紫府修士则升级使用灵器。"
        ),
        "definition": (
            "在玄鉴仙族品阶体系中，法器属于'''兵器与造物类'''，位于灵器之下：\n\n"
            "* '''类型'''：法器（含筑基法器、筑基法剑、凡器）\n"
            "* '''层级'''：筑基\n"
            "* '''品质'''：下品 / 中品 / 上品 / 凡器\n\n"
            "法器与灵器的核心区别：法器为筑基修士使用的常规兵器，灵器为紫府修士温养的高阶兵器。"
            "一件灵器的威能往往远超法器。"
        ),
        "related": [
            ("灵器", "法器的紫府级升阶物"),
            ("灵宝", "天变前的古灵器"),
            ("凡器", "法器中的最低品阶"),
            ("玄鉴仙族品阶体系", "完整品阶体系"),
        ],
    },
    "灵器": {
        "dir": "06-灵器",
        "prefix": "造物",
        "overview": (
            "'''灵器'''是《玄鉴仙族》世界观中紫府修士所使用的常规兵器与器具，"
            "品阶位于法器之上、灵宝之下。灵器由紫府修士炼制或温养而成，"
            "分上/中/下三品，是紫府修士征战的主要依仗。"
        ),
        "definition": (
            "在玄鉴仙族品阶体系中，灵器属于'''兵器与造物类'''，位于法器之上、灵宝之下：\n\n"
            "* '''类型'''：灵器（含紫府灵器、灵甲、灵胚等子类）\n"
            "* '''层级'''：紫府\n"
            "* '''品质'''：下品 / 中品 / 上品 / 紫府灵器\n\n"
            "灵器与法器的核心区别：灵器为紫府修士的常规兵器，蕴含灵性与法力；"
            "法器仅为筑基修士的基础器具。灵器与灵宝的核心区别：灵宝为天变前的古灵器，"
            "历经岁月沉淀，威能远超当代灵器，且往往具有「神妙」。"
        ),
        "related": [
            ("法器", "灵器的筑基级前身"),
            ("灵宝", "灵器之上的古灵器"),
            ("法宝", "灵宝之上的更高阶造物"),
            ("玄鉴仙族品阶体系", "完整品阶体系"),
        ],
    },
    "符箓": {
        "dir": "13-符箓",
        "prefix": "造物",
        "overview": (
            "'''符箓'''是《玄鉴仙族》世界观中以灵力封印于符纸之上的造物，"
            "一次性使用，品阶从筑基到紫府不等。符箓在战斗中可提供关键辅助，"
            "如雷罚、驱邪、传讯等。"
        ),
        "definition": (
            "在玄鉴仙族品阶体系中，符箓属于'''消耗品类'''造物：\n\n"
            "* '''类型'''：符箓\n"
            "* '''层级'''：筑基 → 紫府\n"
            "* '''品质'''：视具体符箓而定\n\n"
            "符箓与法器的区别：符箓为一次性消耗品，法器为可反复使用的兵器。"
            "部分符箓品阶标注为「符箓/灵器」，兼具两者的特性。"
        ),
        "related": [
            ("法器", "符箓的可复用对应物"),
            ("灵器", "部分符箓兼具灵器品阶"),
            ("灵宝", "更高阶的造物"),
            ("玄鉴仙族品阶体系", "完整品阶体系"),
        ],
    },
    "材料": {
        "dir": "12-材料",
        "prefix": "造物",
        "overview": (
            "'''材料'''是《玄鉴仙族》世界观中用于炼器、炼丹、布阵的辅助性造物，"
            "品阶横跨筑基到紫府。材料本身通常不具备独立威能，"
            "但作为炼器的辅材，是决定成品品阶的关键因素。"
        ),
        "definition": (
            "在玄鉴仙族品阶体系中，材料属于'''辅材类'''造物：\n\n"
            "* '''类型'''：材料\n"
            "* '''层级'''：筑基 → 紫府\n"
            "* '''品质'''：普通材料 / 筑基灵火级材料\n\n"
            "材料与灵物的区别：材料侧重于「用途」（炼器辅材），灵物侧重于「来源」（天然灵材）。"
            "两者有交集但不完全等同。"
        ),
        "related": [
            ("灵物", "材料的天然来源"),
            ("灵器", "材料的主要炼制目标"),
            ("法器", "材料亦可炼制法器"),
            ("玄鉴仙族品阶体系", "完整品阶体系"),
        ],
    },
    "凡器": {
        "dir": "05-法器",  # 凡器文件在法器目录下
        "filter": "凡器",  # 只取品阶含"凡器"的页面
        "prefix": "造物",
        "overview": (
            "'''凡器'''是《玄鉴仙族》世界观中品阶最低的造物类型，"
            "位于法器之下，不入品阶之列。凡器无灵性、无法力，"
            "仅为凡间匠人以凡铁锻造的寻常器物，偶有修士以之应急。"
        ),
        "definition": (
            "在玄鉴仙族品阶体系中，凡器属于'''最低品阶'''造物，位于法器之下：\n\n"
            "* '''类型'''：凡器\n"
            "* '''层级'''：凡人 / 筑基以下\n"
            "* '''品质'''：无品阶\n\n"
            "凡器与法器的区别：法器经修士灌注灵力，具有灵性；"
            "凡器则为凡间器物，无任何灵力加持。"
        ),
        "related": [
            ("法器", "凡器的上一品阶"),
            ("灵器", "紫府修士的兵器"),
            ("玄鉴仙族品阶体系", "完整品阶体系"),
        ],
    },
}


def extract_metadata(filepath: Path) -> dict:
    """从 .wiki 文件提取品阶、道统、出现次数等字段"""
    content = filepath.read_text(encoding="utf-8")
    name = filepath.stem

    # 提取品阶
    pj_match = re.search(r'\|\s*品阶\s*\|\|\s*(.+?)(?:\n|$)', content)
    pj_raw = pj_match.group(1).strip() if pj_match else "未知"
    # 去掉 [[ ]] 链接语法，保留文字
    pj = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', pj_raw)
    # 去掉置信度标记
    pj = re.sub(r'\s*[✅⚡❓]\s*', ' ', pj).strip()
    # 去掉多余括号内容中的置信度
    pj = pj.rstrip()

    # 提取道统
    dt_match = re.search(r'\|\s*道统\s*\|\|\s*(.+?)(?:\n|$)', content)
    dt_raw = dt_match.group(1).strip() if dt_match else "未知"
    dt = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', dt_raw)
    dt = re.sub(r'\s*[✅⚡❓]\s*', ' ', dt).strip()
    # 清理 "待确认" 等后缀
    dt = re.sub(r'\s*待确认.*$', '', dt).strip()
    if not dt or dt == '—':
        dt = "未知"

    # 提取出现次数
    freq_match = re.search(r'\|\s*出现次数\s*\|\|\s*(\d+)', content)
    freq = int(freq_match.group(1)) if freq_match else 0

    # 提取首次出现
    first_match = re.search(r'\|\s*首次出现\s*\|\|\s*(.+?)(?:\n|$)', content)
    first = first_match.group(1).strip() if first_match else "—"

    # 提取最新出现
    last_match = re.search(r'\|\s*最新出现\s*\|\|\s*(.+?)(?:\n|$)', content)
    last = last_match.group(1).strip() if last_match else "—"

    # 提取别名
    alias_match = re.search(r'\|\s*别名\s*\|\|\s*(.+?)(?:\n|$)', content)
    alias = alias_match.group(1).strip() if alias_match else ""

    # 提取首段简介（第一段非空非模板文本）
    intro = ""
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("'''") and name in line:
            # 取这行和后续行直到空行
            intro_lines = []
            for j in range(i, min(i + 5, len(lines))):
                if lines[j].strip() == "" and intro_lines:
                    break
                intro_lines.append(lines[j].strip())
            intro = " ".join(intro_lines)
            # 清理开头的加粗标记
            intro = re.sub(r"'''+", "", intro)
            break

    return {
        "name": name,
        "品阶": pj,
        "道统": dt,
        "出现次数": freq,
        "首次出现": first,
        "最新出现": last,
        "别名": alias,
        "简介": intro[:100] if intro else "",
    }


def normalize_daotong(dt: str) -> list:
    """标准化道统字段，拆分复合道统"""
    # 去掉 （xxx） 括号内容
    dt = re.sub(r'[（(].*?[）)]', '', dt)
    # 按 / 分割
    parts = [p.strip() for p in dt.split('/')]
    result = []
    for p in parts:
        p = p.strip()
        if p and p not in ('未知', '—', '✅', '⚡', '❓'):
            result.append(p)
    return result


def classify_pj_subtypes(items: list, cat_name: str) -> dict:
    """将品阶值归类为子类型"""
    subtypes = defaultdict(list)
    for item in items:
        pj = item["品阶"]
        # 简单规则：按品阶值直接分组
        # 先尝试归并常见变体
        pj_key = pj

        # 品阶归并规则
        if cat_name == "灵物":
            if "紫府" in pj and "灵物" in pj:
                pj_key = "紫府灵物"
            elif "筑基" in pj and "灵物" in pj:
                pj_key = "筑基灵物"
            elif "宝药" in pj:
                pj_key = "宝药"
            elif "邪宝" in pj:
                pj_key = "灵宝级邪宝/灵物"
            elif "太阴" in pj and "灵物" in pj:
                pj_key = "顶级太阴灵物"
            elif pj in ("灵物", "灵物（紫府灵物）"):
                pj_key = "灵物"
            elif "灵火" in pj:
                pj_key = "特殊灵火"
            elif "灵水" in pj:
                pj_key = "筑基灵水"
            elif "灵器" in pj:
                pj_key = "灵器级"
            else:
                pj_key = pj
        elif cat_name == "灵器":
            if "紫府" in pj and "灵器" in pj:
                pj_key = "紫府灵器"
            elif "灵胚" in pj:
                pj_key = "灵胚"
            elif "古法器" in pj or "古灵器" in pj:
                pj_key = "古法器/灵器（进化型）"
            elif "灵甲" in pj:
                pj_key = "灵甲"
            elif "符" in pj:
                pj_key = "符器/灵器"
            elif "艮土" in pj:
                pj_key = "艮土灵器"
            elif pj in ("灵器", "灵器 ✅"):
                pj_key = "灵器"
            else:
                pj_key = pj
        elif cat_name == "法器":
            if "法剑" in pj or "剑" in pj and "法" in pj:
                pj_key = "筑基法剑"
            elif "古法器" in pj:
                pj_key = "古法器"
            elif "四品" in pj:
                pj_key = "四品法器/法术"
            elif "中品" in pj:
                pj_key = "中品法器"
            elif "凡器" in pj:
                pj_key = "凡器"
            elif "法器" in pj:
                pj_key = "筑基法器"
            else:
                pj_key = pj

        subtypes[pj_key].append(item)

    return dict(subtypes)


def generate_wiki_page(cat_name: str, items: list, config: dict) -> str:
    """生成专题页 wiki 文本"""
    total = len(items)
    sections = []

    # ---- 导航栏 ----
    sections.append("{{导航栏}}\n")

    # ---- 概述 ----
    sections.append(config["overview"])
    sections.append("")

    # ---- 定义与定位 ----
    sections.append("== 定义与定位 ==\n")
    sections.append(config["definition"])
    sections.append("")

    # ---- 品阶细分 ----
    subtypes = classify_pj_subtypes(items, cat_name)
    if len(subtypes) > 1 or total > 5:
        sections.append("== 品阶细分 ==\n")
        sections.append(f"wiki 中共收录 '''{total}''' 个{cat_name}类页面，按品阶字段细分如下：\n")

        sections.append('{| class="wikitable"')
        sections.append("|-")
        sections.append(f"! 品阶细类 !! 页数 !! 说明")
        for subtype_name, subtype_items in sorted(subtypes.items(), key=lambda x: -len(x[1])):
            # 取代表举例
            examples = [i["name"] for i in sorted(subtype_items, key=lambda x: -x["出现次数"])[:3]]
            example_str = "、".join(
                f"[[造物-{e}|{e}]]" if config["prefix"] == "造物" else f"[[{e}]]"
                for e in examples
            )
            sections.append("|-")
            sections.append(f"| {subtype_name} || {len(subtype_items)} || {example_str}")
        sections.append("|}")
        sections.append("")

    # ---- 道统分布 ----
    if total >= 5:
        dt_counter = Counter()
        dt_items = defaultdict(list)
        for item in items:
            dts = normalize_daotong(item["道统"])
            if not dts:
                dt_counter["未知"] += 1
                dt_items["未知"].append(item)
            else:
                for dt in dts:
                    dt_counter[dt] += 1
                    dt_items[dt].append(item)

        sections.append("== 道统分布 ==\n")
        sections.append(f"以下为 {total} 个{cat_name}页面的道统分布：\n")

        sections.append('{| class="wikitable sortable"')
        sections.append("|-")
        sections.append(f"! 道统 !! {cat_name}数 !! 代表{cat_name}")
        for dt, count in dt_counter.most_common():
            rep_items = sorted(dt_items[dt], key=lambda x: -x["出现次数"])[:3]
            rep_str = "、".join(
                f"[[造物-{r['name']}|{r['name']}]]" for r in rep_items
            )
            sections.append("|-")
            sections.append(f"| {dt} || {count} || {rep_str}")
        sections.append("|}")
        sections.append("")

    # ---- 核心 Top N ----
    if total >= 5:
        top_n = min(15, total)
        sorted_items = sorted(items, key=lambda x: -x["出现次数"])
        top_items = [i for i in sorted_items if i["出现次数"] > 0][:top_n]

        if top_items:
            sections.append(f"== 核心{cat_name}（高频 Top {len(top_items)}） ==\n")
            sections.append(f"以下为原著中出现频次最高的 {len(top_items)} 件{cat_name}，按出现次数降序排列：\n")

            sections.append('{| class="wikitable sortable"')
            sections.append("|-")
            sections.append(f"! 排名 !! {cat_name}名 !! 道统 !! 品阶 !! 出现次数")
            for idx, item in enumerate(top_items, 1):
                sections.append("|-")
                link = f"[[造物-{item['name']}|{item['name']}]]"
                sections.append(
                    f"| {idx} || {link} || {item['道统']} || {item['品阶']} || {item['出现次数']}"
                )
            sections.append("|}")
            sections.append("")

    # ---- 全部一览 ----
    sections.append(f"== 全部{cat_name}一览 ==\n")

    if len(subtypes) > 1 and total > 10:
        # 按品阶子类分节展示
        for subtype_name, subtype_items in sorted(subtypes.items(), key=lambda x: -len(x[1])):
            sections.append(f"=== {subtype_name}（{len(subtype_items)} 件） ===\n")
            _emit_table(sections, subtype_items, cat_name, config)
    else:
        _emit_table(sections, items, cat_name, config)

    # ---- 相关链接 ----
    sections.append("== 相关链接 ==\n")
    for rel_name, rel_desc in config["related"]:
        if rel_name != "玄鉴仙族品阶体系":
            sections.append(f"* [[{rel_name}]] — {rel_desc}")
    sections.append(f"* [[玄鉴仙族品阶体系]] — 完整的品阶体系专题页")
    sections.append(f"* [[Category:{cat_name}]] — 全部{cat_name}页面")
    sections.append("")

    # ---- 分类 ----
    sections.append(f"[[Category:体系]]")
    sections.append(f"[[Category:玄鉴仙族]]")
    sections.append(f"[[Category:{cat_name}]]")

    return "\n".join(sections)


def _emit_table(sections, items, cat_name, config):
    """输出一个 wikitable"""
    sorted_items = sorted(items, key=lambda x: -x["出现次数"])

    # 判断是否需要简介列
    has_intro = any(i["简介"] for i in sorted_items[:5])

    sections.append('{| class="wikitable sortable"')
    sections.append("|-")
    if has_intro:
        sections.append(f"! {cat_name}名 !! 道统 !! 品阶 !! 出现次数 !! 简介")
    else:
        sections.append(f"! {cat_name}名 !! 道统 !! 品阶 !! 出现次数")

    for item in sorted_items:
        link = f"[[造物-{item['name']}|{item['name']}]]"
        freq_str = str(item["出现次数"]) if item["出现次数"] > 0 else "—"
        sections.append("|-")
        if has_intro:
            intro_str = item["简介"] if item["简介"] else "—"
            sections.append(
                f"| {link} || {item['道统']} || {item['品阶']} || {freq_str} || {intro_str}"
            )
        else:
            sections.append(
                f"| {link} || {item['道统']} || {item['品阶']} || {freq_str}"
            )
    sections.append("|}")
    sections.append("")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for cat_name, config in CATEGORIES.items():
        dir_path = PAGES_DIR / config["dir"]
        if not dir_path.exists():
            print(f"[SKIP] {cat_name}: 目录不存在 {dir_path}")
            continue

        # 扫描目录
        items = []
        for wiki_file in sorted(dir_path.glob("*.wiki")):
            meta = extract_metadata(wiki_file)
            # 凡器专题需要过滤
            if "filter" in config:
                if config["filter"] not in meta["品阶"]:
                    continue
            items.append(meta)

        if not items:
            print(f"[SKIP] {cat_name}: 无匹配页面")
            continue

        # 生成专题页
        wiki_text = generate_wiki_page(cat_name, items, config)

        # 写入文件
        out_path = OUTPUT_DIR / f"{cat_name}.wiki"
        out_path.write_text(wiki_text, encoding="utf-8")
        print(f"[OK] {cat_name}: {len(items)} pages → {out_path}")

    print("\nDone!")


if __name__ == "__main__":
    main()
