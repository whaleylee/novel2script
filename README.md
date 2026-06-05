# Novel2Script · AI 小说转剧本工具

将 3+ 章节的小说文本智能转换为结构化剧本 YAML，降低小说改编剧本的门槛。

---

## 功能特性

- **多格式输入**：支持 TXT、DOCX、PDF 小说文件上传
- **智能场景拆分**：AI 自动分析章节，识别场景边界、时间线、视角切换
- **对话提取**：从叙述文本中识别角色对话，区分旁白与台词
- **角色图谱**：自动提取全部角色，构建角色关系网络
- **镜头语言增强**：将文字描写转换为分镜描述建议
- **三幕结构**：自动识别经典三幕结构（起因/对抗/解决）
- **YAML Schema**：输出符合规范的结构化剧本，可直接在编辑器中修改
- **多 AI 引擎**：支持 OpenAI GPT、Ollama（本地）、Gemini
- **流式输出**：实时看到 AI 生成进度
- **双格式导出**：导出 YAML 文件 + 人类可读的 TXT 剧本

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 AI

**方式 A — OpenAI（推荐，效果最佳）**
```bash
export OPENAI_API_KEY=sk-your-key-here
```

**方式 B — Ollama（本地免费）**
```bash
# 安装 Ollama
# https://ollama.com

# 拉取模型
ollama pull qwen2.5
# 或
ollama pull deepseek-r1

# 启动服务（通常自动启动）
ollama serve
```

**方式 C — Gemini**
```bash
export GEMINI_API_KEY=your-key-here
```

### 3. 启动应用

```bash
python run.py
```

浏览器自动打开 `http://localhost:7860`

### 4. 使用

1. 在左侧粘贴小说文本或上传文件（支持 .txt / .docx / .pdf）
2. 填写剧本标题和原作者（可选）
3. 选择 AI 提供商并配置
4. 点击「🚀 开始转换」
5. 在 YAML 编辑器中查看、修改结果
6. 导出为 YAML 或 TXT 剧本

---

## 项目结构

```
qnyzy/
├── SPEC.md               # 项目规格说明
├── YAML_SCHEMA.md        # YAML Schema 完整设计文档
├── requirements.txt      # Python 依赖
├── run.py                # 应用入口
├── README.md             # 本文件
│
├── backend/
│   ├── api/
│   │   └── app.py        # FastAPI 路由
│   ├── core/
│   │   ├── config.py     # 配置常量
│   │   └── models.py     # Pydantic 数据模型
│   └── services/
│       ├── llm_service.py    # LiteLLM 统一 AI 接口
│       ├── file_parser.py    # 文件解析（TXT/DOCX/PDF）
│       └── converter.py      # 核心转换引擎
│
├── frontend/
│   └── app.py            # Gradio Web 界面
│
└── docs/
    └── plans/            # 设计文档
```

---

## YAML Schema 概览

生成的 YAML 包含 5 个顶层部分：

```yaml
script:              # 脚本基本信息（标题/作者/类型/一句话简介）
metadata:            # 制作元数据（场景数/角色数/时长）
characters:          # 全局角色表（ID 引用方式）
act_structure:       # 三幕结构（各幕场景编号）
scenes:              # 场景列表（带类型化元素）
```

详见 [`YAML_SCHEMA.md`](./YAML_SCHEMA.md)。

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

### 指定前端端口

```bash
python run.py --port 8080
```

### API 调用示例

```bash
curl -X POST http://localhost:8000/convert \
  -F "text=第一章的内容..." \
  -F "provider=openai" \
  -F "api_key=$OPENAI_API_KEY" \
  -F "model=gpt-4o-mini"
```

---

## 开发说明

### 依赖说明

| 库 | 用途 |
|---|---|
| FastAPI + uvicorn | 后端 REST API |
| Gradio | Web 前端界面 |
| LiteLLM | 统一 AI 调用层 |
| PyPDF2 | PDF 文本提取 |
| python-docx | Word 文本提取 |
| PyYAML | YAML 序列化/反序列化 |
| Pydantic | 数据验证 |

### 健康检查

```bash
curl http://localhost:8000/health
```

### Ollama 模型列表

```bash
curl http://localhost:8000/ollama/models
```

---

## 系统要求

- Python 3.10+
- （可选）Ollama（本地模型运行）
- （可选）OpenAI API Key
- 至少 4GB RAM

---

## License

MIT
