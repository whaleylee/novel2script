"""
Novel2Script — Gradio Web Interface
AI-powered novel to screenplay YAML converter.
"""

import os, re, time, httpx, threading, json
import gradio as gr
from datetime import datetime

# ── Constants ───────────────────────────────────────────────────

API_BASE = os.environ.get("NOVEL2SCRIPT_API", "http://localhost:8000")

XF_MODELS = [
    ("Spark X2 Flash (可用)", "xsparkx2flash"),
    ("Qwen3.5-35B-A3B (可用)", "xopqwen35v35b"),
    ("Qwen3.6-35B-A3B (可用)", "xopqwen36v35b"),
    ("Qwen3-Coder-Next-FP8 (可用)", "xop3qwencodernext"),
    ("GLM-4.7-Flash (可用)", "xopglmv47flash"),
    ("Spark X2", "xsparkx2"), ("GLM-5.1", "xopglm51"), ("GLM-5", "xopglm5"),
    ("DeepSeek-V4-Pro", "xopdeepseekv4pro"), ("DeepSeek-V4-Flash", "xopdeepseekv4flash"),
    ("DeepSeek-V3.2", "xopdeepseekv32"), ("Kimi-K2.6", "xopkimik26"),
    ("Kimi-K2.5", "xopkimik25"), ("MiniMax-M2.5", "xminimaxm25"),
    ("Qwen3.5-397B-A17B", "xopqwen35397b"),
]

OPENAI_MODELS = [
    ("GPT-4o (推荐)", "gpt-4o"), ("GPT-4o Mini", "gpt-4o-mini"),
    ("GPT-4 Turbo", "gpt-4-turbo"), ("GPT-3.5 Turbo", "gpt-3.5-turbo"),
]
OLLAMA_MODELS = [("qwen2.5", "qwen2.5"), ("deepseek-r1", "deepseek-r1"), ("llama3.1", "llama3.1"), ("mistral", "mistral")]
GEMINI_MODELS = [("Gemini 1.5 Flash", "gemini-1.5-flash"), ("Gemini 1.5 Pro", "gemini-1.5-pro"), ("Gemini 2.0 Flash", "gemini-2.0-flash")]

STYLE_CHOICES = [
    ("电影化 - 强镜头语言，视觉感强", "cinematic"),
    ("舞台戏剧 - 对话密集，聚焦人物", "theatrical"),
    ("可拍摄剧本 - 口语化，便于拍摄", "practical"),
    ("文学剧本 - 保留诗意，适合艺术片", "literary"),
    ("电视剧节奏 - 快节奏，短场景", "teleplay"),
]

EXPORT_FORMATS = [
    ("YAML (.yaml)", "yaml"), ("文本剧本 (.txt)", "txt"),
    ("Fountain (.fountain)", "fountain"), ("JSON (.json)", "json"),
]

# ── State ───────────────────────────────────────────────────────

class AppState:
    def __init__(self):
        self.ollama_connected = False
        self.ollama_models = []
state = AppState()

# ── Helpers ─────────────────────────────────────────────────────

def check_api():
    try:
        r = httpx.get(f"{API_BASE}/health", timeout=5)
        if r.status_code == 200:
            d = r.json()
            state.ollama_connected = d.get("ollama_connected", False)
            return d
    except Exception:
        pass
    return {"status": "offline"}

def fetch_ollama_models():
    try:
        r = httpx.get(f"{API_BASE}/ollama/models", timeout=5)
        if r.status_code == 200:
            d = r.json()
            state.ollama_connected = d.get("connected", False)
            state.ollama_models = [m.get("name","") for m in d.get("models",[]) if m.get("name")]
            return state.ollama_models
    except Exception:
        state.ollama_connected = False
    return []

# ── YAML Preview Renderer ───────────────────────────────────────

