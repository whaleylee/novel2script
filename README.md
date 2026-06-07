# Novel2Script · AI 小说转剧本工具

将 3+ 章节的小说文本智能转换为结构化剧本 YAML，降低小说改编剧本的门槛。

---

## 功能特性

- **多格式输入**：支持 TXT、DOCX、PDF 小说文件上传
- **多 AI 引擎**：讯飞 MaaS Coding（15 个模型）、OpenAI、Ollama（本地）、Gemini
- **5 种剧本风格**：电影化 / 舞台戏剧 / 可拍摄剧本 / 文学剧本 / 电视剧节奏
- **智能场景拆分**：AI 自动分析章节，识别场景边界、时间线、视角切换
- **角色图谱**：全局角色表 + ID 引用，自动提取并保持角色一致性
- **三幕结构**：自动分配经典三幕（起因/对抗/解决）
- **进度条 + 分步转换**：实时显示转换进度，不再是黑盒等待
- **双栏预览**：YAML 源码 + 可视化预览（角色卡片、幕统计、场景列表）
- **多格式导出**：YAML / TXT 剧本 / Fountain（专业剧本格式）/ JSON
- **YAML Schema**：输出符合规范的结构化剧本，支持扩展字段（`x_` 前缀）

---

## 快速开始

### 1. 环境要求

- Python 3.10+
- 至少 4GB RAM

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 API Key

Novel2Script 支持 4 种 AI 提供商。推荐使用**讯飞 MaaS Coding**（效果最佳，支持 15 个模型）：

```bash
# 讯飞 MaaS Coding（推荐）
export XF_API_KEY="your-xfyun-api-key"

# 或 OpenAI
export OPENAI_API_KEY="sk-your-key-here"

# 或 Gemini
export GEMINI_API_KEY="your-gemini-key"

# 或 Ollama（本地免费，无需 API Key）
ollama pull qwen2.5
ollama serve
```

> 也可以在 Web 界面中直接填写 API Key，无需设置环境变量。

### 4. 启动应用

```bash
python run.py
```

浏览器打开 `http://localhost:7860`

### 5. 使用步骤

1. 粘贴小说文本（至少 3 章）或上传文件（.txt / .docx / .pdf）
2. 填写剧本标题和原作者（可选）
3. 选择 AI 提供商，输入 API Key
4. 选择模型 + 剧本风格
5. 点击「开始转换」
6. 查看进度条，等待生成完成
7. 在「YAML 源码」和「可视化预览」之间切换查看结果
8. 导出为 YAML / TXT / Fountain / JSON

---

## 项目结构

```
novel2script/
├── SPEC.md                    # 项目规格说明
├── YAML_SCHEMA.md             # YAML Schema 完整设计文档（含设计原因）
├── README.md                  # 本文件
├── requirements.txt           # Python 依赖
├── run.py                     # 应用入口
│
├── backend/
│   ├── api/
│   │   └── app.py             # FastAPI 路由
│   ├── core/
│   │   ├── config.py          # 配置常量（模型列表、风格预设等）
│   │   └── models.py          # Pydantic 数据模型
│   └── services/
│       ├── llm_service.py     # LiteLLM 统一 AI 接口
│       ├── file_parser.py     # 文件解析（TXT/DOCX/PDF）
│       ├── converter.py       # 核心转换引擎（单次 LLM 调用/章）
│       └── export_service.py  # 多格式导出（YAML/TXT/Fountain/JSON）
│
└── frontend/
    └── app.py                 # Gradio Web 界面
```

---

## API 接口

### 健康检查

```bash
curl http://localhost:8000/health
```

### 转换小说（流式 SSE）

```bash
curl -X POST http://localhost:8000/convert \
  -F "text=第一章 雨夜..." \
  -F "provider=xfyun" \
  -F "api_key=$XF_API_KEY" \
  -F "model=xsparkx2flash"
```

### 转换小说（JSON 响应）

```bash
curl -X POST http://localhost:8000/convert/plain \
  -H "Content-Type: application/json" \
  -d '{
    "text": "第一章 雨夜\n...\n第二章 重逢\n...\n第三章 真相\n...",
    "config": {
      "provider": "xfyun",
      "model": "xsparkx2flash",
      "api_key": "your-key",
      "temperature": 0.7,
      "max_tokens": 4096
    }
  }'
```

### 多格式导出

