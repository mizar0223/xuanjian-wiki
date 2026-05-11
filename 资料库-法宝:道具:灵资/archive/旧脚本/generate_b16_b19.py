#!/usr/bin/env python3
"""B16-B19 Wiki Page Generator v2 - Fixed bugs + improved name origin"""
import os, shutil, json

BASE = "/Users/leoshi/AIBOOK/xuanjian/wiki/资料库-法宝:道具:灵资"
PAGES = os.path.join(BASE, "pages")

DAO_MAP = [
    ("明阳", "明阳"), ("太阴", "太阴"), ("太阳", "太阳"),
    ("厥阴", "厥阴"), ("少阴", "少阴"), ("少阳", "少阳"),
    ("衡祝", "衡祝"), ("六相", "全丹"), ("渌台", "渌水"),
    ("离", "离火"), ("庚", "庚金"), ("渌", "渌水"),
    ("并", "并火"), ("府", "府水"), ("坎", "坎水"),
    ("逍", "逍金"), ("牡", "牡火"), ("牝", "牝水"),
    ("灴", "灴火"), ("兑", "兑金"), ("齐", "齐金"),
    ("库", "库金"), ("合", "合水"),
    ("紫炁", "紫炁"), ("紫气", "紫炁"), ("真炁", "真炁"),
    ("真气", "真炁"), ("谪炁", "谪炁"), ("寒炁", "寒炁"),
    ("煞炁", "煞炁"), ("晞炁", "晞炁"), ("邃炁", "邃炁"),
    ("瑞炁", "瑞炁"),
    ("霄雷", "霄雷"), ("玄雷", "玄雷"), ("元雷", "元雷"),
    ("玉真", "玉真"), ("鸺葵", "鸺葵"), ("上巫", "上巫"),
    ("司天", "司天"), ("剑道", "剑道"),
    ("雷", "霄雷"), ("谪", "谪炁"), ("寒", "寒炁"),
    ("煞", "煞炁"), ("紫", "紫炁"), ("真", "真炁"),
    ("玉", "玉真"), ("月", "太阴"), ("阳", "明阳"),
]

def infer_daotong(name):
    """推断道统"""
    for pattern, daotong in DAO_MAP:
        if pattern not in name:
            continue
        if pattern == "离" and any(x in name for x in ["太阳", "太阴"]):
            continue
        if pattern == "阳":
            if any(x in name for x in ["明阳", "太阳", "少阳", "少阴", "太阴", "厥阴"]):
                continue
            for p2, d2 in DAO_MAP[:40]:
                if p2 != "阳" and p2 != "离" and p2 in name:
                    return (d2, "⚡")
            return ("明阳", "⚡")
        if pattern == "真":
            if "真炁" in name or "真气" in name:
                return ("真炁", "✅")
            if "真火" in name:
                return ("真火", "✅")
            return ("真炁", "⚡")
        if pattern == "紫":
            return ("紫炁", "⚡")
        if pattern == "月":
            if "太阴" in name:
                continue
            return ("太阴", "⚡")
        if pattern == "玉":
            return ("玉真", "⚡") if "玉真" not in name else ("玉真", "✅")
        if pattern == "离":
            return ("离火", "✅")
        if pattern in ["庚", "渌", "并", "府", "坎", "逍", "牡", "牝", "灴", "兑", "齐", "库", "合"]:
            return (daotong, "✅")
        if pattern in ["明阳", "太阴", "太阳", "厥阴", "少阴", "少阳", "衡祝", "六相"]:
            return (daotong, "✅")
        if pattern in ["紫炁", "紫气", "真炁", "真气", "谪炁", "寒炁", "煞炁", "晞炁", "邃炁", "瑞炁"]:
            return (daotong, "✅")
        if pattern in ["霄雷", "玄雷", "元雷", "玉真", "鸺葵", "上巫", "司天", "剑道"]:
            return (daotong, "✅")
        return (daotong, "⚡")
    return ("未知", "❓")

def pinjie_for_category(category):
    m = {
        "材料": "材料", "筑基法器": "筑基法器", "灵器": "灵器",
        "灵宝": "灵宝", "灵物": "灵物", "灵资": "灵资",
        "丹药": "丹药", "符箓": "符箓", "剑道": "剑道",
        "仙器": "仙器", "位别": "位别", "古灵器/灵宝": "古灵器",
        "法宝": "法宝",
    }
    return m.get(category, "待分类")

