# 宽窗考据工程 · 工作流文档 v2.0

> **目标**: 对375个法宝/道具/灵资实体，使用宽窗上下文拼接+LLM深度推理，产出高质量Wiki页面
> **驱动文件**: workstate.json（断点恢复）、batch_extractor.py（阶段1）、Agent任务包裹（阶段2）

---

## 目录结构

```
.workbuddy/wide_window/
├── workflow.md              ← 本文件
├── workstate.json           ← 全局状态机（断点恢复核心）
├── batch_extractor.py       ← 阶段1: 批量宽窗提取
├── agent_tasks/             ← 阶段2: Agent任务包裹
│   ├── batch_B01.json       ← 批次1: 华阳王钺等6个高频
│   ├── batch_B02.json
│   └── ...
├── context/                 ← 宽窗产出
│   ├── 灵资/
│   │   ├── 颈下羽/
│   │   │   ├── context.txt
│   │   │   └── meta.json
│   │   └── ...
│   ├── 灵物/
│   ├── 灵器/
│   ├── 灵宝/
│   ├── 法宝/
│   ├── 筑基法器/
│   ├── 材料/
│   ├── 丹药/
│   ├── 剑道/
│   ├── 符箓/
│   ├── 位别/
│   └── 待分类/
├── output_wiki/             ← 阶段2: Wiki页面产出
└── reference/               ← 参考数据（规则表、模板、JSON）
```

---

## 三阶段流水线

### 阶段1: 宽窗提取

```
执行: python3 batch_extractor.py
输入: 375个实体名 + 39个原著txt
输出: context/{品类}/{实体}/context.txt + meta.json
状态: workstate.json → entity_registry[实体名].extraction = "done"
```

**特性**:
- 断点恢复: 跳过已标记"done"的实体
- 增量保存: 每10个实体刷新workstate.json
- 品类自动分类: 基于名字关键词+预标注映射表
- 窗口参数: 前500字+后500字, overlap>80%合并

### 阶段2: Agent批次推理

```
执行: 分派Agent，每批次5-10个实体
输入: context/{实体}/context.txt + reference/规则表
输出: output_wiki/造物-{实体}.wiki
状态: workstate.json → entity_registry[实体名].reasoning = "done"
```

**批次划分规则**:
- L1批次 (5-6个/Agent): 提及≥50次的高频实体
- L2批次 (8-10个/Agent): 提及5-49次的中频实体
- L3批次 (15-20个/Agent): 提及<5次的低频实体

**Agent推理Prompt结构**:
1. 系统指令: 你是法宝考据专家...
2. 规则嵌入: 分类判定规则表(压缩版) + 五德位业体系(道统名称+位置关系)
3. 上下文: 该批次的全部context.txt拼接
4. 模板: {{造物}} Wiki模板
5. 输出约束: 12维度JSON格式, 每项附原文举证

### 阶段3: Wiki上传

```
执行: python3 scripts/upload_pages.py
输入: output_wiki/*.wiki
输出: MediaWiki页面
状态: workstate.json → entity_registry[实体名].uploaded = true
```

---

## workstate.json 状态机

```json
{
  "version": "2.0",
  "created": "ISO时间",
  "updated": "ISO时间",
  "total_entities": 375,
  "stages": {
    "extraction": {"status": "in_progress|completed", "completed_at": null},
    "reasoning": {"status": "pending", "batches_planned": 0, "batches_done": 0},
    "upload": {"status": "pending"}
  },
  "entity_registry": {
    "颈下羽": {
      "category": "灵资",
      "extraction": "pending|done|failed",
      "context_path": "context/灵资/颈下羽/context.txt",
      "reasoning": "pending|batched|done|failed",
      "reasoning_batch": "B03",
      "wiki_output": null,
      "uploaded": false
    }
  },
  "batches": [
    {
      "batch_id": "B01",
      "entities": ["华阳王钺", "三候戍玄火", ...],
      "agent_id": null,
      "status": "planned|assigned|done|failed",
      "assigned_at": null,
      "completed_at": null
    }
  ]
}
```

### 断点恢复流程