```bash
# YAML
curl -X POST "http://localhost:8000/export/yaml?yaml_text=..."

# Fountain（专业剧本格式）
curl -X POST "http://localhost:8000/export/fountain?yaml_text=..."

# JSON
curl -X POST "http://localhost:8000/export/json?yaml_text=..."

# TXT 剧本
curl -X POST "http://localhost:8000/export/txt?yaml_text=..."
```

---

## YAML Schema 概览

生成的 YAML 包含 5 个顶层键：

```yaml
script:         # 基本元信息（标题、作者、类型、一句话简介）
metadata:       # 制作元数据（场景数、角色数、时长、版本号）
characters:     # 全局角色表（ID 引用，含角色关系）
act_structure:  # 三幕结构（含各幕场景编号列表）
scenes:         # 场景列表（含类型化元素：dialogue/action/narrative/transition/camera）
```

完整 Schema 设计文档及设计原因见 **[YAML_SCHEMA.md](./YAML_SCHEMA.md)**。

### 设计亮点

- **全局角色表 + ID 引用**：角色定义一次，场景中通过 `char_XXX` ID 引用，避免名字不一致
- **固定三幕制**：经典 Setup / Confrontation / Resolution 结构
- **扁平化 elements 列表**：对话、动作、旁白按剧本节奏交替排列
- **5 种元素类型**：dialogue、action、narrative、transition、camera
- **可扩展**：以 `x_` 前缀添加自定义字段（导演注释、拍摄备注等）

---

## 依赖说明

| 库 | 用途 | 版本 |
|---|---|---|
| FastAPI + uvicorn | 后端 REST API | 0.115.0 |
| Gradio | Web 前端界面 | 4.44.1 |
| LiteLLM | 统一 AI 调用层 | 1.44.6 |
| PyPDF2 | PDF 文本提取 | 3.0.1 |
| python-docx | Word 文本提取 | 1.1.2 |
| PyYAML + ruamel.yaml | YAML 序列化/反序列化 | 6.0.2 |
| Pydantic | 数据验证 | 2.9.2 |
| httpx | HTTP 客户端 | 0.27.2 |

---

## 高级用法

### 仅启动后端 API

```bash
python run.py --backend-only
# API 文档: http://localhost:8000/docs
```

### 仅启动前端

```bash
python run.py --frontend-only
```

### 指定端口

```bash
python run.py --port 8080
```

---

## 支持的 AI 模型

### 讯飞 MaaS Coding（推荐）

| 模型 | model_id |
|------|----------|
| Spark X2 Flash | xsparkx2flash |
| Qwen3.5-35B-A3B | xopqwen35v35b |
| Qwen3.6-35B-A3B | xopqwen36v35b |
| Qwen3-Coder-Next-FP8 | xop3qwencodernext |
| GLM-4.7-Flash | xopglmv47flash |
| Spark X2 | xsparkx2 |
| GLM-5.1 | xopglm51 |
| DeepSeek-V4-Pro | xopdeepseekv4pro |
| DeepSeek-V3.2 | xopdeepseekv32 |
| Kimi-K2.6 | xopkimik26 |
| MiniMax-M2.5 | xminimaxm25 |
| Qwen3.5-397B-A17B | xopqwen35397b |

### 剧本风格预设

| 风格 | style_id | 特点 |
|------|----------|------|
| 电影化 | cinematic | 强镜头语言，注重视觉节奏 |
| 舞台戏剧 | theatrical | 对话密集，聚焦人物关系 |
| 可拍摄剧本 | practical | 口语化台词，便于低成本制作 |
| 文学剧本 | literary | 保留诗意，适合艺术片 |
| 电视剧节奏 | teleplay | 快节奏短场景，每场留悬念 |

---

## 原创功能

本项目的核心技术原创点：

1. **小说 → 剧本 YAML 转换引擎**：从章节检测 → LLM 逐章生成 → YAML 组装 → 三幕分配的完整流水线，为本项目从零编写
2. **YAML Schema 设计**：5 层结构的剧本数据格式，含 characters（全局角色表 + 角色关系）、act_structure（三幕）、scenes（5 种类型化元素），为项目原创设计
3. **多风格 Prompt 注入**：5 种剧本风格预设通过不同的 prompt suffix 影响 LLM 生成，无需微调即可切换风格
4. **进度分步反馈**：`[STEP_1]` 到 `[STEP_5]` 的分步标记系统，前端进度条实时解析显示
5. **多格式导出引擎**：YAML → Fountain/YAML/TXT/JSON 的转换管道

---

## License

MIT
