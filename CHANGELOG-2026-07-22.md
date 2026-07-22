# 项目变更记录（2026-07-22 重大升级）

本文件备份自 `/Users/leoshi/AIBOOK/Book_download/knowledge_base/.workbuddy/memory/2026-07-22.md`，供 `xuanjian/wiki` 工作区直接查阅。

---

## 1. wiki 仓库 README 精简

- 删除「仓库清理与远程同步（2026-07-06）」整个章节（工蜂 origin + GitHub github 双仓库描述）
- 代码仓库仅保留 GitHub: https://github.com/mizar0223/xuanjian-wiki
- 文件: `/Users/leoshi/AIBOOK/xuanjian/wiki/README.md`

---

## 2. git 提交收尾（wiki 仓库）

- 初始误操作: `git add -A` 落在 `book_download_tool` 仓库，commit 了 2254 个文件（含 knowledge_base 中间产物）
- 已撤销: `git reset --mixed HEAD~1`，`book_download` 仓库恢复原状
- wiki 仓库正确提交: `b402485`，3027 文件 changed，39074 insertions(+)，13848 删除(-)
- 已推送 GitHub: `github/main` 与本地 `main` 同步
- Commit 内容: 人物维度全量增丰回写（1263 derived → wiki）+ `人物与势力/` → `人物/` 目录迁移 + `势力/` 独立目录拆分 + SMW 配置 + 紫府索引页 + README 工蜂章节删除

### 教训
- Bash 工具工作目录不跨调用持久（或容易搞混），wiki 仓库操作**必须**每条命令前缀 `cd /Users/leoshi/AIBOOK/xuanjian/wiki &&`
- `git add -A` 在有多层 git 仓库嵌套时风险极高，宁可分路径 add

---

## 3. 金丹人物 grep 原著反查（漏收验证）

- 方法：grep 原著 `玄鉴仙族_完整版_清洗版_到1535章.txt` 金丹级称号（真君/魔君/帝君/飞君/神君/玄君/龙君），硬虚词过滤 + 已知关联 + wiki 页比对
- 根因：金丹 tracker（105 人）从 wiki 人物页派生，无页 = 天然漏收
- 结果：清洗后 161 独特称号串 / 362 命中；排除已知收录后 A 类真实候选 50 个
  - 6 个**有 wiki 页却未收录**（须相真君、北嘉龙君、晞阳龙君、太昱真君、李通崖真君、太益真君）→ 可直接补进金丹名单
  - 44 个**完全无 wiki 页**（少阴玄君、道阳真君、少阳魔君、妙道化生真君、垣下真君、大照帝君、上曜真君、上妙翃外飞君、昭元真君、持琅、持敻、长塘...）→ 需先建页才能进管线
- 注：候选含已知人物称号全称/异体（清元渌水 ≈ 渌水、先天玄候 = 先天玄侯），需人工核对去假
- 脚本 `/tmp/grep_jindan_titles.py`，输出 `/tmp/jindan_gap.txt`
- 待决策：漏收人物是否补名单/建页（高频 少阴 16 / 道阳 9 / 少阳 8 优先）

---

## 4. 金丹漏收人物核验 + 基础页建设（17:02-17:10）

- 用户确认 12 个无页 + 5 个"有页"漏收人物。逐项原著 + 别名库 + clean_json 核验，**重大碰撞发现**：
  - **道阳真君 = 蒋清**（原文「道阳真君蒋清」「正是蒋清临死前的算计」）→ 已在 Wave1，不建页
  - **少阳魔君 = 蒯离**（别名库已录，蒯离有页）→ 不建页
  - **妙道化生真君 = 牝水娘娘**（别名库已录，牝水娘娘有页）→ 不建页
  - **上曜真君 = 崔彦**（原文「上曜真君崔彦」「落款博野崔彦」；崔彦确有页，且正在 Wave1 跑）→ 不建页
  - **5 个"有页"实际只有 2 个真有页**：须相真君 ✓、太昱真君 ✓；**北嘉龙君/晞阳龙君/太益真君 实际无页**（v4 检测误报）→ 归入建页