def render_preview(yaml_text):
    """Render YAML into a beautiful HTML preview."""
    if not yaml_text or not yaml_text.strip():
        return "<div style='color:#888;padding:2rem;text-align:center'>等待转换...</div>"

    try:
        import yaml
        data = yaml.safe_load(yaml_text)
        if not data:
            return "<div style='color:#888;padding:2rem'>解析中...</div>"
    except Exception:
        return "<div style='color:#888;padding:2rem;text-align:center'>等待转换完成...</div>"

    script = data.get("script", {})
    chars = data.get("characters", [])
    scenes = data.get("scenes", [])
    meta = data.get("metadata", {})
    acts = data.get("act_structure", [])

    char_map = {c.get("id",""): c.get("name","") for c in chars}

    html = "<div style='font-family:system-ui,sans-serif;font-size:14px;line-height:1.7;padding:8px'>"

    # Header
    title = script.get("title", "未命名")
    author = script.get("author", "")
    genre = script.get("genre", "")
    logline = script.get("logline", "")
    html += f"<div style='background:linear-gradient(135deg,#4338ca,#6366f1);color:#fff;padding:20px 24px;border-radius:12px;margin-bottom:16px'>"
    html += f"<h2 style='margin:0 0 4px 0;font-size:22px'>{title}</h2>"
    if author: html += f"<span style='opacity:0.85'>✍ {author}</span> &nbsp;"
    if genre: html += f"<span style='opacity:0.85'>🎬 {genre}</span>"
    if logline: html += f"<p style='margin:8px 0 0 0;opacity:0.9;font-style:italic'>{logline}</p>"
    html += "</div>"

    # Stats bar
    html += "<div style='display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px'>"
    html += f"<span style='background:#eef2ff;color:#4338ca;padding:6px 14px;border-radius:20px;font-weight:600'>🎬 {meta.get('total_scenes','?')} 场景</span>"
    html += f"<span style='background:#fef3c7;color:#92400e;padding:6px 14px;border-radius:20px;font-weight:600'>👥 {meta.get('total_characters','?')} 角色</span>"
    html += f"<span style='background:#ecfdf5;color:#065f46;padding:6px 14px;border-radius:20px;font-weight:600'>⏱ {meta.get('estimated_duration','?')}</span>"
    html += f"<span style='background:#fdf2f8;color:#9d174d;padding:6px 14px;border-radius:20px;font-weight:600'>🏗 3 幕</span>"
    html += "</div>"

    # Characters
    if chars:
        html += "<details open style='margin-bottom:12px'><summary style='cursor:pointer;font-weight:700;font-size:15px;padding:8px 0;color:#1e293b'>👤 角色表 ({})</summary>".format(len(chars))
        html += "<div style='display:flex;gap:8px;flex-wrap:wrap;padding:8px 0'>"
        role_colors = {"protagonist":"#6366f1","antagonist":"#ef4444","supporting":"#10b981","minor":"#6b7280","narrator":"#f59e0b"}
        role_labels = {"protagonist":"主角","antagonist":"反派","supporting":"配角","minor":"次要","narrator":"旁白"}
        for c in chars[:12]:
            role = c.get("role","")
            color = role_colors.get(role, "#6b7280")
            label = role_labels.get(role, role)
            html += f"<div style='border-left:3px solid {color};padding:6px 10px;background:#f8fafc;border-radius:6px;min-width:100px'>"
            html += f"<b>{c.get('name','?')}</b> <span style='font-size:11px;color:{color}'>{label}</span>"
            desc = c.get("description","")[:40]
            if desc: html += f"<br><span style='font-size:12px;color:#64748b'>{desc}</span>"
            html += "</div>"
        html += "</div></details>"

    # Act structure
    if acts:
        html += "<div style='display:flex;gap:8px;margin-bottom:16px'>"
        colors = ["#6366f1","#f59e0b","#10b981"]
        for a in acts:
            idx = a.get("act",1)-1
            c = colors[idx] if idx < 3 else "#6b7280"
            html += f"<div style='flex:1;background:{c}18;border:1px solid {c}40;border-radius:8px;padding:10px;text-align:center'>"
            html += f"<div style='font-weight:700;color:{c}'>{a.get('title','')}</div>"
            html += f"<div style='font-size:22px;font-weight:800'>{len(a.get('scenes',[]))}</div><div style='font-size:11px;color:#64748b'>场景</div>"
            html += "</div>"
        html += "</div>"

    # Scenes
    html += "<details open style='margin-bottom:12px'><summary style='cursor:pointer;font-weight:700;font-size:15px;padding:8px 0;color:#1e293b'>🎬 场景列表 ({})</summary>".format(len(scenes))
    for s in scenes[:20]:
        sid = s.get("id","?")
        loc = s.get("location","")
        t = s.get("time","")
        loc_type = s.get("location_type","")
        weather = s.get("weather","")
        loc_icon = "🏠" if loc_type == "int" else ("🌳" if loc_type == "ext" else "🏠🌳")
        chars_in = [char_map.get(c,c) for c in s.get("characters",[])]
        elements = s.get("elements",[])
        d_count = sum(1 for e in elements if e.get("type")=="dialogue")
        a_count = sum(1 for e in elements if e.get("type")=="action")
        n_count = sum(1 for e in elements if e.get("type")=="narrative")
        c_count = sum(1 for e in elements if e.get("type")=="camera")

        act_num = s.get("act","?")
        html += f"<div style='border:1px solid #e2e8f0;border-radius:10px;padding:10px 14px;margin-bottom:8px'>"
        html += f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px'>"
        html += f"<b style='color:#1e293b'>场景 {sid}</b>"
        html += f"<span style='font-size:11px;background:#f1f5f9;padding:2px 8px;border-radius:10px'>第{act_num}幕</span>"
        html += f"</div>"
        html += f"<div style='color:#64748b;font-size:13px'>{loc_icon} {loc} · {t}"
        if weather: html += f" · {weather}"
        html += f"</div>"
        if chars_in: html += f"<div style='font-size:12px;color:#94a3b8;margin:2px 0'>出场: {', '.join(chars_in[:6])}</div>"
        html += f"<div style='display:flex;gap:8px;margin-top:4px;font-size:11px;color:#64748b'>"
        html += f"<span>💬x{d_count}</span><span>🎬x{a_count}</span><span>📖x{n_count}</span><span>🎥x{c_count}</span>"
        html += "</div></div>"
    if len(scenes) > 20:
        html += f"<div style='color:#94a3b8;text-align:center;padding:8px'>... 还有 {len(scenes)-20} 个场景</div>"
    html += "</details>"

    html += "</div>"
    return html


