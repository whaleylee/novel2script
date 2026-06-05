# Novel2Script YAML Schema 规范文档

> 定义剧本 YAML 的完整结构、设计原因、以及各字段的约束与扩展规则。

---

## 目录

1. [设计理念](#1-设计理念)
2. [整体结构](#2-整体结构)
3. [根对象](#3-根对象)
4. [script 元信息](#4-script-元信息)
5. [metadata 制作元数据](#5-metadata-制作元数据)
6. [characters 角色定义](#6-characters-角色定义)
7. [act_structure 幕结构](#7-act_structure-幕结构)
8. [scenes 场景列表](#8-scenes-场景列表)
9. [scene elements 场景元素类型](#9-scene-elements-场景元素类型)
10. [设计决策详解](#10-设计决策详解)
11. [扩展规范](#11-扩展规范)
12. [示例文件](#12-示例文件)

---

## 1. 设计理念

剧本 YAML Schema 的设计遵循三条核心原则：

**可读性优先**：YAML 本身是人类可读的数据格式，Schema 设计时让字段名称和层级关系与剧本的直观结构（标题 → 角色 → 幕 → 场景 → 元素）完全一致，无需文档也能猜出大致含义。

**结构最小化**：只定义必要的层级（脚本信息 → 角色列表 → 幕结构 → 场景列表 → 场景元素），不多嵌套一层。每一层都有明确的语义：幕是场景的逻辑分组，场景是场景元素的容器，元素是原子内容单位。

**AI 生成友好**：Schema 的树形结构与 AI 生成 JSON/YAML 时的思维链（decompose: 先确定角色 → 再拆分场景 → 最后填充对话/动作）高度契合，使 AI 能够有序地逐步构建输出，减少结构错乱和遗漏字段的概率。

---

## 2. 整体结构

```yaml
script:        # 脚本基本元信息（必填）
metadata:      # 制作级元数据（必填）
characters:    # 角色列表（必填，>=1 个）
act_structure: # 幕结构定义（必填，3 个 act）
scenes:        # 场景列表（必填，>=1 个）
```

---

## 3. 根对象

根对象为 `dict`，包含 5 个顶层键，全部为 **必填**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `script` | `ScriptInfo` | 脚本基本信息 |
| `metadata` | `Metadata` | 制作元数据 |
| `characters` | `List[Character]` | 角色列表 |
| `act_structure` | `List[Act]` | 幕结构 |
| `scenes` | `List[Scene]` | 场景列表 |

### 验证规则

```python
assert len(root["script"]) == 5              # 必须有 5 个顶层键
assert 1 <= len(root["characters"])          # 至少 1 个角色
assert len(root["act_structure"]) == 3       # 严格 3 幕
assert 1 <= len(root["scenes"])              # 至少 1 个场景
```

---

## 4. script 元信息

```yaml
script:
  title: "故事的名字"          # 必填 string
  author: "原作者名称"         # 必填 string
  genre: "剧情"               # 必填 enum
  logline: "一句话故事"       # 必填 string，≤ 200 字符
  original_source: "小说"     # 选填 string
  adaptation_notes: "改编说明" # 选填 string
```

### genre 枚举值

| 值 | 中文 | 说明 |
|----|------|------|
| `drama` | 剧情 | 写实生活、情感冲突 |
| `thriller` | 悬疑 | 推理、惊悚、神秘 |
| `sci_fi` | 科幻 | 未来设定、技术元素 |
| `fantasy` | 奇幻 | 超自然、魔法 |
| `romance` | 爱情 | 情感、浪漫关系 |
| `comedy` | 喜剧 | 幽默、讽刺 |
| `horror` | 恐怖 | 惊吓、黑暗氛围 |
| `action` | 动作 | 战斗、追逐 |
| `historical` | 历史 | 时代剧、古装 |
| `other` | 其他 | 未分类类型 |

### 设计原因

- **`logline` 必填**：让改编者在任何时候都能用一句话说清楚这个故事是什么，是剧本开发的第一工具。
- **`genre` 为枚举**：强制作者在类型上做选择，避免生成一个模糊的「混合类型」剧本，也便于后续分类检索。
- **`adaptation_notes`**：说明这一版的改编侧重点，为后续修改提供上下文。

---

## 5. metadata 制作元数据

```yaml
metadata:
  total_scenes: 25           # 必填 int，场景总数
  total_characters: 8        # 必填 int，角色总数
  total_acts: 3              # 必填 int，固定为 3
  estimated_duration: "45分钟"  # 必填 string，估算时长
  word_count: 12000          # 选填 int，原文字数
  generated_by: "gpt-4o"     # 选填 string，生成模型
  generated_at: "2026-06-05" # 必填 string，ISO 日期
  version: "1.0"             # 选填 string，版本号
```

### 设计原因

- **`estimated_duration`**：小说转剧本后，字数与屏幕时长的换算关系不固定（动作场景密/旁白场景稀），用 AI 估算一个参考时长，帮助作者判断剧本的完整度。
- **`total_*` 字段**：`total_scenes`、`total_characters`、`total_acts` 在 metadata 中独立暴露，而非仅从数据结构中计数，是因为工具和人工都需要在不遍历整个文件的情况下快速了解剧本规模。
- **`version` 字段**：剧本是迭代产物，版本号便于追踪多轮修改。

---

## 6. characters 角色定义

```yaml
characters:
  - id: "char_001"                    # 必填，格式: char_NNN
    name: "李明"                      # 必填
    role: "protagonist"               # 必填 enum
    description: "35岁，退伍军人..."   # 必填，>= 10 字符
    voice: "沉稳有力，偶有冷幽默"     # 选填，语音/性格特征
    first_appearance: 1               # 必填 int，场景编号
    relationships:                    # 选填
      - target: "char_002"            # 关联角色 ID
        type: "mentor"                # enum: mentor|family|friend|enemy|romantic|partner
        description: "曾是上下级关系"
```

### role 枚举值

| 值 | 中文 | 说明 |
|----|------|------|
| `protagonist` | 主角 | 故事核心视角人物 |
| `antagonist` | 反派 | 主要对立力量 |
| `supporting` | 配角 | 重要但非核心 |
| `minor` | 配角 | 次要角色，出场少 |
| `narrator` | 旁白 | 叙述者角色 |

### 设计原因

- **全局角色表 + ID 引用**：这是本 Schema 最关键的设计决策之一（详见 [§10](#10-设计决策详解)）。
- **`voice` 字段**：帮助演员和编剧在对话写作时保持角色语言风格的一致性。
- **`first_appearance`**：AI 生成时用于校验角色是否在出场前就被引用。
- **`relationships`**：显式建模角色关系，有助于 AI 理解对话中的潜台词和情感张力。

---

## 7. act_structure 幕结构

```yaml
act_structure:
  - act: 1                                        # 必填，1/2/3
    title: "第一幕：起因"                          # 必填
    description: "建立世界，引入冲突"              # 选填
    scenes: [1, 2, 3, 4, 5]                       # 必填，场景编号列表
  - act: 2
    title: "第二幕：对抗"
    description: "冲突升级，挫折阻碍"
    scenes: [6, 7, 8, 9, 10, 11, 12]
  - act: 3
    title: "第三幕：解决"
    description: "高潮对决，结局收束"
    scenes: [13, 14, 15]
```

### 设计原因

- **固定 3 幕制**：经典的三幕结构（Setup / Confrontation / Resolution）是剧本写作的事实标准，将 3 个 act 的 scene ID 列表在顶层列出，而非散落在场景内部，是为了用一次遍历就能了解整部剧本的节奏分布（哪一幕场景最多=高潮在哪里）。
- **`act` 值为 1/2/3 整数而非字符串**：便于工具做数值排序和计算。

---

## 8. scenes 场景列表

```yaml
scenes:
  - id: 1                        # 必填 int，从 1 开始连续编号
    act: 1                        # 必填 int，所属幕号
    location: "城市场景"           # 必填 string
    time: "白天"                  # 必填 string
    location_type: "ext"          # 必填 enum: ext|int|mixed
    weather: "阴天"              # 选填 string
    characters: ["char_001", "char_002"]  # 必填，角色 ID 列表
    summary: "李明偶遇王芳..."    # 必填 string，场景概述
    elements:                    # 必填，场景元素列表
      - type: "transition"
        content: "淡入"
      - type: "narrative"
        content: "城市街道，雨后。李明独自走在街上。"
      - type: "action"
        content: "李明停下脚步，看向街角的咖啡馆。"
      - type: "dialogue"
        character: "char_001"
        content: "这雨下得真是没完没了。"
        parenthetical: "自言自语"
      - type: "dialogue"
        character: "char_002"
        content: "需要进来坐坐吗？"
      - type: "camera"
        content: "近景，李明的侧脸，雨水顺着脸颊滑落。"
      - type: "transition"
        content: "淡出"
```

### location_type 枚举

| 值 | 含义 |
|----|------|
| `ext` | 外部场景（室外） |
| `int` | 内部场景（室内） |
| `mixed` | 混合（室内外交替） |

### 设计原因

- **`id` 从 1 连续编号**：`act_structure.scenes` 中的编号必须与 `scenes` 列表中的 `id` 一致，形成双向引用验证。
- **`location` 和 `time` 分离**：这两者是场景的最基本信息（电影学中叫 scene heading / slug line），分离存储便于按「夜晚室内」「白天室外」等组合条件快速检索场景。
- **`summary` 必填**：帮助读者在不看对话的情况下快速了解每个场景发生了什么。

---

## 9. scene elements 场景元素类型

场景的 `elements` 列表中，每个元素必须指定 `type`，目前支持 6 种类型：

### 9.1 dialogue — 对话

```yaml
- type: "dialogue"
  character: "char_001"          # 必填，角色 ID（需在 characters 中定义）
  content: "台词内容"             # 必填 string
  parenthetical: "动作/语气提示"   # 选填 string
```

**设计原因**：`parenthetical`（括注语）是剧本写作标准格式，用于说明说话时的动作或语气（如"皱眉""冷笑""小声说"），与 `content` 分离存储使得：
1. 文本提取工具可以区分旁白和台词语气
2. AI 可以在保留语气的同时，精简括注语使其不冗余

### 9.2 action — 动作描述

```yaml
- type: "action"
  content: "动作描写内容"         # 必填 string
```

**设计原因**：动作描述在剧本中不属于对话，但和对话一样是原子级元素。独立的 `action` 类型让：
- 渲染器可以选择用斜体显示动作描述
- AI 在生成时不会把动作描述混入对话或旁白

### 9.3 narrative — 旁白

```yaml
- type: "narrative"
  content: "叙述内容"             # 必填 string
```

**设计原因**：旁白（Voice-Over / V.O.）是小说改编剧本中最关键也最难处理的部分。将 `narrative` 独立为类型，使得：
- 可以区分「画面内旁白」和「画外音旁白」（可通过 metadata 扩展）
- 编剧可以快速找到并压缩旁白，降低剧本的「小说感」

### 9.4 transition — 转场

```yaml
- type: "transition"
  content: "淡入"                # 必填 string
```

**设计原因**：转场是场景的边界标记，常见值：`淡入`/`淡出`/`快速切换`/`黑场`。将转场作为场景的边界元素（第一个或最后一个元素），而不是独立场景，保持了 YAML 结构扁平化。

### 9.5 camera — 镜头指令

```yaml
- type: "camera"
  content: "近景，特写李明的眼神" # 必填 string
```

**设计原因**：
1. 镜头语言是小说文本中「描写最丰富」的部分，AI 可以将小说的环境描写转化为镜头语言建议
2. 这些建议是**可选的创作参考**，不是硬约束，最终由导演决定
3. 独立 `camera` 类型让导演/编剧可以选择忽略镜头建议，而不影响叙事内容

### 9.6 element 类型约束汇总

| type | 必填字段 | 选填字段 | 说明 |
|------|---------|---------|------|
| `dialogue` | `character`, `content` | `parenthetical` | 角色对话 |
| `action` | `content` | — | 动作描述 |
| `narrative` | `content` | — | 旁白/叙述 |
| `transition` | `content` | — | 转场指令 |
| `camera` | `content` | — | 镜头建议 |

---

## 10. 设计决策详解

### 10.1 为什么用全局角色表 + ID 引用，而不是内联角色名？

**问题**：如果角色信息直接写在对话旁边，会发生什么？

```yaml
# ❌ 内联方式（不好）
- type: "dialogue"
  character_name: "李明"  # 同一个人可能写成"李明""李 大明""小明"
  content: "台词"
```

**问题场景**：
- 第三章 AI 生成了「李明」，第五章生成了「李 大明」（多了空格）
- 角色表中的描述是「35岁退伍军人」，但对话中写的是「李明，42岁」
- 编剧想改主角名字，需要替换几十处

```yaml
# ✅ 全局表 + ID 引用（好）
characters:
  - id: "char_001"
    name: "李明"
    description: "35岁，退伍军人"

scenes:
  - elements:
      - type: "dialogue"
        character: "char_001"  # 引用 ID，精确无歧义
        content: "台词"
```

**结论**：全局角色表强制了角色命名的一致性，同时 `name` 字段在角色表中只定义一次，改名时只需改一处。

### 10.2 为什么是「幕 → 场景 → 元素」三级，而不是「幕 → 章节 → 场景 → 元素」四级？

**背景**：小说有「章/Chapter」，但剧本没有。小说的一章往往包含多个场景（室内、室外、回忆），反之多个章节能被压缩进一个场景。

**决策**：Schema 不试图保留小说的章结构，而是重新按剧本逻辑（幕→场景）组织内容。原小说的章节信息通过 `scenes[i].original_chapters: [1, 2]`（扩展字段）可选地保留。

### 10.3 为什么 `elements` 用列表而不是按类型嵌套？

**对比**：

```yaml
# ❌ 按类型嵌套（不好）
elements:
  dialogues: [...]
  actions: [...]
  narratives: [...]

# ✅ 扁平列表 + type 标记（好）
elements:
  - type: "dialogue"
    character: "char_001"
    content: "..."
  - type: "action"
    content: "..."
```

**原因**：
1. 对话和动作在剧本中本来就是交替出现的（说一句台词 → 做一个动作 → 再说一句），嵌套结构会丢失这个交替顺序
2. 扁平列表更适合流式生成和实时渲染
3. 渲染器按 `type` 分发到不同的样式模板即可

### 10.4 为什么不直接用 Final Draft XML (FDX) 或专业剧本格式？

**目标不同**：Final Draft、Celtx 等工具面向专业编剧，输出的是带格式指令的 `.fdx`/`.fountain` 文件，适合直接制片。

本工具的目标用户是**小说作者做剧本初稿**，需要：
- 低门槛：YAML 的键值对比 XML 更直观
- 可编辑：初稿需要大幅度改写，YAML 比二进制格式更友好
- AI 生成友好：AI 在生成结构化 YAML 时比生成 `.fountain` 犯错的概率更低

YAML 输出后，用户可以进一步使用 `fountain` 或 `python-fountain` 等工具转换为专业格式。

---

## 11. 扩展规范

### 扩展原则

本 Schema 允许在以下位置添加自定义字段，扩展字段须遵循：
1. 以 `x_` 前缀开头（例如 `x_director_note`、`x_draft`）
2. 不修改任何必填字段的类型或必填性
3. 扩展字段不应影响标准工具的解析

### 允许的扩展位置

```yaml
# 在 script 下扩展
script:
  x_draft_notes: "第一版草稿，待打磨"

# 在 character 下扩展
characters:
  - id: "char_001"
    name: "李明"
    x_actor_suggestion: "建议由张译出演"

# 在 scene 下扩展
scenes:
  - id: 1
    x_director_note: "这段可以用长镜头表现孤独感"
    x_locations_notes: "可在横店影视城拍摄"

# 在 metadata 下扩展
metadata:
  x_review_status: "待审核"
  x_last_modified: "2026-06-05T14:00:00Z"
```

---

## 12. 示例文件

完整的示例文件见同目录下的 `example.yaml`，以下是核心片段展示：

```yaml
script:
  title: "雨夜归途"
  author: "张小说"
  genre: "drama"
  logline: "一个退伍军人在雨夜的城市中偶遇故人，重新面对自己逃避多年的过去。"

metadata:
  total_scenes: 5
  total_characters: 3
  total_acts: 3
  estimated_duration: "12分钟"
  generated_by: "gpt-4o"
  generated_at: "2026-06-05"

characters:
  - id: "char_001"
    name: "李明"
    role: "protagonist"
    description: "35岁，退伍军人，身形挺拔，性格内敛沉稳，习惯独来独往。"
    voice: "沉稳有力，言语简洁，偶有冷幽默"
    first_appearance: 1
    relationships:
      - target: "char_002"
        type: "family"
        description: "失散多年的兄妹"
  - id: "char_002"
    name: "王芳"
    role: "supporting"
    description: "33岁，李明的妹妹，独立坚强，与哥哥关系复杂。"
    voice: "温柔但坚定，外柔内刚"
    first_appearance: 1

act_structure:
  - act: 1
    title: "第一幕：偶遇"
    description: "雨夜街头，李明与王芳意外重逢。"
    scenes: [1, 2]
  - act: 2
    title: "第二幕：对峙"
    description: "兄妹重逢揭开往事，各自面对内心挣扎。"
    scenes: [3, 4]
  - act: 3
    title: "第三幕：和解"
    description: "真相浮现，两人选择面对而非逃避。"
    scenes: [5]

scenes:
  - id: 1
    act: 1
    location: "城市街道"
    time: "夜晚"
    location_type: "ext"
    weather: "中雨"
    characters: ["char_001"]
    summary: "雨夜，李明独自走在街道上，在一家咖啡馆前停下脚步。"
    elements:
      - type: "transition"
        content: "淡入"
      - type: "narrative"
        content: "城市街道，中雨。霓虹灯在雨幕中模糊成一片光晕。"
      - type: "action"
        content: "李明停下脚步，抬头看向街角的咖啡馆，雨水顺着脸颊滑落。"
      - type: "camera"
        content: "中景，俯拍，雨伞的弧线与街道形成构图。"
      - type: "dialogue"
        character: "char_001"
        content: "这雨下得真是没完没了。"
        parenthetical: "自言自语"
      - type: "transition"
        content: "淡出"
```

---

*本文档由 Novel2Script AI 小说转剧本工具项目组编写，版本 1.0*