- **最终处置**：
  - 新建基础页 **11 人**（derived JSON + 渲染 .wiki）：少阴玄君、垣下真君、大照帝君、上妙翃外飞君、昭元真君、持琅真君、持敻真君、长塘玄君、北嘉龙君、晞阳龙君、太益真君
  - 仅入 tracker（已有页）：须相真君、太昱真君
  - 跳过（别名碰撞 4 人）：道阳真君 = 蒋清、少阳魔君 = 蒯离、妙道化生真君 = 牝水娘娘、上曜真君 = 崔彦
- 建页方法：`wiki_json/clean_json/人物/<path>/<name>_derived.json`（schema 3.2） → `tools/render_derived_to_wiki.py <derived> --out pages/人物/<name>.wiki`
  - 路径规范：龙属 → `人物/妖类异族/螭属/`；三玄系 → `人物/三玄道统/`；其余 → `人物/金丹道统/`
  - 修为：均为金丹，长塘玄君后得仙君之号 → 标仙君；龙君种族 = 妖 → infobox 身份 = 妖
  - 基础页仅填原著可确认字段，其余待增丰补全
  - 脚本 `/tmp/build_jindan_pages.py`（可复用）
- **chunks 来源澄清**：prescreen 从 `data/chunks.json`（原著全量分块）按名检索，人物名出现在原著即有 chunks，与是否有 wiki 页无关。故建好页 + 入 tracker 后 chunks 自动流入。
- 待办（Wave1 跑完后）：将 11 新页 + 须相/太昱 并入金丹增丰名单（task #8），chunks 自动算。

---

## 5. 金丹尊号补记（顺手补齐，17:14）

- 用户要求：① 少阴/大照标注"传世功法署名、疑似上古非明确个体"；② 给 4 碰撞角色补记金丹称号便于检索互通
- ① 少阴玄君/大照帝君：建页时 lead 已写"上古修士，传世功法《X》...其余生平待考" → 已满足，无需改
- ② 4 角色核验修正（重要）：grep 按"称号字符串"匹配页名（页名用真名）造成**误报**——蒯离（道号=少阳魔君）、牝水娘娘（道号=妙道化生真君）的 wiki 页**早已正确标尊号**，非漏收
  - 真需补的是 **蒋清**（原道号=道阳，补 `真君号=道阳真君`）、**崔彦**（原 lead 写"上曜"但 infobox 无，补 `道号=上曜` + `真君号=上曜真君`）
  - **字段标准更正（17:20 Leo 指示）**：金丹级尊称用「**真君号**」字段，「真人号」留给紫府真人级（如素韫真人）；已扩展 schema v3.2（新增真君号，optional） + render_derived_to_wiki.py（优先展示真君号于道号括号）
  - 渲染：`道号=道阳（道阳真君）` / `道号=上曜（上曜真君）`，括号由真君号驱动
- **entity_aliases.json 检索归一**：新增 蒋清←道阳真君、崔彦←上曜真君；蒯离←少阳魔君、牝水娘娘←妙道化生真君 **原本已在别名库**（顶层检查误判）
  - 格式：`aliases[canonical] = {canonical, alias: [尊号], note, stats: {canonical: 0, 尊号: 频次}}`
  - 效果：搜"道阳真君/上曜真君"等称号可归一到真名，检索互通达成
- infobox 字段坑：简单字段（道号/真人号）是 **string** 不是 dict；render 对 dict 会整串 str() 出来（首次 patch 踩坑，已改 string 重渲）

---

## 6. 太鸿真君修复 + Wave1 收尾（17:23）

