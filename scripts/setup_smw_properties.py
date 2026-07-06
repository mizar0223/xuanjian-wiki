#!/usr/bin/env python3
"""批量创建 SMW Property 页面 + 重写 {{角色}} 模板（含 SMW 标注）"""

import requests
import time

from common.config import AppConfig, require_wiki_password

CONFIG = AppConfig()
WIKI_API = CONFIG.wiki_api
USERNAME = CONFIG.wiki_user
WIKI_URL = CONFIG.wiki_url or 'http://9433.com.cn/wiki/'

# ============================================================
# SMW Property 定义
# ============================================================

PROPERTIES = {
    # === 角色类 ===
    "Property:姓名": {
        "type": "Text",
        "desc": "角色的全名"
    },
    "Property:性别": {
        "type": "Text",
        "desc": "角色性别：男/女",
        "values": "男, 女"
    },
    "Property:字辈": {
        "type": "Text",
        "desc": "角色的字辈字（如玄、景、渊、清等）"
    },
    "Property:族系": {
        "type": "Text",
        "desc": "所属脉系：伯脉/仲脉/叔脉/季脉/外姓"
    },
    "Property:世代": {
        "type": "Text",
        "desc": "世代编号（如十三世）"
    },
    "Property:修为": {
        "type": "Text",
        "desc": "修为境界（凡人/胎息/练气/筑基/紫府 + 子级别）"
    },
    "Property:仙基": {
        "type": "Text",
        "desc": "仙基名称"
    },
    "Property:命神通": {
        "type": "Text",
        "desc": "命神通名称"
    },
    "Property:道统": {
        "type": "Text",
        "desc": "修行道统/功法路线"
    },
    "Property:法器": {
        "type": "Text",
        "desc": "持有法器"
    },
    "Property:道号": {
        "type": "Text",
        "desc": "道号/真人号"
    },
    "Property:身份": {
        "type": "Text",
        "desc": "社会身份/头衔"
    },
    "Property:状态": {
        "type": "Text",
        "desc": "存活状态：存活/已故/失踪/未知",
        "values": "存活, 已故, 失踪, 未知"
    },
    "Property:父亲": {
        "type": "Page",
        "desc": "生父（Wiki 页面链接）"
    },
    "Property:嗣父": {
        "type": "Page",
        "desc": "嗣父/过继养父（Wiki 页面链接）"
    },
    "Property:母亲": {
        "type": "Text",
        "desc": "母亲名字"
    },
    "Property:配偶": {
        "type": "Page",
        "desc": "道侣/配偶（Wiki 页面链接，可多值）"
    },
    "Property:子女": {
        "type": "Page",
        "desc": "子女（Wiki 页面链接，可多值）"
    },
    "Property:师承": {
        "type": "Text",
        "desc": "师父/师承关系"
    },
    "Property:所属势力": {
        "type": "Page",
        "desc": "所属门派/势力（Wiki 页面链接）"
    },
    "Property:首次出场": {
        "type": "Text",
        "desc": "首次出场章节"
    },
    "Property:结局": {
        "type": "Text",
        "desc": "角色最终结局"
    },

    # === 势力类 ===
    "Property:势力类型": {
        "type": "Text",
        "desc": "势力类型：宗门/家族/王国/散修组织",
        "values": "宗门, 家族, 王国, 散修组织, 商会, 军队"
    },
    "Property:势力等级": {
        "type": "Text",
        "desc": "势力实力等级"
    },
    "Property:掌门": {
        "type": "Page",
        "desc": "当前掌门/族长（Wiki 页面链接）"
    },
    "Property:势力所在地": {
        "type": "Page",
        "desc": "势力驻地（Wiki 页面链接）"
    },

    # === 地点类 ===
    "Property:地点类型": {
        "type": "Text",
        "desc": "地点类型：山脉/城池/秘境/村落/海域",
        "values": "山脉, 城池, 秘境, 村落, 海域, 岛屿, 宗门驻地"
    },
    "Property:所属区域": {
        "type": "Text",
        "desc": "所属大区域"
    },
    "Property:管辖势力": {
        "type": "Page",
        "desc": "管辖此地点的势力（Wiki 页面链接）"
    },

    # === 功法类 ===
    "Property:功法品级": {
        "type": "Text",
        "desc": "功法品级：三品/四品/五品/六品/无品",
        "values": "一品, 二品, 三品, 四品, 五品, 六品, 无品"
    },
    "Property:功法属性": {
        "type": "Text",
        "desc": "功法属性/元素"
    },
    "Property:修炼者": {
        "type": "Page",
        "desc": "修炼此功法的角色（Wiki 页面链接，可多值）"
    },

    # === 事件类 ===
    "Property:事件时间": {
        "type": "Text",
        "desc": "事件发生的纪年时间"
    },
    "Property:事件地点": {
        "type": "Page",
        "desc": "事件发生地点（Wiki 页面链接）"
    },
    "Property:参与角色": {
        "type": "Page",
        "desc": "参与此事件的角色（Wiki 页面链接，可多值）"
    },
    "Property:事件结果": {
        "type": "Text",
        "desc": "事件的结果/影响"
    },
}