def extract_name_origin(name):
    """名字字义分析"""
    compounds = []
    elems = {
        "离": "离火", "庚": "庚金", "渌": "渌水", "并": "并火",
        "府": "府水", "坎": "坎水", "明阳": "明阳", "太阴": "太阴",
        "太阳": "太阳", "真火": "真火", "紫炁": "紫炁", "真炁": "真炁",
        "谪炁": "谪炁", "寒炁": "寒炁", "厥阴": "厥阴", "少阴": "少阴",
        "少阳": "少阳", "衡祝": "衡祝", "六相": "全丹", "渌台": "渌水",
        "玉真": "玉真", "鸺葵": "鸺葵", "太阴": "太阴",
        "太阳": "太阳", "月": "太阴",
    }
    for key, meaning in elems.items():
        if key in name and key not in [x[0] for x in compounds]:
            compounds.append((key, meaning))
    compounds = compounds[:3]
    if compounds:
        parts = [f"「{k}」为{m}标帜字" for k, m in compounds]
        return "名字中" + "、".join(parts) + "。"
    return "''待考据''"

def generate_wiki(entity, category, daotong, daotong_conf):
    pinjie = pinjie_for_category(category)
    pinjie_conf = "✅" if category != "待分类" else "❓"
    dao_display = f"[[道统-{daotong}|{daotong}]]" if daotong != "未知" else "未知"
    name_origin = extract_name_origin(entity)

    page = f"""{{{{导航栏}}}}

'''{entity}'''是《玄鉴仙族》中的{pinjie if pinjie != '待分类' else '[[待分类]]'}。

== 基本信息 ==

{{| class="wikitable"
|-
! 字段 !! 内容
|-
| 品阶 || [[{pinjie}]]
|-
| 品阶置信度 || {pinjie_conf}
|-
| 道统 || {dao_display}
|-
| 道统置信度 || {daotong_conf}
|-
| 出现次数 || 1次
|-
| 首次出现 || 待考据
|-
| 最新出现 || 待考据
|}}

== 名字由来 ==
{name_origin}

== 功能与威能 ==
''待考据''

== 所属道统 ==
'''道统'''：{daotong if daotong != '未知' else '未知'}
"""
    cats = ["造物"]
    cats.append(category if category != "待分类" else "待分类")
    cats.append(f"道统-{daotong}" if daotong != "未知" else "道统-未知")
    for c in cats:
        page += f"\n[[Category:{c}]]"
    return page