def parse_progress(msg):
    """Extract progress percentage from backend status messages."""
    if "[STEP_1]" in msg: return 0.08, "📖 章节识别"
    if "[STEP_2]" in msg: return 0.16, "📊 文本分析"
    if "[STEP_3]" in msg and "正在构建" in msg: return 0.30, "🔍 构建角色图谱"
    if "[STEP_3]" in msg and "正在摘要" in msg:
        m = re.search(r"(\d+)/(\d+)", msg)
        if m:
            done, total = int(m.group(1)), int(m.group(2))
            pct = 0.18 + (done/total) * 0.12
            return min(pct, 0.38), f"📝 摘要章节 {done}/{total}"
        return 0.25, "📝 摘要章节"
    if "[STEP_4]" in msg and "正在生成" in msg:
        m = re.search(r"(\d+)/(\d+)", msg)
        if m:
            done, total = int(m.group(1)), int(m.group(2))
            pct = 0.38 + (done/total) * 0.52
            return min(pct, 0.92), f"⚙️ 生成场景 {done}/{total}"
        return 0.45, "⚙️ 逐章生成场景"
    if "[STEP_5]" in msg or "生成完成" in msg: return 0.98, "📦 格式化输出"
    return None, None


# ── Convert Logic ───────────────────────────────────────────────