def get_session():
    """创建已登录的 requests session"""
    password = require_wiki_password(CONFIG)
    s = requests.Session()
    # Step 1: 获取 login token
    r = s.get(WIKI_API, params={
        "action": "query", "meta": "tokens", "type": "login", "format": "json"
    })
    login_token = r.json()["query"]["tokens"]["logintoken"]

    # Step 2: 登录
    r = s.post(WIKI_API, data={
        "action": "clientlogin",
        "username": USERNAME,
        "password": password,
        "loginreturnurl": WIKI_URL.rstrip('/') + '/首页',
        "logintoken": login_token,
        "format": "json"
    })
    result = r.json()
    if result.get("clientlogin", {}).get("status") == "PASS":
        print(f"✅ 登录成功: {USERNAME}")
    else:
        print(f"❌ 登录失败: {result}")
        # 尝试 action=login 备选
        r = s.get(WIKI_API, params={
            "action": "query", "meta": "tokens", "type": "login", "format": "json"
        })
        login_token = r.json()["query"]["tokens"]["logintoken"]
        r = s.post(WIKI_API, data={
            "action": "login",
            "lgname": USERNAME,
            "lgpassword": password,
            "lgtoken": login_token,
            "format": "json"
        })
        print(f"  备选登录: {r.json()}")

    return s


def get_csrf_token(session):
    """获取 CSRF 编辑 token"""
    r = session.get(WIKI_API, params={
        "action": "query", "meta": "tokens", "format": "json"
    })
    return r.json()["query"]["tokens"]["csrftoken"]


def create_page(session, title, content, summary=""):
    """创建或覆盖一个 Wiki 页面"""
    token = get_csrf_token(session)
    r = session.post(WIKI_API, data={
        "action": "edit",
        "title": title,
        "text": content,
        "summary": summary or f"Bot: 创建 {title}",
        "format": "json",
        "token": token
    })
    result = r.json()
    if "edit" in result and result["edit"].get("result") == "Success":
        return True
    else:
        print(f"  ⚠️ {title}: {result}")
        return False


def create_properties(session):
    """批量创建 SMW Property 页面"""
    print("\n📋 创建 SMW Property 页面...")
    success = 0
    for prop_name, prop_def in PROPERTIES.items():
        prop_type = prop_def["type"]
        desc = prop_def["desc"]
        allowed = prop_def.get("values", "")

        # 构建 Property 页面内容
        content = f"这是类型为 [[Has type::{prop_type}]] 的属性。\n\n"
        content += f"'''{desc}'''\n\n"
        if allowed:
            content += f"允许的值: {allowed}\n\n"
        content += f"[[Category:Property]]\n"

        if create_page(session, prop_name, content, f"定义 SMW Property: {prop_name}"):
            success += 1
            print(f"  ✅ {prop_name} ({prop_type})")
        time.sleep(0.3)

    print(f"\n完成: {success}/{len(PROPERTIES)} 个 Property 创建成功")
    return success