- 太鸿真君 assemble 失败根因：`04_final.json` 顶层是 **list** 非 dict（OUTPUT 阶段 LLM 异常，原文稀薄典型症状）
- 修复：备份坏 `04_final.json` → `/tmp`，删 `output.ckpt`，重跑 OUTPUT（22.9s，¥0.003，仅重抽 1 阶段，discover/cross/verify 复用 checkpoint 跳过） + assemble → PASS，final 落盘
- **Wave1 现 0 失败、干净收尾**：21 人全处理，18 人新落 final + 3 人已有 final 跳过（慕容夏/著埵/怒目四魔帝剎相）
- ⚠️ 太鸿真君是**空壳**（事件 0 / 关系 0 / 神通 0 / 法宝 0），原文极稀薄；audit 阶段会标空壳，需后续决定保留/补抽/标记跳过
- 注：真君号字段标准更正（17:20）已落 schema/render/蒋清崔彦两页；本批次 21 人 final 仍用旧"真人号"字段（蒋清/崔彦的 derived 已改真君号，但 final 由 llm_enrich 生成未回填真君号——回写 wiki 前需把真君号同步进 final 或 render 时才生效；待确认回写流程是否读 derived 还是 final）

---

## 7. audit 质检 + 3 人 parse_failed 修复（17:28）

- `audit_final_batch.py --batch jindan_w1`：初检 10/21 异常，发现 **3 人 `_parse_failed=True`**（拓跋玄郯/崔彦/太鸿真君），`_raw` 含思考过程但 JSON 被截断（拓跋 raw_len=515 只有 tool_calls 头部）
- 根因：OUTPUT 阶段 prompt 未禁思考过程，LLM 输出大段"我来组装…"文本后 JSON 被截断
- 修复：① 改 `llm_enrich_agent.py` 的 `stage_output` extra + `OUTPUT_USR`，显式要求"直接输出 JSON，禁止思考过程/markdown"；② 3 人清 `output.ckpt` 重跑 OUTPUT（拓跋 4806t / 崔彦 4590t / 太鸿 4266t） + assemble
- 结果：拓跋玄郯/崔彦修复（assemble PASS，事件/关系/法宝均抽出）；太鸿真君事件 0→3 但关系仍 0（原文稀薄）
- 复检：异常 10→8。剩余 8 人多为**原文稀薄真空壳**（玄沧真君 0 关系 0 事件、真璀玄君/逍金真君/怒目四魔帝剎相 0 关系、蒋清/张元禹 0 事件），非流程 bug；杜青道统待考
- 待决策：8 人空壳保留/补抽/标记跳过（历史做法：保留占位或确认原文无料后跳过）

---

## 8. 8 人别名归类 + 空壳修复（18:02）

- 用户提示：8 异常人物可按称号归类（蒋清=道阳真君、张元禹=太元真君、杜青=渌水真君），用推理 + grep 原文 + 查 JSON 确定
- **关键发现**：别名库缺杜青"渌水真君"（原文 21 次 vs 已有"太青真君"1 次），导致 prescreen 只召回 36 chunks（真名 + 太青真君），漏了渌水真君的 12 chunks
- 修复：① 补杜青别名"渌水真君"；② 杜青/张元禹/蒋清清 checkpoint 重跑全管线；③ 剩余 5 空壳（真璀玄君/太鸿真君/玄沧真君/逍金真君/怒目四魔帝剎相）也重跑
- 结果：audit 8→4 异常。修复 4 人：杜青（神通 0→4 / 法宝 0→2 / 关系 0→6 / 事件 0→3）、张元禹（事件 0→3）、蒋清（关系 4→6 / 事件 0→4）、逍金真君（关系 0→1）
- **剩余 4 空壳**（chunks 5-7，原文确实极稀薄）：真璀玄君（0 关系 0 事件）、太鸿真君（1 关系 0 事件）、玄沧真君（0 关系 4 事件）、怒目四魔帝剎相（6 关系 0 事件，法相豁免神通）
- 根因：金丹级但戏份极少，LLM 重跑后结构正确但填不出内容——按历史做法保留占位或标记跳过

---

## 9. 4 空壳保留占位 + 金丹 dashboard 刷新（18:41）