# ========== Entity definitions ==========
CATEGORIES = {
    "待分类": "予命尘微, 仰元浮土, 伐柯宫阙, 余生幻象, 冲阳虚土, 凝光土, 初霞浮土, 净月白, 列宿岁光, 刘长龚银盒, 劫中相, 厚重衣, 受抚顶, 取命玉, 吐纳石, 含光瓶, 吞金灵土, 合阳道石, 命真敕, 噤元布, 四火明光, 四象仪, 圆光动心, 地火, 地玄灵光, 垂正光, 夏中元土, 大归无念, 天火, 太阳承光, 夺魂杵, 夺魂金, 好昆都, 如玉东, 孤阴元光, 安朝石, 定坤灵火, 定衡金书, 定阳厥阴大法剑, 密云磨石, 宝敕太阴金光敕, 密明传度, 富年石, 尘劫灵火炮, 山越石, 峨冠玄光, 岳雲石, 巽光风刃, 平木心, 广明玄光, 广漠玄土, 建光土, 归均玉, 归衡玄光, 心王禅位, 必受玄光, 念石, 性灾风火, 息悬土, 恨天道法, 悦风石, 悬星石, 成言玄光, 成言钟, 承阳炉, 把素土, 抑山石, 折元土, 拂尘石, 按气真火, 拾古玉, 授道金, 捻玄火, 焕象石, 玉中金书, 玉中金母, 玉素金, 玉阳金, 班石, 瑞气云, 留步山石, 白衡道石, 白鳞金光, 百里玄光, 百阳高玄, 盘星道石, 真浮土, 真火天, 真火烟, 石鳞火炉, 碎星玉, 碧落玄光, 祖讳, 福地石, 禅道信, 立宗石, 竹杖, 符阳, 篁水, 篁母灵水, 筹光石, 纳星玉, 绝阴火, 罗喉金阶, 老参根, 聚火土, 胎息灵物, 能辰玉, 芫气, 草木之尹, 落道灵石, 藤萝木, 虚玄土, 观化灵火, 言阳玉, 语冰石, 调杼柚, 谪道玄光, 踏火玄石, 通呈石, 道经玄龟, 避死玄光, 鎮元玄口土, 长霞雾, 阖天之光, 阴司阴司符敕, 降真土, 集木真潭, 霜暗石, 青尺金书, 青宣, 鞠部火石, 风火玄光, 飞光石, 食气环, 首阳山石, 高观玄光",
    
    "材料": "上玉, 丙火星铁, 东火元金, 书齐墨, 乾熙玄铁, 修量金, 六真火, 凯土石母, 凤鸣金, 列宿火, 到乡台, 北旨金, 半尺岩, 召云金, 合离元火, 合阳铁, 商浊遗水, 土中石, 地火元井, 安天玄铁, 宝霞土, 宝霞火, 容山金, 少离玄铁, 山中枯木, 平光玄铁, 度命金泉, 归鹤土, 归鹤玉, 悬阳土, 成汤真土, 托阳石, 承明金, 承淮铁, 拱阳石, 捻玉, 摇木石, 散合之木, 斋阴石, 斩缘石, 斩金玄火, 明含金石, 明山石, 明燧土, 明烛金, 星离铁, 月兔, 望玉泉, 杳溟玄铁, 松上雪, 枭魂羽玉, 极桐玄铁, 极海深水, 样中玄铁, 正阳烈石, 每阳石, 求土, 沉阳元火, 沙鸣土, 浮光玄土, 涫阳土, 涵离金, 湖下玄铁, 灰玉, 煞陵铜, 牛饮土, 玄离铁, 玄铁, 玉伏金, 玉夜铁, 瑞气云, 白泊元金, 硅阳石, 硬生石, 祖讳玄铁, 神危金, 空蚕金, 粹元铜, 紫阳石, 织命玄铁, 网丝金, 群燕金, 至方铜, 良庐铜, 落离火, 觅金, 誉金, 赤尺石, 赤金, 跃光金, 辰阳土, 金冠玄铁, 铁心玄铁, 铜铁金, 锋金, 锁心玄铁, 长明火, 阳地土, 阳尺铜, 阳火石, 阳火铜, 阳焰金, 陈玄铁, 雨石玄铁, 青尺铁, 青渊火, 颜湖铁, 飞光石, 高悬石, 鲸石玄土, 麟光铜",
    
    "筑基法器": "凡铁法器, 天一终阕皇剑, 寒铁大刃, 少阴玄剑, 巽木金笼, 扰命长刀, 替参玄剑, 月阙玄剑, 沉金掠, 清炁玄剑, 烛天黑旗, 疾风飞石, 金销洞玄器, 门华宝冠, 青锋法剑, 雷元铁棍, 骅掠玄花",
    
    "灵器": "修越权柄, 入玄灵火环, 却邪灵金, 周公玄索, 天中玉, 宿卫玄金钟, 岁中细毫, 帝戮玄刃, 战合灵剑, 月阙玄剑, 桀金玄光, 橐灵刀, 河清海晏杖, 清源笔, 玉伏离钩, 玉甘金, 真武华, 破阵黄金台, 艮土宝塔",
    
    "灵宝": "修越玄阶, 八风玄舟, 剑意玉, 名余镜, 向辟景, 呈祥金鹤, 四境战鼓, 大灵宝, 太阳玄金盒, 太阴宝炉, 寒室白鳞, 居心炉, 引风炉, 敲狼金册, 明阳玄炉, 昙花宝罐, 枭鸺玉, 桑下玉, 正木玄祓, 武道金盘, 泉帝叩门, 沐光炉, 浴血金铃, 渔火金鳞, 火中取金盘, 焚元纯阳钟, 真一炉, 紫金玉镯, 舜行逆舟, 良金鼎, 荡风铃, 通呈金盘, 青玉玄金, 青玄灵岩, 青虹舟, 颈上金羽, 香积金炉, 鹈金盒",
    
    "灵物": "万花灵木, 不移灵岩, 不落松, 东火流金, 临光木, 乐目石, 九黎石, 云霆石, 修心天仪石, 修越心石, 列岛金木, 功德玄石, 参明玉, 却邪白, 取明石, 合阙玄石, 合阳宝珠, 命息石, 太阴玄石, 央明石, 威道玄石, 学语石, 守心玉, 安天心铁, 宝光玉, 将胜石, 山越石, 府水灵物, 归土石, 当阳石, 心禅木, 心韵宝珠, 忠愚石, 扇明石, 捕火石, 探道玉, 散余玄石, 明世玄珠, 明石乳, 明窍珠, 昭元石, 时墟石, 朝阳石, 朝霞石, 正合听风石, 正听石, 正阳玄木, 正阳玄胎, 每阳玄胎, 每阳石, 沉云宝珠, 治命玄石, 渡明玉, 火中石, 烈火星石, 烈阳玄石, 灵明宝珠, 灵火心岩, 灵火石, 灵物, 灼阳石, 甘木, 白木心, 白朝玄石, 白朝石, 真火元石, 真火岩, 真金鼎, 石心金, 石烛火, 石髓金, 砂隐石, 碧玉, 祖陵木, 禪武石, 穿石心铁, 红光石, 紫玄石, 紫府玉, 紫气心石, 续命木, 育德圣心, 至明火, 至阳玄石, 苍云石, 荡邪金, 落道灵木, 观石, 赤霞石, 违命灵木, 金命玄铁, 金玉, 金髓石, 金鳞石, 钻心玄木, 铁心玄木, 铜石心, 锁命元铁, 锁心玄木, 金光玄木, 阴司石, 青元石, 青道石, 风穴石, 饮气灵木, 鬼命灵木, 魂石",
    
    "灵资": "修越命土, 六相金液, 合阳灵资, 四绪土, 土德灵资, 太阳玉液, 太阴灵资, 定阳真金, 宝光灵资, 明阳资玉, 明阳金藏, 暖阳玉, 朝霞玉液, 水火真精, 灵资, 玉阳资, 玉阳金, 真汞, 真火真精, 真阳玄铁, 艮土命石, 赤玄元锏, 还阳玉, 金阳资, 阳玉, 阳金真汞, 青元真汞",
    
    "丹药": "九华散, 余阳真人药, 太阴月华真丹, 巫丹丹道, 消元散, 溟光散, 白囊阳丹, 真玉散, 紫府玄丹, 紫气归元丹, 行气丹, 金阳元丹, 阳元玉液, 阳丹, 阳火元丹, 青玄大丹",
    
    "符箓": "上元符箓, 何中符, 借世拘心巫法, 定阳天符, 宝阳符箓, 明阳符, 真武符箓, 紫府符夹, 镇字符, 青松观符箓",
    
    "剑道": "夏长仙剑, 太阴玄剑心, 明阳玄剑, 涵元, 玄月灵粹",
    
    "仙器": "道胎法旨, 仙器",
    
    "位别": "大衍天素书, 渌台醒心剑, 素元, 萃心环",
    
    "古灵器/灵宝": "巢祖玄庭",
    
    "法宝": "春长仙剑, 纯阳仙剑",
}

