"""
Novel2Script — Gradio Web Interface
AI-powered novel to screenplay YAML converter.
"""

import os
import json
import threading
import time
import httpx
import gradio as gr
from datetime import datetime

# ── Theme & Constants ──────────────────────────────────────────

THEME = gr.themes.Soft(
    primary_hue="indigo",
    secondary_hue="slate",
    neutral_hue="slate",
)

CSS = """
#app-header { text-align: center; padding: 1rem 0; }
.gradio-container { max-width: 1400px !important; }
#yaml-editor textarea { font-family: 'JetBrains Mono', 'Fira Code', monospace !important; font-size: 13px !important; }
.status-bar { padding: 8px 16px; border-radius: 8px; font-size: 13px; }
.panel-section { padding: 16px; border-radius: 12px; background: var(--background-fill-secondary); }
"""

APP_TITLE = """
# Novel2Script · AI 小说转剧本

*将小说文本智能转换为结构化剧本 YAML*

---
"""

API_BASE = os.environ.get("NOVEL2SCRIPT_API", "http://localhost:8000")

GENRE_CHOICES = [
    ("剧情", "drama"),
    ("悬疑", "thriller"),
    ("科幻", "sci_fi"),
    ("奇幻", "fantasy"),
    ("爱情", "romance"),
    ("喜剧", "comedy"),
    ("恐怖", "horror"),
    ("动作", "action"),
    ("历史", "historical"),
    ("其他", "other"),
]

OPENAI_MODELS = [
    ("GPT-4o（推荐）", "gpt-4o"),
    ("GPT-4o Mini（便宜快速）", "gpt-4o-mini"),
    ("GPT-4 Turbo", "gpt-4-turbo"),
    ("GPT-3.5 Turbo", "gpt-3.5-turbo"),
]

OLLAMA_MODELS_DEFAULT = [
    ("qwen2.5（通义千问）", "qwen2.5"),
    ("deepseek-r1（深度求索）", "deepseek-r1"),
    ("llama3.1", "llama3.1"),
    ("mistral", "mistral"),
]

GEMINI_MODELS = [
    ("Gemini 1.5 Flash（推荐）", "gemini-1.5-flash"),
    ("Gemini 1.5 Pro", "gemini-1.5-pro"),
    ("Gemini 2.0 Flash", "gemini-2.0-flash"),
]

XF_MODELS = [
    ("Spark X2 Flash (可用)", "xsparkx2flash"),
    ("Qwen3.5-35B-A3B (可用)", "xopqwen35v35b"),
    ("Qwen3.6-35B-A3B (可用)", "xopqwen36v35b"),
    ("Qwen3-Coder-Next-FP8 (可用)", "xop3qwencodernext"),
    ("GLM-4.7-Flash (可用)", "xopglmv47flash"),
    ("Spark X2", "xsparkx2"),
    ("GLM-5.1", "xopglm51"),
    ("GLM-5", "xopglm5"),
    ("DeepSeek-V4-Pro", "xopdeepseekv4pro"),
    ("DeepSeek-V4-Flash", "xopdeepseekv4flash"),
    ("DeepSeek-V3.2", "xopdeepseekv32"),
    ("Kimi-K2.6", "xopkimik26"),
    ("Kimi-K2.5", "xopkimik25"),
    ("MiniMax-M2.5", "xminimaxm25"),
    ("Qwen3.5-397B-A17B", "xopqwen35397b"),
]

# ── State ──────────────────────────────────────────────────────

class AppState:
    def __init__(self):
        self.ollama_connected = False
        self.ollama_models = []
        self.last_yaml = ""
        self.converting = False
        self.api_health = False


state = AppState()

# ── Helpers ──────────────────────────────────────────────────────