- 用户决策：4 空壳（真璀玄君/太鸿真君/玄沧真君/怒目四魔帝剎相）**保留占位**
- 刷新金丹 tracker：`tools/gen_enrichment_tracker.py --tier jindan` → 108 独立人物（合并 6 重复），已增丰 41，剩余 67
- 创建金丹 dashboard：`enrichment_dashboard_jindan.html`（基于通用版改数据源 `enrichment_tracker_jindan_display.json` + 字段 `total_金丹` + 标题"金丹人物增丰看板"）
- 启动服务器：tmux 会话 `dashboard` 跑 `python3 -m http.server 8137`（nohup 在 macOS shell 退出时杀进程，改 tmux 持久）
- 访问地址：`http://127.0.0.1:8137/enrichment_dashboard_jindan.html`，数据加载验证通过（108 总计 / 41 已增丰 / 67 剩余）

---

## 10. 3 对重复人物合并（19:09）

- 用户发现：道青 JSON 里有"法相玄名怒目四魔帝剎相"，说明**道青 = 怒目四魔帝剎相**（怒目四魔帝剎相是道青的法相玄名），两 JSON 应合并
- 系统扫描所有 final 的 lead 里的别名线索（法号/道号/真人号/真君号/尊号/法相玄名），找应合并的重复：
  - **道青 = 怒目四魔帝剎相**（法相玄名双向确认，合并到道青，关系 1→7）
  - **张元禹 = 善青道人**（lead 明确"张元禹...又称善青道人"，都是金丹真君/兑金果位主人，合并到张元禹，事件 3→4 / 关系 3→4）
  - **素免真人 = 齐真人**（都是玄妙观之主/道号素免/宝土道统，修为中期 vs 初期是不同时间点描述，合并到素免真人，事件 5→7 / 关系 4→7）
- 合并策略：以信息更全的为主，合并关系/事件（去重），补别名到 infobox，删除被合并的 final，补 entity_aliases.json
- 刷新 tracker：已增丰 41→40（合并删除 1 个），剩余 67→68
- 别名库已补 3 条：道青←怒目四魔帝剎相、张元禹←善青道人、素免真人←齐真人

---

## 11. SMW 属性标注冗余问题修复（18:30-19:20）

**根因**：`Template:角色` 使用了错误的 `[[属性:道统::...]]` SMW 语法，MW 1.42 + SMW 5.0.2 下被当作普通内链输出，导致页面上 `[[属性:道统::离火| ]]` 源码裸露。

**修复步骤**：
1. **模板止血**：移除 `Template:角色` 中所有 `[[属性:...]]` 和 `[[property::...]]` 内联包装，让渲染器直接输出完整标注。
2. **渲染器升级**：`/Users/leoshi/AIBOOK/Book_download/knowledge_base/tools/render_derived_to_wiki.py` v2
   - `linkify`/`linkify_multi` 新增 `smw_prop` 参数
   - infobox 字段生成 `[[NS-target|text]][[property::text| ]]`
   - 修为字段补 `[[修为::紫府前期| ]]`（紫府索引查询依赖）
3. **批量刷新 + 上传**：1276/1276 重新渲染，1281/1283 上传成功（2 冲突已强制覆盖），0 失败。
4. **索引页修复**：紫府人物 #ask 查询从 `[[属性:修为::~*紫府*]]` 改为 `[[修为::~*紫府*]]`。
5. **rebuildData**：运行两次 SMW `rebuildData.php`（~6366 IDs），紫府人物索引从 0 位恢复到 **296 位**。
6. **配置修复**：`wiki/config.yaml` 的 api/url 改为 `https://`，避免 API 301 返回 HTML 导致 JSON decode 失败。

**待跟进**：紫府人物 296 vs 之前 309 差 13 人，需排查是修为字段未含"紫府"、页面未上传还是其他原因。

---

## 相关文件路径

- 渲染器：`/Users/leoshi/AIBOOK/Book_download/knowledge_base/tools/render_derived_to_wiki.py`
- wiki 配置：`/Users/leoshi/AIBOOK/xuanjian/wiki/config.yaml`
- 紫府索引：`/Users/leoshi/AIBOOK/xuanjian/wiki/pages/索引/紫府人物.wiki`
- 金丹 dashboard：`/Users/leoshi/AIBOOK/Book_download/knowledge_base/enrichment_dashboard_jindan.html`
- 原始记忆：`/Users/leoshi/AIBOOK/Book_download/knowledge_base/.workbuddy/memory/2026-07-22.md`
