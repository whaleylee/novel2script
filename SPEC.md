# SPEC.md — AI 小说转剧本工具 (Novel2Script)

## 1. Project Overview

**Project Name**: Novel2Script  
**Type**: AI-powered web application for converting novel text into structured screenplay YAML  
**Core Functionality**: Upload 3+ chapters of novel text, let AI analyze scenes, extract dialogue, and generate a structured screenplay draft in YAML format  
**Target Users**: Novel authors, screenwriters, content creators adapting prose to screen

---

## 2. Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | Gradio | Beautiful UI, built-in file upload, markdown rendering, theme system |
| Backend | FastAPI | Async, high-performance, automatic OpenAPI docs |
| AI Layer | LiteLLM | Unified interface for OpenAI + Ollama + Gemini + Azure |
| File Parsing | PyPDF2, python-docx | TXT/DOCX/PDF multi-format support |
| YAML | PyYAML + ruamel.yaml | Clean YAML serialization with preserve order |

---

## 3. UI/UX Design Direction

**Visual Style**: Clean, professional, dark-mode-friendly — inspired by VS Code + Notion  
**Color Scheme**: Slate/indigo palette — dark sidebar, light content area  
**Layout**: Three-panel layout:
  - Left: File upload + AI config
  - Center: Conversion progress + YAML editor
  - Right: Live preview / character map (collapsible)

**Key UX Principles**:
- Zero-config for OpenAI users (just paste API key)
- One-click Ollama detection (auto-scan localhost:11434)
- Drag-and-drop file upload
- Real-time streaming output during conversion
- Inline YAML editing with syntax highlighting
- Export to YAML + formatted TXT screenplay

---

## 4. Functionality Specification

### 4.1 File Input
- [x] Accept `.txt`, `.docx`, `.pdf` files via drag-and-drop or file picker
- [x] Accept raw text pasted into a text area
- [x] Auto-detect chapter boundaries (look for "第X章", "Chapter", "CHAPTER", numbered headers)
- [x] Validate minimum 3 chapters before processing
- [x] Show text preview with word count and chapter count

### 4.2 AI Configuration
- [x] Model provider toggle: OpenAI / Ollama / Gemini
- [x] OpenAI: API key input + model selector (gpt-4o, gpt-4o-mini, gpt-3.5-turbo)
- [x] Ollama: Auto-detect running instances + model selector (qwen2.5, deepseek-r1, etc.)
- [x] Gemini: API key input + model selector
- [x] Temperature / max tokens sliders
- [x] Save config to local storage (gradio state)

### 4.3 Conversion Engine
- [x] **Chapter Analysis**: AI parses each chapter, identifies scene boundaries, time, location
- [x] **Dialogue Extraction**: Identify character names, extract spoken dialogue from narration
- [x] **Character Profiling**: Build character list with IDs, roles (protagonist/antagonist/supporting), descriptions, voice traits
- [x] **Scene Decomposition**: Break chapters into individual scenes with act structure
- [x] **Shot Language Enhancement**: Add camera directions, scene type hints
- [x] **Act Structure**: Auto-detect three-act structure (Setup / Confrontation / Resolution)
- [x] Streaming output — tokens appear in real-time as AI generates

### 4.4 YAML Output
- [x] Validate generated YAML is parseable
- [x] Display YAML in syntax-highlighted editor (Gradio Code component)
- [x] Allow manual editing of YAML in-app
- [x] Show scene count, character count, estimated duration metadata

### 4.5 Export
- [x] Download as `.yaml` file
- [x] Download as formatted `.txt` screenplay (human-readable)
- [x] Copy YAML to clipboard

### 4.6 Progress & State
- [x] Progress bar during conversion
- [x] Chapter-by-chapter status indicators
- [x] Session state preservation (config survives refresh)
- [x] Error recovery with retry button

---

## 5. YAML Schema Design Principles

The `YAML_SCHEMA.md` document (sibling to this file) defines the complete schema. Key design decisions:

1. **Act/Scene hierarchy** — Strict three-act structure with scene as atomic unit
2. **Character-first indexing** — Characters defined globally, referenced by ID in scenes (avoids name-spelling inconsistencies)
3. **Element typing** — Every scene element has a `type` field: `dialogue | action | narrative | transition | camera`
4. **Metadata-first** — Script header contains title, author, genre, logline for quick context
5. **Minimal prose** — Each element is concise; lengthy descriptions are split into multiple elements
6. **Extensible** — Custom fields allowed via `notes` and `metadata.extended` sections

---

## 6. API Design

### POST `/convert`
**Request**: `{ text: string, config: AIConfig, options: ConvertOptions }`  
**Response**: Streaming `text/event-stream` of YAML chunks

### GET `/health`
**Response**: `{ status: "ok", ollama_connected: bool, openai_connected: bool }`

### GET `/ollama/models`
**Response**: `{ models: [{ name: string, size: int }] }`

---

## 7. Error Handling

| Error | User Feedback |
|-------|--------------|
| File too large (>10MB) | "文件过大，请上传小于 10MB 的文件" |
| < 3 chapters detected | "检测到章节数不足，请确保至少包含 3 个章节" |
| AI API error | "AI 服务出错：[具体错误]，请检查 API Key 或网络连接" |
| YAML parse error | "YAML 生成异常，已生成原始文本，可在编辑器中手动调整" |
| Ollama not running | "未检测到 Ollama，请确保已启动 Ollama 服务" |

---

## 8. Acceptance Criteria

1. User can upload a 3-chapter TXT novel and receive a valid YAML screenplay in under 5 minutes
2. Generated YAML parses successfully with `yaml.safe_load()`
3. YAML contains all required fields: script metadata, characters, act_structure, scenes with typed elements
4. User can edit the YAML inline and re-validate
5. User can export to both `.yaml` and `.txt` screenplay formats
6. Ollama auto-detection works when Ollama is running on localhost:11434
7. All UI text is bilingual: Chinese primary, English secondary
8. Application starts with a single `python run.py` command