def do_convert(
    input_method, text_input, file_input, title_input, author_input,
    provider, xfyun_model, openai_api_key, openai_model,
    ollama_model, ollama_base_url, gemini_api_key, gemini_model,
    temperature, max_tokens, style,
    progress=gr.Progress(),
):
    """Main conversion. Updates progress bar as conversion runs."""

    # Resolve text
    if input_method == "text":
        raw_text = text_input.strip()
    elif input_method == "file":
        if file_input is None:
            yield "请上传文件", "", render_preview("")
            return
        if isinstance(file_input, dict):
            fpath = file_input.get("path", "")
        elif isinstance(file_input, str):
            fpath = file_input
        else:
            fpath = str(file_input)
        try:
            with open(fpath, "rb") as f:
                raw_text = f.read().decode("utf-8", errors="replace")
        except Exception:
            yield "文件读取失败", "", render_preview("")
            return
    else:
        raw_text = text_input.strip() if text_input else ""

    if len(raw_text) < 500:
        yield "文本内容过短（至少需要 500 字符）", "", render_preview("")
        return

    # Resolve config
    api_key = None; model = "xsparkx2flash"; base_url = None
    if provider == "xfyun":
        model = xfyun_model or "xsparkx2flash"
    elif provider == "openai":
        api_key = openai_api_key or os.environ.get("OPENAI_API_KEY", "")
        model = openai_model
    elif provider == "ollama":
        model = ollama_model or "qwen2.5"
        base_url = ollama_base_url or "http://localhost:11434"
    elif provider == "gemini":
        api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        model = gemini_model

    # Use SSE streaming endpoint for progress, then get final YAML
    try:
        import requests as sync_requests

        # Phase 1: stream status for progress bar
        with sync_requests.post(
            f"{API_BASE}/convert",
            data={
                "text": raw_text, "provider": provider, "model": model,
                "temperature": str(temperature), "max_tokens": str(max_tokens),
                "title": title_input or "", "author": author_input or "",
                "api_key": api_key or "", "base_url": base_url or "",
            },
            stream=True, timeout=600,
        ) as stream_resp:
            if stream_resp.status_code != 200:
                yield f"请求失败: HTTP {stream_resp.status_code}", "", render_preview("")
                return

            last_status = ""
            for line in stream_resp.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                chunk = line[6:]
                if chunk.startswith("[ERROR]"):
                    yield f"错误: {chunk[7:]}", "", render_preview("")
                    return
                if "---YAML_OUTPUT_START---" in chunk or "---YAML_OUTPUT_END---" in chunk:
                    continue
                if chunk.strip():
                    last_status = chunk.strip()
                    pct, label = parse_progress(last_status)
                    if pct is not None and label:
                        progress(pct, desc=label)
                    yield last_status, "", render_preview("")

        # Phase 2: get final YAML via plain endpoint
        progress(0.95, desc="📦 获取最终结果")
        resp = sync_requests.post(
            f"{API_BASE}/convert/plain",
            json={
                "text": raw_text,
                "config": {"provider": provider, "model": model, "temperature": temperature, "max_tokens": max_tokens},
                "title": title_input or "", "author": author_input or "",
            },
            timeout=600,
        )

        if resp.status_code != 200:
            yield f"转换失败: {resp.text[:200]}", "", render_preview("")
            return

        import yaml as pyyaml
        yaml_text = resp.json().get("yaml", "")
        data = pyyaml.safe_load(yaml_text)
        scene_count = len(data.get("scenes", []))
        char_count = len(data.get("characters", []))

        progress(1.0, desc="✅ 完成")
        yield f"转换完成：{scene_count} 个场景，{char_count} 个角色", yaml_text, render_preview(yaml_text)

    except Exception as e:
        yield f"请求失败: {str(e)}", "", render_preview("")

# ── Validation & Export ─────────────────────────────────────────

def validate_yaml(yaml_text):
    if not yaml_text.strip():
        return "YAML 内容为空"
    try:
        import yaml
        data = yaml.safe_load(yaml_text)
        sc = len(data.get("scenes",[]))
        cc = len(data.get("characters",[]))
        return f"✅ YAML 格式正确 — {sc} 个场景，{cc} 个角色"
    except Exception as e:
        return f"❌ YAML 解析错误: {str(e)[:100]}"

def do_export(yaml_text, fmt):
    if not yaml_text.strip():
        return gr.update(visible=False), gr.update(visible=False)
    try:
        fname = f"screenplay_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if fmt == "yaml":
            return gr.update(value=yaml_text, visible=True), gr.update(visible=False)
        elif fmt == "txt":
            import requests
            r = requests.post(f"{API_BASE}/export/txt?yaml_text={requests.utils.quote(yaml_text)}", timeout=10)
            if r.status_code == 200:
                content = r.json().get("content", yaml_text)
                return gr.update(visible=False), gr.update(value=content, visible=True)
        elif fmt in ("fountain", "json"):
            import requests
            r = requests.post(f"{API_BASE}/export/{fmt}?yaml_text={requests.utils.quote(yaml_text)}", timeout=10)
            if r.status_code == 200:
                content = r.json().get("content", yaml_text)
                ext = r.json().get("ext", f".{fmt}")
                return gr.update(value=content, visible=True), gr.update(visible=False)
    except Exception as e:
        pass
    return gr.update(visible=False), gr.update(visible=False)

# ── Build UI ────────────────────────────────────────────────────

