# 法宝 Wiki 工程 · WORKFLOW SOP

> 整合：内容生产 / 上传发布 / 品阶核对 / 多 Agent 协作 / 阻塞恢复
>
> 最近更新：2026-05-12 12:03（§2 增加专项规范链接；§7 更新遗留状态）

---

## 0. 项目结构速查

唯一权威源：`pages/{NN-类型}/{实体名}.wiki`（449 页）
写作规范：`docs/`（内链规范 / 分类判定 / wiki 模板）
长期记忆：`.workbuddy/memory/MEMORY.md`
每日日志：`.workbuddy/memory/YYYY-MM-DD.md`
工程脚本：`.workbuddy/wide_window/`
原文 context：`.workbuddy/wide_window/context/{品类}/{实体}/context.txt`
上传脚本：`/Users/leoshi/AIBOOK/xuanjian/wiki/scripts/upload_pages.py`
凭证：`/Users/leoshi/AIBOOK/xuanjian/wiki/.env`（WIKI_USER, WIKI_PASS）

---

## 1. 内容生产工作流

```
原著章节
    ↓
.workbuddy/wide_window/context/{品类}/{实体}/context.txt   （宽窗：每次提及 ±500 字）
    ↓
单页深度推理（Agent 或人工，约 3 min/页）
    ↓
pages/{NN-类型}/L{层级}-{实体名}.wiki                       （唯一权威源）
    ↓
品阶三同步检查（info 表 / 首句 / Category）
    ↓
QA 抽样（每批 10%）
    ↓
上传 MediaWiki
```

### 单页内容标准
- **基本信息表**：品阶、道统、出现章节、相关人物
- **名字由来**：每字拆解 + 整体语义推测
- **功能与威能**：原文证据 + 提炼（不可机械复读）
- **外观**：原文描述
- **历史**：出场场景
- **相关实体**：内链规范 v1（详见 `docs/内链规范.md`）
- **原文引用**：3 条以上，带章节注释
- **道统标记**：✅ 明确 / ⚡ 推断 / ❓ 未知

---

## 2. 品阶三同步铁律（P0）

每页必须三处一致：

1. **info 表**：`|品阶 = 紫府灵物`
2. **首句**：`'''XX''' 是《玄鉴仙族》中的[[紫府灵物]]。`
3. **Category**：`[[Category:紫府灵物]]`

**核对清单**：
- [ ] 三处品阶字符串完全一致
- [ ] 与原文证据匹配（判定方法见下方专项规范）
- [ ] 与目录品类不冲突（如冲突，以原文为准）

> **品阶/道统判定专项规范**：如何从宽窗 context 提取证据、证据分级（✅/⚡/⚡⚠️/❓）、三大禁止行为（名面联想/上位泛化/推理标✅）、案例对照，详见 `docs/workflow-基本信息更新工作规范.md`（v3.1）。

**已知坑**：目录品类 ≠ 原文品阶。早期修正过 4 处错误（戊咲珠/缡刃/牝水/飞玄乱石）。

### 品阶并列推断规则
- 原文出现"X、Y、Z"且 Y/Z 已知品阶时，X **可推断为同品阶**
- 但单独出现"X 与 Y" 不足以推断（如大夏郢铜甲案例）
- 推断品阶用 ⚡ 标注，不可用 ✅

---

## 3. 上传发布 SOP

### 标准上传命令

```bash
cd /Users/leoshi/AIBOOK/xuanjian/wiki
set -a && source .env && set +a
python3 scripts/upload_pages.py \
    --only "资料库-法宝:道具:灵资/pages" \
    --summary "xxx 批次升级"
```

### 关键参数
| 参数 | 用途 |
|---|---|
| `--prefix 造物-` | 默认前缀（造物类）— 已是默认，可省略 |
| `--prefix-map 20-人物=人物-` | 子目录映射前缀（人物目录）— 已是默认 |
| `--no-prefix` | 恢复裸 stem 模式（不推荐） |
| `--force` | 覆盖冲突 |
| `--dry-run` | 预览不写入 |
| `--only PATH` | 仅上传指定子路径 |

### 上传前检查清单
- [ ] `pages/` 是最新版本（修改后立刻准备上传）
- [ ] `--dry-run` 验证标题正确（应显示 `造物-` / `人物-` 前缀）
- [ ] `.env` 已 source（环境变量 WIKI_USER 已设置）
- [ ] 无文件名带 L 前缀残留（`ls pages/*/L*` 应为空）

### 上传后验证
- 抽查 3-5 页线上内容
- 确认前缀正确：`造物-XX` 而非 `XX` 或 `L4-XX`
- 检查 Category 链接

### 已修复的坑（防再犯）
1. **裸名 + 前缀双副本**：旧版用 `path.stem` 当标题，已修复为目录映射
2. **L 前缀进标题**：`L4-万煞贯金刀` 当标题，已批量改名 + 删除旧页
3. **upload_staging/ 死分支**：曾经的中间快照，已删除，**不要再创建**

---

## 4. 多 Agent 协作 SOP

### 上限：3 个并发
> 超过 3 个会出现僵尸 agent + context 膨胀 + 决策退化。**硬上限**。

### 标准流程
```
TeamCreate（批次明确，每 agent 5-12 页，无重叠）
    ↓
3 agent 并行执行
    ↓
各自完成后 SendMessage 上报
    ↓
主理人 Review → 上传
    ↓
TeamDelete（清理）
```