```
1. 读取 workstate.json
2. 筛选 extraction == "pending" → 执行阶段1
3. 筛选 reasoning == "pending" → 规划批次，生成agent_tasks/
4. 筛选 reasoning == "batched" → 等待Agent完成
5. 筛选 uploaded == false → 执行阶段3
```

---

## 工程约定

1. **所有路径用绝对路径**，不依赖工作目录
2. **Python脚本可重复运行**，幂等操作
3. **workstate.json是唯一真相源**，不要手工修改
4. **每阶段完成后标记stages.{stage}.status = "completed"**
5. **失败实体标记extraction/reasoning = "failed"并记录错误信息**
6. **Agent任务包裹独立存储**，格式: agent_tasks/batch_{BXX}.json

---

## 当前进度

| 阶段 | 状态 | 备注 |
|------|------|------|
| 阶段0 | ✅ 完成 | 分类规则表+Wiki模板+POC(颈下羽)验证 |
| 阶段1 | ✅ 完成 | 375实体全量宽窗提取(7.1MB) |
| 阶段2 | ✅ 完成 | L1-L3 45页全部深度化，L4-L6 330页机械底版 |
| 阶段3 | ⏳ 待执行 | 待上传MediaWiki |

---

## 🔥 实战教训（2026-05-09 终盘）

### 教训1: Agent并行上限

**现象**：同时开启10+个fork agent，导致模型严重混乱——大部分agent"完成"但从不写文件，少数产生幻觉性道统标注（如辛酉渌泽印→府水）。

**根因**：fork模式下每个agent继承全部会话上下文（数万字），reasoning模型将大部分轮次消耗在"理解上下文"而非"读文件→写产出"。超过5个并行agent后，系统级资源竞争导致不可靠。

**规则**：
- **单轮并行上限: 3个agent**
- **L1高频（≥50次）: 1个/轮**，手工深度推理
- **L2中频（5-49次）: 2-3个/轮**，用default模型+独立短上下文
- **L3低频（<5次）: 不用agent**，机械填充即可

### 教训2: 必须增加QA核对环节

**现象**：机械填充脚本的 `guess_daotong()` 硬编码字典出现人为错误——'辛酉渌泽印'被错标为'府水'，名中"渌"字即为渌水道统标帜。该错误经备份恢复二次传播，直到用户手动抽查才发现。

**根因**：生成流水线中**没有任何自动核对环节**——产出即交付，没有回归原文验证。

**QA规则（必须执行）**：
1. **名字自证优先**：实体名含渌/明阳/离火/庚金等道统标帜字 → 自动绑定对应道统，无需查上下文
2. **高频实体（≥50次）强制人工复核**：每个页面需读context验证道统+品阶
3. **批量产出手工抽检**：每轮生成后随机抽5页，逐页对context做difference check
4. **道统白名单验证**：产出后跑脚本，`名字含渌 → 道统!=渌水` 的自动标红

### 教训3: 生成器必须有文件保护

**现象**：`batch_wiki_generator.py` 无条件覆盖已有文件，导致B03 agent推理产出（六丁并火令7.6KB/大雪绝锋7.6KB）被机械底版（1.2KB）覆写，深度内容永久丢失。幸有 `output_wiki/` 旧备份恢复了12页。

**修复**：已在生成器中加入保护逻辑——
```python
if os.path.exists(op) and os.path.getsize(op) > 3000:
    continue  # 跳过已有深度页面
```

### 教训4: 保留旧备份目录

`output_wiki/` 是旧版Agent产出的31页备份，在本次灾难中抢救了B01/B03/B04共19页。**该目录设为只读保护区**，禁止任何脚本写入。

### 新工作流

```
阶段1: 宽窗提取 (batch_extractor.py)
         ↓
阶段2a: 名字自证匹配 → 道统自动标注
         ↓
阶段2b: 机械填充所有实体 (batch_wiki_generator.py, 带3KB保护)
         ↓
阶段2c: 手工深度推理 (每轮≤3个高频实体，读context→产出→QA核对)
         ↓
阶段2d: QA核对 (道统白名单+随机抽检+高频全检)
         ↓
阶段3: 上传Wiki
```

---

*最后更新: 2026-05-09 21:54*