def build_ui():
    css = """
    .gradio-container { max-width: 1500px !important; }
    #yaml-editor textarea { font-family: 'JetBrains Mono','Fira Code',monospace !important; font-size: 12px !important; }
    .preview-scroll { max-height: 75vh; overflow-y: auto; }
    """

    with gr.Blocks(title="Novel2Script · AI 小说转剧本", css=css) as demo:

        # Header
        gr.HTML("""
        <div style='text-align:center;padding:16px 0'>
        <h1 style='margin:0;font-size:28px'>Novel2Script · AI 小说转剧本</h1>
        <p style='color:#64748b;margin:4px 0 0 0'>将小说文本智能转换为结构化剧本 YAML</p>
        </div>
        """)

        with gr.Row():
            api_status = gr.HTML("<span style='color:#888;font-size:13px'>检查后端连接...</span>")

        demo.load(
            fn=lambda: "🟢 后端已连接" if check_api().get("status")=="ok" else "🔴 后端未连接",
            outputs=[api_status],
        )

        with gr.Tabs():
            # ═══ Tab 1: Convert ═══
            with gr.Tab("📖 小说转剧本"):
                with gr.Row(equal_height=False):
                    # Left panel
                    with gr.Column(scale=1, min_width=340):
                        gr.HTML("<h3 style='margin:8px 0'>📁 输入</h3>")
                        input_method = gr.Radio(["text","file"], value="text", label="输入方式")

                        with gr.Group(visible=True) as text_group:
                            text_input = gr.Textbox(
                                label="小说文本",
                                placeholder="在此粘贴小说章节内容（至少 3 章，建议 1000+ 字）...",
                                lines=11,
                            )
                        with gr.Group(visible=False) as file_group:
                            file_input = gr.File(label="上传文件", file_types=[".txt",".docx",".pdf"])

                        input_method.change(
                            lambda m: (gr.update(visible=m=="text"), gr.update(visible=m=="file")),
                            [input_method], [text_group, file_group],
                        )

                        gr.HTML("<h3 style='margin:12px 0 8px 0'>📝 剧本信息</h3>")
                        title_input = gr.Textbox(label="剧本标题", placeholder="自动提取或手动填写", lines=1)
                        author_input = gr.Textbox(label="原作者", placeholder="作者名称", lines=1)

                        gr.HTML("<h3 style='margin:12px 0 8px 0'>🤖 AI 配置</h3>")
                        provider = gr.Radio(["xfyun","openai","ollama","gemini"], value="xfyun", label="AI 提供商")

                        with gr.Group(visible=True) as xfyun_group:
                            xfyun_model = gr.Dropdown(
                                choices=[v for _,v in XF_MODELS], value="xsparkx2flash",
                                label="模型", allow_custom_value=True,
                            )
                        with gr.Group(visible=False) as openai_group:
                            openai_api_key = gr.Textbox(label="API Key", placeholder="sk-...", type="password")
                            openai_model = gr.Dropdown(choices=[v for _,v in OPENAI_MODELS], value="gpt-4o-mini", label="模型", allow_custom_value=True)
                        with gr.Group(visible=False) as ollama_group:
                            ollama_base_url = gr.Textbox(label="Ollama 地址", value="http://localhost:11434")
                            ollama_model = gr.Dropdown(choices=[v for _,v in OLLAMA_MODELS], value="qwen2.5", label="模型", allow_custom_value=True)
                            btn_refresh = gr.Button("🔄 检测模型", size="sm")
                        with gr.Group(visible=False) as gemini_group:
                            gemini_api_key = gr.Textbox(label="API Key", placeholder="AIza...", type="password")
                            gemini_model = gr.Dropdown(choices=[v for _,v in GEMINI_MODELS], value="gemini-1.5-flash", label="模型", allow_custom_value=True)

                        def toggle_provider(p):
                            return tuple(gr.update(visible=p==x) for x in ["xfyun","openai","ollama","gemini"])
                        provider.change(toggle_provider, [provider], [xfyun_group,openai_group,ollama_group,gemini_group])

                        btn_refresh.click(
                            lambda url: (fetch_ollama_models() or [], f"发现 {len(state.ollama_models)} 个模型" if state.ollama_models else "未发现模型"),
                            [ollama_base_url], [ollama_model, api_status],
                        )

                        gr.HTML("<h3 style='margin:12px 0 8px 0'>🎨 剧本风格</h3>")
                        style_input = gr.Dropdown(choices=[(k,v) for k,_,v in [(a,b,c) for a,b,c in [(x[0],None,x[1]) for x in STYLE_CHOICES]]], value="cinematic", label="风格预设")

                        with gr.Row():
                            temperature = gr.Slider(0.0, 2.0, 0.7, step=0.1, label="创意度")
                            max_tokens = gr.Slider(512, 32768, 8192, step=256, label="最大长度")

                        btn_convert = gr.Button("🚀 开始转换", variant="primary", size="lg")

                        status_output = gr.Textbox(label="处理状态", lines=3, interactive=False)

                    # Right panel: dual pane
                    with gr.Column(scale=2, min_width=500):
                        with gr.Tabs():
                            with gr.Tab("📄 YAML 源码"):
                                yaml_editor = gr.Code(label="剧本 YAML（可编辑）", language="yaml", lines=30, elem_id="yaml-editor")
                            with gr.Tab("👁 可视化预览"):
                                preview_output = gr.HTML(
                                    "<div style='color:#888;padding:3rem;text-align:center;font-size:15px'>"
                                    "📖 点击「开始转换」后，这里将实时展示剧本结构预览<br>"
                                    "<span style='font-size:13px'>包括角色卡片、场景列表、幕结构统计</span></div>",
                                    elem_classes=["preview-scroll"],
                                )

                        with gr.Row():
                            btn_validate = gr.Button("✅ 验证 YAML", variant="secondary", size="sm")
                            validation_result = gr.HTML("<span style='color:#888;font-size:13px'>点击验证 YAML 格式</span>")

                        btn_validate.click(validate_yaml, [yaml_editor], [validation_result])

                        with gr.Accordion("📥 多格式导出", open=False):
                            with gr.Row():
                                export_fmt = gr.Dropdown(
                                    choices=[(k,v) for k,_,v in [(x[0],None,x[1]) for x in EXPORT_FORMATS]],
                                    value="yaml", label="导出格式",
                                )
                                btn_export = gr.Button("💾 导出", variant="primary", size="sm")

                            export_file = gr.File(label="YAML 下载", visible=False)
                            export_preview = gr.Textbox(label="导出内容预览", lines=12, visible=False)

                            btn_export.click(do_export, [yaml_editor, export_fmt], [export_file, export_preview])

                # Wire convert
                inputs_list = [
                    input_method, text_input, file_input, title_input, author_input,
                    provider, xfyun_model, openai_api_key, openai_model,
                    ollama_model, ollama_base_url, gemini_api_key, gemini_model,
                    temperature, max_tokens, style_input,
                ]
                btn_convert.click(do_convert, inputs=inputs_list, outputs=[status_output, yaml_editor, preview_output])

            # ═══ Tab 2: Schema ═══
            with gr.Tab("📋 Schema 参考"):
                gr.HTML("""
                <div style='padding:16px;line-height:1.8;font-size:14px'>
                <h2>Novel2Script YAML Schema</h2>
                <p>完整文档见 <code>YAML_SCHEMA.md</code></p>
                <h3>5 个顶层键</h3>
                <pre style='background:#f8fafc;padding:12px;border-radius:8px'>
script:        # 基本元信息
metadata:      # 制作元数据
characters:    # 角色列表 (>=1)
act_structure: # 幕结构 (3 acts)
scenes:        # 场景列表 (>=1)</pre>
                <h3>元素类型</h3>
                <table style='width:100%;border-collapse:collapse;font-size:13px'>
                <tr style='background:#f1f5f9'><th style='padding:6px'>type</th><th>必填字段</th><th>说明</th></tr>
                <tr><td style='padding:4px'>dialogue</td><td>character, content</td><td>角色对话</td></tr>
                <tr><td style='padding:4px'>action</td><td>content</td><td>动作描述</td></tr>
                <tr><td style='padding:4px'>narrative</td><td>content</td><td>旁白/叙述</td></tr>
                <tr><td style='padding:4px'>transition</td><td>content</td><td>转场指令</td></tr>
                <tr><td style='padding:4px'>camera</td><td>content</td><td>镜头建议</td></tr>
                </table>
                </div>""")

            # ═══ Tab 3: Help ═══
            with gr.Tab("❓ 使用说明"):
                gr.HTML("""
                <div style='padding:16px;line-height:1.8;font-size:14px'>
                <h2>快速开始</h2>
                <ol>
                <li>粘贴小说文本或上传文件（支持 .txt/.docx/.pdf）</li>
                <li>选择 AI 提供商和模型（默认讯飞，开箱即用）</li>
                <li>选择剧本风格预设</li>
                <li>点击「开始转换」</li>
                <li>在「YAML 源码」和「可视化预览」之间切换查看结果</li>
                <li>导出为 YAML / TXT / Fountain / JSON</li>
                </ol>
                </div>""")

    return demo


if __name__ == "__main__":
    demo = build_ui()
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False, show_error=True)