### 任务分配原则
- **无重叠**：每页只属于一个 agent
- **明确边界**：明确 "Agent A 负责 #1-#10, Agent B 负责 #11-#20"
- **同质批次**：同一批次的 agent 处理同品类/同频次层

### 阻塞恢复协议（5 条规则）
1. **TeamDelete 前必须先 ToolSearch 查 schema**（避免 "additional properties" 错误）
2. **shutdown_request 不等待确认**：直接 TeamDelete
3. **Agent 创建失败 3 次** → 上报用户，不再重试
4. **直接执行**是正式后备方案，不是 SOP 违规
5. **Context 膨胀**（>40 turns 切换策略）→ 立即收尾，下轮重启

### 批次过渡检查清单（7 项）
- [ ] 上一批所有 agent 已 SendMessage 上报完成
- [ ] 上一批所有 agent 进程已退出
- [ ] TeamDelete 已成功执行
- [ ] team_name 在系统中无残留
- [ ] 主理人 context 在合理范围（<30 turns）
- [ ] 下一批任务清单已写入文档
- [ ] 下一批 TeamCreate 参数已准备

---

## 5. Rescue 批次模板（精修浅页）

### 适用场景
- L4-L6 浅页需要补足深度
- 或线上发现品阶/道统错误

### 模板
```
1. 圈定批次（24 页一组，按频次或品类）
2. 写入 .workbuddy/memory/rescueN-plan.md（任务清单 + agent 分配）
3. TeamCreate
4. 3 agent 并行升级
5. 各 agent 完成后 SendMessage 上报
6. 抽查 10% 验证质量
7. 上传 + 线上验证
8. TeamDelete
9. 写入 .workbuddy/memory/YYYY-MM-DD.md（结果归档）
```

### Rescue 质量评级
- ⭐⭐⭐ 高质量：原文引用 3+ / 名字由来逐字 + 整体 / 功能威能 3+ / 外观 / 相关实体 3 类
- ⭐⭐ 中等：原文 + 名字 + 功能（部分待揭示）
- ⭐ 低质量：机械复读 / 无提炼 / 字段缺失

**目标**：每批 75% 达 ⭐⭐ 及以上。

---

## 6. QA 检查

### 道统白名单校验
```bash
python3 .workbuddy/wide_window/qa_check.py
```

### 抽查清单
- [ ] 品阶三同步（10% 抽样）
- [ ] 道统标记规范（✅/⚡/❓）
- [ ] 内链格式（`[[造物-XX]]` 等）
- [ ] 原文引用条数 ≥ 3
- [ ] 文件名 ≠ 标题（脱 L 前缀）
- [ ] Category 链接有效

---

## 7. 已知遗留与待办（按优先级）

| 优先级 | 事项 | 量级 | 状态 |
|--------|------|------|------|
| P1 | 中频遗漏实体 Batch 2（7个）+ Batch 3（2个）评估/补录 | 9个 | ⏳ 待办 |
| P2 | L6（仅 1 次提及）维持机械底版 | 155 页 | ⏳ 维持 |
| P2 | 内链补全（造物→人物→道统→家族） | 全量 | ⏳ 待办 |
| P3 | 高价值专题页（太阴道/李家世系/仙鉴/月华元府等） | 5-10 个 | ⏳ 待办 |
| P3 | 横向扩展：势力/神通/事件三大维度 | — | ⏳ 待办 |
| — | ~~B15 脚本批次功能机械复读~~ | ~12 页 | ✅ 2026-05-11 完成 |
| — | ~~跨命名空间消歧~~ | 7 个 | ✅ 2026-05-11 完成 |
| — | ~~9个品阶体系专题页批量生成~~ | 灵气/灵物/灵资/丹药/法器/灵器/符箓/材料/凡器 | ✅ 2026-05-11 完成 |
| — | ~~中频遗漏 Batch 1 补录+审计~~ | 10个 | ✅ 2026-05-12 完成 |

---

## 8. 文件维护规则

### 不要做
- ❌ 不要重建 `upload_staging/`（已废弃死分支）
- ❌ 不要修改 `archive/` 内容（只读归档）
- ❌ 不要在 `pages/` 用 `path.stem` 直接当标题（必须经上传脚本前缀映射）
- ❌ 不要超过 3 个 agent 并发

### 必须做
- ✅ 修改 `pages/` 后立刻准备上传（避免本地 / 线上分裂）
- ✅ 完成批次后写入当日 daily log（`.workbuddy/memory/YYYY-MM-DD.md`）
- ✅ 长期事实（用户偏好/项目约定）写入 `MEMORY.md`
- ✅ 重要决策必须有原文证据（无证据用 ❓）

---

## 9. 一句话速查

| 场景 | 命令 |
|---|---|
| 上传所有 pages | `cd ../.. && set -a && source .env && set +a && python3 scripts/upload_pages.py --only "资料库-法宝:道具:灵资/pages" --summary "xxx"` |
| 上传单子目录 | 同上 + `--only ".../pages/01-灵气"` |
| 预览不写 | 加 `--dry-run` |
| 强制覆盖 | 加 `--force` |
| 道统校验 | `python3 .workbuddy/wide_window/qa_check.py` |
| 看长期记忆 | `cat .workbuddy/memory/MEMORY.md` |
| 看今日日志 | `cat .workbuddy/memory/$(date +%Y-%m-%d).md` |