def main():
    batch_dirs = [
        "B16-L6-仅1次",
        "B17-L6-仅1次",
        "B18-L6-仅1次",
        "B19-L6-仅1次",
    ]
    
    all_entities = []
    for cat, ent_str in CATEGORIES.items():
        for entity in [e.strip() for e in ent_str.split(',') if e.strip()]:
            all_entities.append((entity, cat))
    
    print(f"总计实体: {len(all_entities)}")
    
    pages = []
    stats = {"total": 0, "no_daotong": 0, "by_conf": {}, "by_dao": {}, "by_cat": {}}
    
    for entity, category in all_entities:
        dao, conf = infer_daotong(entity)
        page = generate_wiki(entity, category, dao, conf)
        pages.append((entity, category, dao, conf, page))
        
        stats["total"] += 1
        stats["by_conf"][conf] = stats["by_conf"].get(conf, 0) + 1
        stats["by_dao"][dao] = stats["by_dao"].get(dao, 0) + 1
        stats["by_cat"][category] = stats["by_cat"].get(category, 0) + 1
        if dao == "未知":
            stats["no_daotong"] += 1
    
    n = len(pages) // 4 + 1
    dir_map = {d: [] for d in batch_dirs}
    for i, pg in enumerate(pages):
        d = batch_dirs[min(i // n, 3)]
        dir_map[d].append(pg)
    
    # 备份旧文件并写入新文件
    for d in batch_dirs:
        dp = os.path.join(PAGES, d)
        backup = os.path.join(BASE, "backup", f"{d}_old")
        os.makedirs(backup, exist_ok=True)
        for f in os.listdir(dp):
            if f.endswith('.wiki'):
                shutil.copy2(os.path.join(dp, f), os.path.join(backup, f))
                os.remove(os.path.join(dp, f))
        for entity, cat, dao, conf, page in dir_map[d]:
            fp = os.path.join(dp, f"造物-{entity}.wiki")
            with open(fp, 'w', encoding='utf-8') as fh:
                fh.write(page)
        print(f"  {d}: {len(dir_map[d])} pages")
    
    # 统计
    print(f"\n========== B16-B19 生成统计 ==========")
    print(f"总实体: {stats['total']}")
    print(f"无道统: {stats['no_daotong']} ({stats['no_daotong']/stats['total']*100:.1f}%)")
    print(f"\n道统置信度: {stats['by_conf']}")
    print(f"\n各道统Top15:")
    for dao, cnt in sorted(stats['by_dao'].items(), key=lambda x: -x[1])[:15]:
        print(f"  {dao}: {cnt}")
    print(f"\n各分类:")
    for cat, cnt in stats['by_cat'].items():
        print(f"  {cat}: {cnt}")
    
    with open(os.path.join(BASE, "generation_stats.json"), 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