def check_api():
    """Check backend health."""
    try:
        resp = httpx.get(f"{API_BASE}/health", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            state.api_health = True
            state.ollama_connected = data.get("ollama_connected", False)
            return data
    except Exception:
        state.api_health = False
    return {"status": "offline", "ollama_connected": False}


def fetch_ollama_models():
    """Fetch available Ollama models."""
    try:
        resp = httpx.get(f"{API_BASE}/ollama/models", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            state.ollama_connected = data.get("connected", False)
            models = data.get("models", [])
            state.ollama_models = [m.get("name", "") for m in models if m.get("name")]
            return state.ollama_models
    except Exception:
        state.ollama_connected = False
    return []


def do_convert(
    input_method,
    text_input,
    file_input,
    title_input,
    author_input,
    provider,
    xfyun_model,
    openai_api_key,
    openai_model,
    ollama_model,
    ollama_base_url,
    gemini_api_key,
    gemini_model,
    temperature,
    max_tokens,
    add_camera,
    add_transitions,
    preserve_narrative,
    progress_callback=None,
):
    """Main conversion function."""
    import io

    if input_method == "text":
        raw_text = text_input.strip()
    elif input_method == "file":
        if file_input is None:
            yield "请上传文件", ""
            return
        if isinstance(file_input, dict):
            file_path = file_input.get("path", "")
        elif isinstance(file_input, str):
            file_path = file_input
        else:
            file_path = str(file_input)
        try:
            with open(file_path, "rb") as f:
                file_content = f.read()
        except Exception:
            file_content = file_input
        raw_text = file_content.decode("utf-8", errors="replace")
    else:
        raw_text = text_input.strip() if text_input else ""

    if len(raw_text) < 500:
        yield "文本内容过短（至少需要 500 字符）", ""
        return

    api_key = None
    model = "xsparkx2flash"
    base_url = None

    if provider == "xfyun":
        model = xfyun_model or "xsparkx2flash"
    elif provider == "openai":
        api_key = openai_api_key or os.environ.get("OPENAI_API_KEY", "")
        model = openai_model
        if not api_key:
            yield "请输入 OpenAI API Key", ""
            return
    elif provider == "ollama":
        model = ollama_model or "qwen2.5"
        base_url = ollama_base_url or "http://localhost:11434"
        if not state.ollama_connected:
            yield "未检测到 Ollama，请确保 Ollama 服务已启动", ""
    elif provider == "gemini":
        api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        model = gemini_model
        if not api_key:
            yield "请输入 Gemini API Key", ""
            return

    # Use /convert/plain - simpler, returns complete YAML
    try:
        yield "正在转换，请稍候（通常需要 2-5 分钟）...", ""
        import requests as sync_requests

        resp = sync_requests.post(
            f"{API_BASE}/convert/plain",
            json={
                "text": raw_text,
                "config": {
                    "provider": provider,
                    "model": model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                "title": title_input or "",
                "author": author_input or "",
            },
            timeout=600,
        )

        if resp.status_code != 200:
            yield f"转换失败: {resp.text[:200]}", ""
            return

        import yaml as pyyaml
        yaml_text = resp.json().get("yaml", "")
        data = pyyaml.safe_load(yaml_text)
        scene_count = len(data.get("scenes", []))
        char_count = len(data.get("characters", []))

        yield f"转换完成：{scene_count} 个场景，{char_count} 个角色", yaml_text

    except Exception as e:
        yield f"请求失败: {str(e)}", ""


def validate_yaml(yaml_text):
    """Validate YAML syntax."""
    import yaml
    if not yaml_text.strip():
        return "YAML 内容为空", gr.update()
    try:
        data = yaml.safe_load(yaml_text)
        scene_count = len(data.get("scenes", []))
        char_count = len(data.get("characters", []))
        return f"YAML 格式正确 — {scene_count} 个场景，{char_count} 个角色", gr.update()
    except yaml.YAMLError as e:
        return f"YAML 解析错误: {str(e)[:100]}", gr.update()


def export_yaml(yaml_text, title):
    """Export YAML as downloadable file."""
    fname = f"script_{title or 'novel'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
    return gr.update(value=yaml_text, filename=fname)


def export_screenplay(yaml_text):
    """Export YAML as formatted TXT screenplay."""
    try:
        import yaml
        data = yaml.safe_load(yaml_text)
        lines = []

        script = data.get("script", {})
        lines.append("=" * 60)
        lines.append(f"标题：{script.get('title', '未命名')}")
        lines.append(f"作者：{script.get('author', '未知')}")
        lines.append(f"类型：{script.get('genre', '剧情')}")
        lines.append(f"一句话简介：{script.get('logline', '')}")
        lines.append("=" * 60)
        lines.append("")

        lines.append("【角色表】")
        for char in data.get("characters", []):
            role_map = {"protagonist": "主角", "antagonist": "反派",
                        "supporting": "配角", "minor": "次要", "narrator": "旁白"}
            role = role_map.get(char.get("role", ""), char.get("role", ""))
            lines.append(f"  {char.get('name', char.get('id', ''))}（{role}）")
        lines.append("")

        char_map = {c.get("id", ""): c.get("name", "") for c in data.get("characters", [])}

        for scene in data.get("scenes", []):
            lines.append("")
            loc_type = "内" if scene.get("location_type") == "int" else "外"
            lines.append(f"─── 场景 {scene.get('id', '?')} ───")
            lines.append(f"[{loc_type}景] {scene.get('location', '')} - {scene.get('time', '')}")
            if scene.get("weather"):
                lines.append(f"天气：{scene.get('weather')}")
            char_names = [char_map.get(c, c) for c in scene.get("characters", [])]
            lines.append(f"出场：{', '.join(char_names)}")
            lines.append(f"概要：{scene.get('summary', '')}")
            lines.append("")

            for elem in scene.get("elements", []):
                etype = elem.get("type", "")
                content = elem.get("content", "")

                if etype == "transition":
                    lines.append(f"\n  >> {content}")
                elif etype == "dialogue":
                    char_id = elem.get("character", "")
                    paren = elem.get("parenthetical", "")
                    char_name = char_map.get(char_id, char_id)
                    prefix = f"（{paren}）" if paren else ""
                    lines.append(f"\n  {char_name}{prefix}")
                    lines.append(f"    {content}")
                elif etype == "camera":
                    lines.append(f"  [镜头] {content}")
                elif etype == "narrative":
                    lines.append(f"  （旁白）{content}")
                elif etype == "action":
                    lines.append(f"  （动作）{content}")

        return "\n".join(lines)
    except Exception as e:
        return f"导出失败: {str(e)}"


def on_provider_change(provider):
    """Update model choices based on provider."""
    if provider == "xfyun":
        return gr.update(choices=XF_MODELS, value="xsparkx2flash", visible=True)
    elif provider == "openai":
        return gr.update(choices=OPENAI_MODELS, value="gpt-4o-mini", visible=True)
    elif provider == "ollama":
        models = [(m, m) for m in state.ollama_models] if state.ollama_models else OLLAMA_MODELS_DEFAULT
        return gr.update(choices=models, value=models[0][1] if models else "qwen2.5", visible=True)
    elif provider == "gemini":
        return gr.update(choices=GEMINI_MODELS, value="gemini-1.5-flash", visible=True)
    return gr.update()


def on_tab_change(tab):
    """Initialize on tab change."""
    if tab == 0:
        health = check_api()
        if health.get("status") == "ok":
            if not state.ollama_connected:
                fetch_ollama_models()
        return health.get("status", "offline"), state.ollama_connected
    return "offline", False


# ── Build UI ─────────────────────────────────────────────────────

def build_ui():
    with gr.Blocks(title="Novel2Script · AI 小说转剧本") as demo:

        gr.HTML(APP_TITLE)

        with gr.Row():
            api_status = gr.HTML("<span style='color:#888'>正在检查后端连接...</span>")

        demo.load(
            fn=lambda: (
                "后端已连接" if check_api().get("status") == "ok" else "后端未连接",
            ),
            inputs=[],
            outputs=[api_status],
        )

        with gr.Tabs():
            with gr.Tab("小说转剧本"):
                gr.HTML("<p style='color:var(--text-color-subdued);font-size:14px'>上传小说文本，AI 将自动分析场景、提取对话、构建角色图谱，生成结构化剧本 YAML</p>")

                with gr.Row(equal_height=False):
                    with gr.Column(scale=1, min_width=360):
                        gr.HTML("<b>输入方式</b>")
                        input_method = gr.Radio(["text", "file"], value="text", label="选择输入")

                        with gr.Group(visible=True) as text_group:
                            text_input = gr.Textbox(label="小说文本", placeholder="在此粘贴小说章节内容（至少包含 3 个章节）...", lines=12)

                        with gr.Group(visible=False) as file_group:
                            file_input = gr.File(label="上传文件", file_types=[".txt", ".docx", ".pdf"])

                        input_method.change(
                            fn=lambda m: (gr.update(visible=m == "text"), gr.update(visible=m == "file")),
                            inputs=[input_method], outputs=[text_group, file_group],
                        )

                        gr.HTML("<b>剧本信息</b>")
                        title_input = gr.Textbox(label="剧本标题", placeholder="自动从文本中提取，也可手动填写", lines=1)
                        author_input = gr.Textbox(label="原作者", placeholder="作者名称", lines=1)

                        gr.HTML("<b>AI 配置</b>")

                        provider = gr.Radio(
                            ["xfyun", "openai", "ollama", "gemini"], value="xfyun",
                            label="AI 提供商", info="讯飞 MaaS Coding / OpenAI / Ollama / Gemini",
                        )

                        with gr.Group(visible=True) as xfyun_group:
                            xfyun_model = gr.Dropdown(
                                choices=[v for k, v in XF_MODELS], value="xsparkx2flash",
                                label="模型", allow_custom_value=True,
                                info="讯飞 MaaS Coding API",
                            )

                        with gr.Group(visible=False) as openai_group:
                            openai_api_key = gr.Textbox(label="OpenAI API Key", placeholder="sk-...", type="password", lines=1)
                            openai_model = gr.Dropdown(
                                choices=[v for k, v in OPENAI_MODELS], value="gpt-4o-mini",
                                label="模型", allow_custom_value=True,
                            )

                        with gr.Group(visible=False) as ollama_group:
                            ollama_base_url = gr.Textbox(label="Ollama 地址", value="http://localhost:11434", lines=1)
                            ollama_model = gr.Dropdown(
                                choices=[v for k, v in OLLAMA_MODELS_DEFAULT], value="qwen2.5",
                                label="模型", allow_custom_value=True,
                            )
                            btn_refresh_ollama = gr.Button("检测 Ollama 模型", size="sm", variant="secondary")

                        with gr.Group(visible=False) as gemini_group:
                            gemini_api_key = gr.Textbox(label="Gemini API Key", placeholder="AIza...", type="password", lines=1)
                            gemini_model = gr.Dropdown(
                                choices=[v for k, v in GEMINI_MODELS], value="gemini-1.5-flash",
                                label="模型", allow_custom_value=True,
                            )

                        def toggle_provider(p):
                            return (
                                gr.update(visible=p == "xfyun"),
                                gr.update(visible=p == "openai"),
                                gr.update(visible=p == "ollama"),
                                gr.update(visible=p == "gemini"),
                            )

                        provider.change(fn=toggle_provider, inputs=[provider], outputs=[xfyun_group, openai_group, ollama_group, gemini_group])

                        btn_refresh_ollama.click(
                            fn=lambda url: (
                                fetch_ollama_models() or [],
                                f"已刷新，发现 {len(state.ollama_models)} 个模型" if state.ollama_models else "未发现运行中的模型",
                            ),
                            inputs=[ollama_base_url], outputs=[ollama_model, api_status],
                        )

                        def on_xfyun_model_change(provider_val):
                            if provider_val == "xfyun":
                                return gr.update(choices=XF_MODELS, value="xsparkx2flash", visible=True)
                            return gr.update()
                        provider.change(fn=on_xfyun_model_change, inputs=[provider], outputs=[xfyun_model])

                        with gr.Row():
                            temperature = gr.Slider(minimum=0.0, maximum=2.0, value=0.7, step=0.1, label="Temperature")
                            max_tokens = gr.Slider(minimum=512, maximum=32768, value=8192, step=256, label="Max Tokens")

                        gr.HTML("<b>输出选项</b>")
                        with gr.Row():
                            add_camera = gr.Checkbox(value=True, label="添加镜头建议")
                            add_transitions = gr.Checkbox(value=True, label="添加转场")
                            preserve_narrative = gr.Checkbox(value=True, label="保留旁白")

                    with gr.Column(scale=2, min_width=500):
                        btn_convert = gr.Button("开始转换", variant="primary", size="lg")

                        status_output = gr.Textbox(label="处理状态", lines=4, interactive=False)
                        yaml_editor = gr.Code(label="剧本 YAML（可编辑）", language="yaml", lines=25)

                        with gr.Row():
                            btn_validate = gr.Button("验证 YAML", variant="secondary")
                            validation_result = gr.HTML("<span style='color:#888'>点击 验证 YAML 检查格式</span>")

                        btn_validate.click(fn=validate_yaml, inputs=[yaml_editor], outputs=[validation_result])

                        with gr.Accordion("导出选项", open=False):
                            with gr.Row():
                                btn_export_yaml = gr.Button("下载 YAML 文件", variant="primary")
                                btn_export_txt = gr.Button("导出为 TXT 剧本", variant="secondary")

                            export_yaml_file = gr.File(label="YAML 下载", visible=False)
                            export_txt_file = gr.Textbox(label="TXT 剧本预览", lines=15)

                            btn_export_yaml.click(fn=export_yaml, inputs=[yaml_editor, title_input], outputs=[export_yaml_file])
                            btn_export_txt.click(fn=export_screenplay, inputs=[yaml_editor], outputs=[export_txt_file])

                btn_convert.click(
                    fn=do_convert,
                    inputs=[
                        input_method, text_input, file_input, title_input, author_input,
                        provider, xfyun_model,
                        openai_api_key, openai_model,
                        ollama_model, ollama_base_url,
                        gemini_api_key, gemini_model,
                        temperature, max_tokens,
                        add_camera, add_transitions, preserve_narrative,
                    ],
                    outputs=[status_output, yaml_editor],
                )

            with gr.Tab("YAML Schema 参考"):
                gr.HTML("""
                <div style="padding: 16px; line-height: 1.8; font-size: 14px;">
                <h2>Novel2Script YAML Schema 参考</h2>
                <p style="color: var(--text-color-subdued);">完整 Schema 定义请参阅项目根目录的 <code>YAML_SCHEMA.md</code> 文件。</p>

                <h3>核心结构（5 个顶层键）</h3>
                <pre style="background: var(--background-fill-secondary); padding: 16px; border-radius: 8px; overflow-x: auto; font-size: 12px;">
script:        # 脚本基本元信息（必填）
metadata:      # 制作级元数据（必填）
characters:    # 角色列表（必填，>=1 个）
act_structure: # 幕结构定义（必填，3 个 act）
scenes:        # 场景列表（必填，>=1 个）
                </pre>

                <h3>characters — 角色定义</h3>
                <pre style="background: var(--background-fill-secondary); padding: 16px; border-radius: 8px; overflow-x: auto; font-size: 12px;">
- id: "char_001"              # 全局唯一 ID
  name: "角色名"               # 角色名
  role: "protagonist"          # protagonist | antagonist | supporting | minor | narrator
  description: "角色描述..."     # >=10 字符
  voice: "语音特征"             # 可选
  first_appearance: 1          # 首次出场场景编号
  relationships:               # 可选
    - target: "char_002"
      type: "family|mentor|friend|enemy|romantic|partner"
      description: "关系描述"
                </pre>

                <h3>scenes — 场景元素类型</h3>
                <table style="width:100%; border-collapse: collapse; font-size: 13px;">
                <tr style="background: var(--background-fill-secondary);">
                    <th style="padding:8px;border:1px solid var(--border-color)">type</th>
                    <th style="padding:8px;border:1px solid var(--border-color)">必填字段</th>
                    <th style="padding:8px;border:1px solid var(--border-color)">说明</th>
                </tr>
                <tr><td style="padding:8px;border:1px solid var(--border-color)">dialogue</td><td style="padding:8px;border:1px solid var(--border-color)">character, content</td><td style="padding:8px;border:1px solid var(--border-color)">角色对话</td></tr>
                <tr><td style="padding:8px;border:1px solid var(--border-color)">action</td><td style="padding:8px;border:1px solid var(--border-color)">content</td><td style="padding:8px;border:1px solid var(--border-color)">动作描述</td></tr>
                <tr><td style="padding:8px;border:1px solid var(--border-color)">narrative</td><td style="padding:8px;border:1px solid var(--border-color)">content</td><td style="padding:8px;border:1px solid var(--border-color)">旁白/叙述</td></tr>
                <tr><td style="padding:8px;border:1px solid var(--border-color)">transition</td><td style="padding:8px;border:1px solid var(--border-color)">content</td><td style="padding:8px;border:1px solid var(--border-color)">转场指令（淡入/淡出）</td></tr>
                <tr><td style="padding:8px;border:1px solid var(--border-color)">camera</td><td style="padding:8px;border:1px solid var(--border-color)">content</td><td style="padding:8px;border:1px solid var(--border-color)">镜头建议</td></tr>
                </table>

                <h3>设计亮点</h3>
                <ul>
                <li><b>全局角色表 + ID 引用</b>：角色在 <code>characters</code> 中定义一次，场景中通过 <code>char_XXX</code> ID 引用，避免名字不一致问题</li>
                <li><b>固定三幕制</b>：幕结构（Setup / Confrontation / Resolution）是剧本写作的事实标准</li>
                <li><b>扁平化 elements 列表</b>：对话、动作、旁白交替出现，保留剧本的节奏感</li>
                <li><b>镜头语言扩展</b>：camera 类型提供可选的镜头建议，不影响导演的创作自由</li>
                <li><b>可扩展字段</b>：以 <code>x_</code> 前缀添加自定义字段（导演注释、拍摄备注等）</li>
                </ul>
                </div>
                """)

            with gr.Tab("使用说明"):
                gr.HTML("""
                <div style="padding: 16px; line-height: 1.8; font-size: 14px;">
                <h2>使用说明</h2>

                <h3>快速开始</h3>
                <ol>
                <li>在「小说转剧本」标签页，选择输入方式（粘贴文本或上传文件）</li>
                <li>填写剧本标题和原作者（可选）</li>
                <li>选择 AI 提供商并配置 API Key</li>
                <li>调整输出选项，点击「开始转换」</li>
                <li>等待 AI 生成剧本 YAML，在编辑器中查看和修改</li>
                <li>导出为 YAML 文件或 TXT 剧本格式</li>
                </ol>

                <h3>AI 配置说明</h3>
                <table style="width:100%; border-collapse: collapse;">
                <tr style="background: var(--background-fill-secondary);">
                    <th style="padding:8px;border:1px solid var(--border-color)">提供商</th>
                    <th style="padding:8px;border:1px solid var(--border-color)">说明</th>
                    <th style="padding:8px;border:1px solid var(--border-color)">推荐模型</th>
                </tr>
                <tr><td style="padding:8px;border:1px solid var(--border-color)">讯飞 MaaS Coding</td><td style="padding:8px;border:1px solid var(--border-color)">内置 API Key，开箱即用</td><td style="padding:8px;border:1px solid var(--border-color)">xsparkx2flash</td></tr>
                <tr><td style="padding:8px;border:1px solid var(--border-color)">OpenAI</td><td style="padding:8px;border:1px solid var(--border-color)">效果最好，需要 API Key</td><td style="padding:8px;border:1px solid var(--border-color)">gpt-4o-mini</td></tr>
                <tr><td style="padding:8px;border:1px solid var(--border-color)">Ollama</td><td style="padding:8px;border:1px solid var(--border-color)">本地运行，免费</td><td style="padding:8px;border:1px solid var(--border-color)">qwen2.5</td></tr>
                <tr><td style="padding:8px;border:1px solid var(--border-color)">Gemini</td><td style="padding:8px;border:1px solid var(--border-color)">Google 多模态模型</td><td style="padding:8px;border:1px solid var(--border-color)">gemini-1.5-flash</td></tr>
                </table>

                <h3>支持的输入格式</h3>
                <ul>
                <li><b>.txt</b>：纯文本文件，自动检测编码（UTF-8/GBK/GB2312）</li>
                <li><b>.docx</b>：Word 文档，自动提取正文段落</li>
                <li><b>.pdf</b>：PDF 文档，提取文本内容</li>
                </ul>

                <h3>注意事项</h3>
                <ul>
                <li>小说至少需要包含 3 个章节，否则无法转换</li>
                <li>文本建议 3000 字以上，章节越多转换效果越好</li>
                <li>Ollama 需要本地安装并启动（运行 <code>ollama serve</code>）</li>
                <li>首次转换可能需要几分钟，取决于文本长度和 AI 模型速度</li>
                </ul>
                </div>
                """)

    return demo


# ── Entry Point ─────────────────────────────────────────────────

if __name__ == "__main__":
    demo = build_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
    )