def create_character_template(session):
    """创建新版 {{角色}} 模板（含 SMW 标注）"""
    print("\n📝 创建新版 {{角色}} 模板...")

    template_content = """<includeonly><div class="infobox-character" style="float:right; width:300px; margin:0 0 16px 16px; border:1px solid #c0b5a0; background:linear-gradient(135deg, #fdfaf4, #f5ede0); border-radius:10px; overflow:hidden; box-shadow: 0 2px 8px rgba(42,37,32,0.1);">

{{!}} class="infobox-header" style="background:linear-gradient(135deg, #4a6fa5, #3a5a8a); color:#fff; padding:12px 16px; text-align:center;" {{!}}
<div style="font-size:20px; font-weight:bold; letter-spacing:2px;">{{{姓名|{{PAGENAME}}}}}</div>
{{#if:{{{道号|}}}|<div style="font-size:12px; opacity:0.8; margin-top:2px;">道号·{{{道号}}}</div>|}}

{{!}}-
{{#if:{{{图片|}}}|
{{!}} colspan="2" style="text-align:center; padding:10px; background:#f8f3ea;" {{!}} [[File:{{{图片}}}|280px]]
{{!}}-
|}}

{{!}} colspan="2" style="background:#eae4d8; padding:6px 12px; font-weight:bold; font-size:13px; color:#5a4a3a; letter-spacing:1px;" {{!}} ⚔ 基本信息

{{!}}-
{{#if:{{{性别|}}}|
{{!}} style="padding:5px 12px; background:#f5efe5; width:80px; font-weight:600; color:#6a5a4a; font-size:12px;" {{!}} 性别
{{!}} style="padding:5px 12px;" {{!}} {{{性别}}}[[属性:性别::{{{性别}}}| ]]
{{!}}-
|}}
{{#if:{{{字辈|}}}|
{{!}} style="padding:5px 12px; background:#f5efe5; font-weight:600; color:#6a5a4a; font-size:12px;" {{!}} 字辈
{{!}} style="padding:5px 12px;" {{!}} {{{字辈}}}[[属性:字辈::{{{字辈}}}| ]]
{{!}}-
|}}
{{#if:{{{族系|}}}|
{{!}} style="padding:5px 12px; background:#f5efe5; font-weight:600; color:#6a5a4a; font-size:12px;" {{!}} 族系
{{!}} style="padding:5px 12px;" {{!}} {{{族系}}}[[属性:族系::{{{族系}}}| ]]
{{!}}-
|}}
{{#if:{{{世代|}}}|
{{!}} style="padding:5px 12px; background:#f5efe5; font-weight:600; color:#6a5a4a; font-size:12px;" {{!}} 世代
{{!}} style="padding:5px 12px;" {{!}} {{{世代}}}[[属性:世代::{{{世代}}}| ]]
{{!}}-
|}}
{{#if:{{{身份|}}}|
{{!}} style="padding:5px 12px; background:#f5efe5; font-weight:600; color:#6a5a4a; font-size:12px;" {{!}} 身份
{{!}} style="padding:5px 12px;" {{!}} {{{身份}}}[[属性:身份::{{{身份}}}| ]]
{{!}}-
|}}
{{#if:{{{状态|}}}|
{{!}} style="padding:5px 12px; background:#f5efe5; font-weight:600; color:#6a5a4a; font-size:12px;" {{!}} 状态
{{!}} style="padding:5px 12px;" {{!}} {{{状态}}}[[属性:状态::{{{状态}}}| ]]
{{!}}-
|}}

{{#if:{{{修为|}}}|
{{!}} colspan="2" style="background:#eae4d8; padding:6px 12px; font-weight:bold; font-size:13px; color:#5a4a3a; letter-spacing:1px;" {{!}} 🔮 修行档案
{{!}}-
{{!}} style="padding:5px 12px; background:#f5efe5; font-weight:600; color:#6a5a4a; font-size:12px;" {{!}} 修为
{{!}} style="padding:5px 12px; font-weight:600;" {{!}} {{{修为}}}[[属性:修为::{{{修为}}}| ]]
{{!}}-
|}}
{{#if:{{{仙基|}}}|
{{!}} style="padding:5px 12px; background:#f5efe5; font-weight:600; color:#6a5a4a; font-size:12px;" {{!}} 仙基
{{!}} style="padding:5px 12px;" {{!}} {{{仙基}}}[[属性:仙基::{{{仙基}}}| ]]
{{!}}-
|}}
{{#if:{{{命神通|}}}|
{{!}} style="padding:5px 12px; background:#f5efe5; font-weight:600; color:#6a5a4a; font-size:12px;" {{!}} 命神通
{{!}} style="padding:5px 12px; color:#6a4a9a; font-style:italic;" {{!}} {{{命神通}}}[[属性:命神通::{{{命神通}}}| ]]
{{!}}-
|}}
{{#if:{{{道统|}}}|
{{!}} style="padding:5px 12px; background:#f5efe5; font-weight:600; color:#6a5a4a; font-size:12px;" {{!}} 道统
{{!}} style="padding:5px 12px;" {{!}} {{{道统}}}[[属性:道统::{{{道统}}}| ]]
{{!}}-
|}}
{{#if:{{{法器|}}}|
{{!}} style="padding:5px 12px; background:#f5efe5; font-weight:600; color:#6a5a4a; font-size:12px;" {{!}} 法器
{{!}} style="padding:5px 12px; color:#b8923a;" {{!}} {{{法器}}}[[属性:法器::{{{法器}}}| ]]
{{!}}-
|}}

{{#if:{{{父亲|}}}{{{母亲|}}}{{{配偶|}}}{{{子女|}}}|
{{!}} colspan="2" style="background:#eae4d8; padding:6px 12px; font-weight:bold; font-size:13px; color:#5a4a3a; letter-spacing:1px;" {{!}} 🏛 血缘关系
{{!}}-
|}}
{{#if:{{{父亲|}}}|
{{!}} style="padding:5px 12px; background:#f5efe5; font-weight:600; color:#6a5a4a; font-size:12px;" {{!}} 父亲
{{!}} style="padding:5px 12px;" {{!}} [[{{{父亲}}}]][[属性:父亲::{{{父亲}}}| ]]
{{!}}-
|}}
{{#if:{{{嗣父|}}}|
{{!}} style="padding:5px 12px; background:#f5efe5; font-weight:600; color:#6a5a4a; font-size:12px;" {{!}} 嗣父
{{!}} style="padding:5px 12px;" {{!}} [[{{{嗣父}}}]][[属性:嗣父::{{{嗣父}}}| ]]
{{!}}-
|}}
{{#if:{{{母亲|}}}|
{{!}} style="padding:5px 12px; background:#f5efe5; font-weight:600; color:#6a5a4a; font-size:12px;" {{!}} 母亲
{{!}} style="padding:5px 12px;" {{!}} {{{母亲}}}[[属性:母亲::{{{母亲}}}| ]]
{{!}}-
|}}
{{#if:{{{配偶|}}}|
{{!}} style="padding:5px 12px; background:#f5efe5; font-weight:600; color:#6a5a4a; font-size:12px;" {{!}} 配偶
{{!}} style="padding:5px 12px;" {{!}} {{{配偶}}}[[属性:配偶::{{{配偶}}}| ]]
{{!}}-
|}}
{{#if:{{{子女|}}}|
{{!}} style="padding:5px 12px; background:#f5efe5; font-weight:600; color:#6a5a4a; font-size:12px;" {{!}} 子女
{{!}} style="padding:5px 12px;" {{!}} {{{子女}}}[[属性:子女::{{{子女}}}| ]]
{{!}}-
|}}

{{#if:{{{师承|}}}{{{所属势力|}}}|
{{!}} colspan="2" style="background:#eae4d8; padding:6px 12px; font-weight:bold; font-size:13px; color:#5a4a3a; letter-spacing:1px;" {{!}} 📜 其他
{{!}}-
|}}
{{#if:{{{师承|}}}|
{{!}} style="padding:5px 12px; background:#f5efe5; font-weight:600; color:#6a5a4a; font-size:12px;" {{!}} 师承
{{!}} style="padding:5px 12px;" {{!}} {{{师承}}}[[属性:师承::{{{师承}}}| ]]
{{!}}-
|}}
{{#if:{{{所属势力|}}}|
{{!}} style="padding:5px 12px; background:#f5efe5; font-weight:600; color:#6a5a4a; font-size:12px;" {{!}} 所属势力
{{!}} style="padding:5px 12px;" {{!}} [[{{{所属势力}}}]][[属性:所属势力::{{{所属势力}}}| ]]
{{!}}-
|}}
{{#if:{{{首次出场|}}}|
{{!}} style="padding:5px 12px; background:#f5efe5; font-weight:600; color:#6a5a4a; font-size:12px;" {{!}} 首次出场
{{!}} style="padding:5px 12px;" {{!}} {{{首次出场}}}[[属性:首次出场::{{{首次出场}}}| ]]
{{!}}-
|}}
{{#if:{{{结局|}}}|
{{!}} style="padding:5px 12px; background:#f5efe5; font-weight:600; color:#6a5a4a; font-size:12px;" {{!}} 结局
{{!}} style="padding:5px 12px; color:#a04a4a; font-size:12px;" {{!}} {{{结局}}}[[属性:结局::{{{结局}}}| ]]
{{!}}-
|}}

{{!}} colspan="2" style="background:linear-gradient(135deg, #4a6fa5, #3a5a8a); padding:6px; text-align:center;" {{!}} <span style="color:#fff; font-size:10px; opacity:0.7;">玄鉴仙族 · 望月李氏</span>

{{!}}}

[[属性:姓名::{{PAGENAME}}| ]]
{{#if:{{{道号|}}}|[[属性:道号::{{{道号}}}| ]]|}}
[[Category:角色]]{{#if:{{{族系|}}}|[[Category:{{{族系}}}]]|}}{{#if:{{{世代|}}}|[[Category:{{{世代}}}]]|}}</includeonly><noinclude>
== 角色信息框模板 ==

=== 使用方法 ===
<pre>
{{角色
|姓名=李周巍
|性别=男
|字辈=周
|族系=望月李氏·伯脉
|世代=十四世
|身份=现任家主、魏王
|状态=存活
|修为=紫府后期
|仙基=煌元关
|命神通=谒天门
|道统=明华煌元经
|法器=长戟大昇、华阳王钺
|道号=明煌
|父亲=李承辽
|母亲=胡氏
|配偶=许佩玉、安氏、陈氏、田氏
|子女=[[李绛遨]]、[[李绛迁]]、[[李绛垄]]、[[李绛夏]]、[[李绛梁]]、[[李绛年]]
|师承=
|所属势力=望月李氏
|首次出场=
|结局=
|图片=人设图_李周巍.jpg
}}
</pre>

=== 支持的 SMW Property ===
此模板自动为以下字段设置语义标注：
* 姓名、性别、字辈、族系、世代、身份、状态
* 修为、仙基、命神通、道统、法器、道号
* 父亲、嗣父、母亲、配偶、子女
* 师承、所属势力、首次出场、结局

使用 <code><nowiki>{{#ask:}}</nowiki></code> 可以查询，例如：
* 所有紫府角色: <code><nowiki>{{#ask:[[属性:修为::~*紫府*]]|?修为|?族系}}</nowiki></code>
* 伯脉所有角色: <code><nowiki>{{#ask:[[属性:族系::望月李氏·伯脉]]|?世代|?修为}}</nowiki></code>

[[Category:模板]]
</noinclude>"""

    if create_page(session, "Template:角色", template_content, "重写角色模板: 模块化 Infobox + SMW 语义标注"):
        print("  ✅ Template:角色 更新成功")
        return True
    return False


def main():
    print("=" * 60)
    print("玄鉴 Wiki · SMW Property 体系 + 模板重写")
    print("=" * 60)

    session = get_session()

    # 1. 创建 Property 页面
    create_properties(session)

    # 2. 重写角色模板
    create_character_template(session)

    print("\n" + "=" * 60)
    print("✅ 全部完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
