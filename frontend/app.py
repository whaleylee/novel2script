"""
Novel2Script — Gradio Web Interface
AI-powered novel to screenplay YAML converter.
"""

import os, re, httpx
import gradio as gr

API_BASE = os.environ.get("NOVEL2SCRIPT_API", "http://localhost:8000")

# ── Model Lists ──────────────────────────────────────────────────

XF_MODELS = [
    ("Spark X2 Flash", "xsparkx2flash"), ("Qwen3.5-35B-A3B", "xopqwen35v35b"),
    ("Qwen3.6-35B-A3B", "xopqwen36v35b"), ("Qwen3-Coder-Next-FP8", "xop3qwencodernext"),
    ("GLM-4.7-Flash", "xopglmv47flash"), ("Spark X2", "xsparkx2"),
    ("GLM-5.1", "xopglm51"), ("GLM-5", "xopglm5"),
    ("DeepSeek-V4-Pro", "xopdeepseekv4pro"), ("DeepSeek-V4-Flash", "xopdeepseekv4flash"),
    ("DeepSeek-V3.2", "xopdeepseekv32"), ("Kimi-K2.6", "xopkimik26"),
    ("Kimi-K2.5", "xopkimik25"), ("MiniMax-M2.5", "xminimaxm25"),
    ("Qwen3.5-397B-A17B", "xopqwen35397b"),
]
OPENAI_MODELS = [("GPT-4o", "gpt-4o"), ("GPT-4o Mini", "gpt-4o-mini"), ("GPT-4 Turbo", "gpt-4-turbo"), ("GPT-3.5 Turbo", "gpt-3.5-turbo")]
OLLAMA_MODELS = [("qwen2.5", "qwen2.5"), ("deepseek-r1", "deepseek-r1"), ("llama3.1", "llama3.1"), ("mistral", "mistral")]
GEMINI_MODELS = [("Gemini 1.5 Flash", "gemini-1.5-flash"), ("Gemini 1.5 Pro", "gemini-1.5-pro"), ("Gemini 2.0 Flash", "gemini-2.0-flash")]

STYLE_CHOICES = [
    ("电影化 - 强镜头语言", "cinematic"), ("舞台戏剧 - 对话密集", "theatrical"),
    ("可拍摄剧本 - 口语化", "practical"), ("文学剧本 - 保留诗意", "literary"),
    ("电视剧节奏 - 快节奏", "teleplay"),
]
EXPORT_FORMATS = [("YAML (.yaml)", "yaml"), ("文本剧本 (.txt)", "txt"), ("Fountain (.fountain)", "fountain"), ("JSON (.json)", "json")]

# ── State ────────────────────────────────────────────────────────

class AppState:
    def __init__(self):
        self.ollama_connected = False
        self.ollama_models = []
state = AppState()

# ── Helpers ──────────────────────────────────────────────────────

def check_api():
    try:
        r = httpx.get(f"{API_BASE}/health", timeout=5)
        if r.status_code == 200:
            d = r.json(); state.ollama_connected = d.get("ollama_connected", False)
            return d
    except Exception: pass
    return {"status": "offline"}

def fetch_ollama_models():
    try:
        r = httpx.get(f"{API_BASE}/ollama/models", timeout=5)
        if r.status_code == 200:
            d = r.json(); state.ollama_connected = d.get("connected", False)
            state.ollama_models = [m.get("name","") for m in d.get("models",[]) if m.get("name")]
            return state.ollama_models
    except Exception: state.ollama_connected = False
    return []

# ── Preview Renderer ─────────────────────────────────────────────

def render_preview(yaml_text):
    if not yaml_text or not yaml_text.strip():
        return "<div style='color:#888;padding:3rem;text-align:center'>等待转换...</div>"
    try:
        import yaml; data = yaml.safe_load(yaml_text)
        if not data: return "<div style='color:#888;padding:2rem'>解析中...</div>"
    except Exception: return "<div style='color:#888;padding:3rem;text-align:center'>等待转换完成...</div>"

    script, chars, scenes, meta, acts = data.get("script",{}), data.get("characters",[]), data.get("scenes",[]), data.get("metadata",{}), data.get("act_structure",[])
    char_map = {c.get("id",""): c.get("name","") for c in chars}
    html = "<div style='font-family:system-ui,sans-serif;font-size:14px;line-height:1.6;padding:8px'>"

    # 标题卡片
    html += f"<div style='background:linear-gradient(135deg,#4338ca,#6366f1);color:#fff;padding:16px 20px;border-radius:10px;margin-bottom:12px'>"
    html += f"<h2 style='margin:0 0 2px 0;font-size:20px'>{script.get('title','未命名')}</h2>"
    if script.get('logline'): html += f"<p style='margin:4px 0 0 0;opacity:0.9;font-style:italic'>{script.get('logline')}</p>"
    html += "</div>"

    # 统计条
    html += "<div style='display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px'>"
    html += f"<span style='background:#eef2ff;color:#4338ca;padding:4px 12px;border-radius:20px;font-weight:600'>场景: {meta.get('total_scenes','?')}</span>"
    html += f"<span style='background:#fef3c7;color:#92400e;padding:4px 12px;border-radius:20px;font-weight:600'>角色: {meta.get('total_characters','?')}</span>"
    html += f"<span style='background:#ecfdf5;color:#065f46;padding:4px 12px;border-radius:20px;font-weight:600'>时长: {meta.get('estimated_duration','?')}</span>"
    html += "</div>"

    # 角色表
    if chars:
        html += "<details open style='margin-bottom:10px'><summary style='cursor:pointer;font-weight:700;font-size:14px;padding:6px 0'>角色表 ({})</summary>".format(len(chars))
        html += "<div style='display:flex;gap:6px;flex-wrap:wrap;padding:6px 0'>"
        rc = {"protagonist":"#6366f1","antagonist":"#ef4444","supporting":"#10b981","minor":"#6b7280","narrator":"#f59e0b"}
        rl = {"protagonist":"主角","antagonist":"反派","supporting":"配角","minor":"次要","narrator":"旁白"}
        for c in chars[:12]:
            role = c.get("role",""); color = rc.get(role, "#6b7280")
            html += f"<div style='border-left:3px solid {color};padding:4px 8px;background:#f8fafc;border-radius:5px;min-width:80px'>"
            html += f"<b>{c.get('name','?')}</b> <span style='font-size:10px;color:{color}'>{rl.get(role,role)}</span>"
            if c.get("description",""): html += f"<br><span style='font-size:11px;color:#64748b'>{c['description'][:30]}</span>"
            html += "</div>"
        html += "</div></details>"

    # 幕卡片
    if acts:
        html += "<div style='display:flex;gap:6px;margin-bottom:10px'>"
        for a in acts:
            idx = a.get("act",1)-1; c = ["#6366f1","#f59e0b","#10b981"][idx] if idx<3 else "#6b7280"
            html += f"<div style='flex:1;background:{c}14;border:1px solid {c}30;border-radius:8px;padding:8px;text-align:center'>"
            html += f"<div style='font-weight:700;color:{c};font-size:13px'>{a.get('title','')}</div>"
            html += f"<div style='font-size:20px;font-weight:800'>{len(a.get('scenes',[]))}</div><div style='font-size:10px;color:#64748b'>场景</div></div>"
        html += "</div>"

    # 场景列表
    html += "<details open><summary style='cursor:pointer;font-weight:700;font-size:14px;padding:6px 0'>场景列表 ({})</summary>".format(len(scenes))
    for s in scenes[:20]:
        sid, loc, t, lt = s.get("id","?"), s.get("location",""), s.get("time",""), s.get("location_type","")
        li = "内" if lt=="int" else ("外" if lt=="ext" else "内外")
        ch_in = [char_map.get(c,c) for c in s.get("characters",[])]
        el = s.get("elements",[])
        d,a,n,c = sum(1 for e in el if e.get("type")=="dialogue"), sum(1 for e in el if e.get("type")=="action"), sum(1 for e in el if e.get("type")=="narrative"), sum(1 for e in el if e.get("type")=="camera")
        html += f"<div style='border:1px solid #e2e8f0;border-radius:8px;padding:8px 12px;margin-bottom:6px'>"
        html += f"<b>场景{sid}</b> <span style='font-size:11px;background:#f1f5f9;padding:1px 6px;border-radius:8px'>第{s.get('act','?')}幕</span>"
        html += f"<span style='color:#64748b;font-size:12px;margin-left:8px'>[{li}] {loc} - {t}</span>"
        if ch_in: html += f"<div style='font-size:11px;color:#94a3b8'>出场: {', '.join(ch_in[:6])}</div>"
        html += f"<div style='font-size:10px;color:#64748b;margin-top:2px'>对话x{d} 动作x{a} 旁白x{n} 镜头x{c}</div></div>"
    if len(scenes) > 20: html += f"<div style='color:#94a3b8;text-align:center;padding:6px'>... 还有 {len(scenes)-20} 个场景</div>"
    html += "</details></div>"
    return html

def parse_progress(msg):
    if "[STEP_1]" in msg: return 0.08, "正在识别章节..."
    if "[STEP_2]" in msg: return 0.16, "正在分析文本..."
    if "[STEP_3]" in msg and "构建" in msg: return 0.30, "正在构建角色图谱..."
    if "[STEP_3]" in msg:
        m = re.search(r"(\d+)/(\d+)", msg)
        if m: return 0.18+(int(m.group(1))/int(m.group(2)))*0.12, f"正在摘要章节 {m.group(1)}/{m.group(2)}"
        return 0.25, "正在摘要章节..."
    if "[STEP_4]" in msg:
        m = re.search(r"(\d+)/(\d+)", msg)
        if m: return 0.38+(int(m.group(1))/int(m.group(2)))*0.52, f"正在生成场景 {m.group(1)}/{m.group(2)}"
        return 0.45, "正在逐章生成场景..."
    if "[STEP_5]" in msg: return 0.98, "正在格式化输出..."
    return None, None

# ── Convert Logic ────────────────────────────────────────────────

def do_convert(
    input_method, text_input, file_input, title_input, author_input,
    provider, xfyun_api_key, xfyun_model, openai_api_key, openai_model,
    ollama_model, ollama_base_url, gemini_api_key, gemini_model,
    temperature, max_tokens, style,
    progress=gr.Progress(),
):
    # 解析输入文本
    if input_method == "text": raw_text = text_input.strip()
    elif input_method == "file":
        if file_input is None: yield "请上传文件", "", render_preview(""); return
        fpath = file_input.get("path","") if isinstance(file_input, dict) else str(file_input)
        try:
            with open(fpath, "rb") as f: raw_text = f.read().decode("utf-8", errors="replace")
        except Exception: yield "文件读取失败", "", render_preview(""); return
    else: raw_text = text_input.strip() if text_input else ""

    if len(raw_text) < 500:
        yield "文本内容过短（至少需要 500 字符）", "", render_preview(""); return

    # 解析 API 配置
    api_key, model, base_url = None, None, None
    if provider == "xfyun":
        api_key = xfyun_api_key or os.environ.get("XF_API_KEY", "")
        if not api_key: yield "请输入讯飞 API Key", "", render_preview(""); return
        model = xfyun_model or "xsparkx2flash"
    elif provider == "openai":
        api_key = openai_api_key or os.environ.get("OPENAI_API_KEY", "")
        if not api_key: yield "请输入 OpenAI API Key", "", render_preview(""); return
        model = openai_model
    elif provider == "ollama":
        model = ollama_model or "qwen2.5"
        base_url = ollama_base_url or "http://localhost:11434"
    elif provider == "gemini":
        api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        if not api_key: yield "请输入 Gemini API Key", "", render_preview(""); return
        model = gemini_model

    try:
        import requests as sync_requests

        # 阶段一：SSE 流式获取进度
        with sync_requests.post(f"{API_BASE}/convert", data={
            "text": raw_text, "provider": provider, "model": model,
            "temperature": str(temperature), "max_tokens": str(max_tokens),
            "title": title_input or "", "author": author_input or "",
            "api_key": api_key or "", "base_url": base_url or "",
        }, stream=True, timeout=600) as sr:
            if sr.status_code != 200: yield f"请求失败: HTTP {sr.status_code}", "", render_preview(""); return
            for line in sr.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "): continue
                chunk = line[6:]
                if chunk.startswith("[ERROR]"): yield f"错误: {chunk[7:]}", "", render_preview(""); return
                if "---YAML_OUTPUT" in chunk: continue
                if chunk.strip():
                    pct, label = parse_progress(chunk.strip())
                    if pct and label: progress(pct, desc=label)
                    yield chunk.strip(), "", render_preview("")

        # 阶段二：获取最终 YAML
        progress(0.95, desc="正在获取最终结果...")
        resp = sync_requests.post(f"{API_BASE}/convert/plain", json={
            "text": raw_text,
            "config": {"provider": provider, "model": model, "temperature": temperature, "max_tokens": max_tokens},
            "title": title_input or "", "author": author_input or "",
        }, timeout=600)

        if resp.status_code != 200: yield f"转换失败: {resp.text[:200]}", "", render_preview(""); return
        import yaml as pyyaml
        yt = resp.json().get("yaml","")
        data = pyyaml.safe_load(yt)
        sc, cc = len(data.get("scenes",[])), len(data.get("characters",[]))
        progress(1.0, desc="完成")
        yield f"转换完成：{sc} 个场景，{cc} 个角色", yt, render_preview(yt)
    except Exception as e:
        yield f"请求失败: {str(e)}", "", render_preview("")

# ── Export ──────────────────────────────────────────────────────

def validate_yaml(yt):
    if not yt.strip(): return "YAML 内容为空"
    try:
        import yaml; d = yaml.safe_load(yt)
        return f"格式正确：{len(d.get('scenes',[]))} 个场景，{len(d.get('characters',[]))} 个角色"
    except Exception as e: return f"解析错误: {str(e)[:100]}"

def do_export(yt, fmt):
    if not yt.strip(): return gr.update(visible=False), gr.update(visible=False)
    try:
        if fmt == "yaml": return gr.update(value=yt, visible=True), gr.update(visible=False)
        import requests
        r = requests.post(f"{API_BASE}/export/{fmt}?yaml_text={requests.utils.quote(yt)}", timeout=10)
        if r.status_code == 200:
            c = r.json().get("content", yt)
            return gr.update(value=c, visible=True), gr.update(visible=False)
    except Exception: pass
    return gr.update(visible=False), gr.update(visible=False)

# ── Build UI ────────────────────────────────────────────────────

def build_ui():
    css = """
    .gradio-container { max-width: 1600px !important; }
    #yaml-editor textarea { font-family: 'JetBrains Mono','Fira Code',monospace !important; font-size: 12px !important; }
    """

    with gr.Blocks(title="Novel2Script · AI 小说转剧本", css=css) as demo:

        gr.HTML("""
        <div style='text-align:center;padding:12px 0 4px 0'>
        <h1 style='margin:0;font-size:26px'>Novel2Script · AI 小说转剧本</h1>
        <p style='color:#64748b;margin:2px 0 0 0;font-size:14px'>将小说文本（3 章以上）智能转换为结构化剧本 YAML</p>
        </div>""")

        with gr.Row():
            api_status = gr.HTML("<span style='color:#888;font-size:12px'>正在检查连接...</span>")
        demo.load(fn=lambda: "后端已连接" if check_api().get("status")=="ok" else "后端未连接", outputs=[api_status])

        with gr.Tabs():
            # ═══ Tab 1: 转换 ═══
            with gr.Tab("小说转剧本"):
                with gr.Row(equal_height=False):
                    # --- 左侧：紧凑配置面板 ---
                    with gr.Column(scale=1, min_width=340):
                        # 输入方式
                        input_method = gr.Radio(["text","file"], value="text", label="输入方式")
                        with gr.Group(visible=True) as text_group:
                            text_input = gr.Textbox(label="小说文本", placeholder="在此粘贴小说章节内容（至少 3 章，建议 1000+ 字）...", lines=10)
                        with gr.Group(visible=False) as file_group:
                            file_input = gr.File(label="上传文件", file_types=[".txt",".docx",".pdf"])
                        input_method.change(lambda m: (gr.update(visible=m=="text"), gr.update(visible=m=="file")), [input_method], [text_group, file_group])

                        # 标题/作者
                        with gr.Row():
                            title_input = gr.Textbox(label="剧本标题", placeholder="自动提取或手动填写", scale=2)
                            author_input = gr.Textbox(label="原作者", placeholder="选填", scale=1)

                        # AI 提供商 + API Key（紧凑排列）
                        with gr.Row():
                            provider = gr.Dropdown([("讯飞 MaaS Coding","xfyun"),("OpenAI","openai"),("Ollama","ollama"),("Gemini","gemini")], value="xfyun", label="AI 提供商", scale=1)
                            xfyun_api_key = gr.Textbox(label="API Key", placeholder="请输入讯飞 API Key", type="password", visible=True, scale=2)
                            openai_api_key = gr.Textbox(label="API Key", placeholder="sk-...", type="password", visible=False, scale=2)
                            ollama_api_key = gr.Textbox(label="API Key（无需填写）", visible=False, scale=2, interactive=False)
                            gemini_api_key = gr.Textbox(label="API Key", placeholder="AIza...", type="password", visible=False, scale=2)

                        def on_provider_change(p):
                            return tuple(gr.update(visible=p==x) for x in ["xfyun","openai","ollama","gemini"])
                        provider.change(on_provider_change, [provider], [xfyun_api_key, openai_api_key, ollama_api_key, gemini_api_key])

                        # 模型 + 风格
                        with gr.Row():
                            xfyun_model = gr.Dropdown(choices=[v for _,v in XF_MODELS], value="xsparkx2flash", label="模型", visible=True, scale=1)
                            openai_model = gr.Dropdown(choices=[v for _,v in OPENAI_MODELS], value="gpt-4o-mini", label="模型", visible=False, scale=1)
                            ollama_model = gr.Dropdown(choices=[v for _,v in OLLAMA_MODELS], value="qwen2.5", label="模型", visible=False, scale=1)
                            gemini_model = gr.Dropdown(choices=[v for _,v in GEMINI_MODELS], value="gemini-1.5-flash", label="模型", visible=False, scale=1)
                            style_input = gr.Dropdown(choices=[(x[0], x[1]) for x in STYLE_CHOICES], value="cinematic", label="剧本风格", scale=1)

                        provider.change(lambda p: (gr.update(visible=p=="xfyun"), gr.update(visible=p=="openai"), gr.update(visible=p=="ollama"), gr.update(visible=p=="gemini")), [provider], [xfyun_model, openai_model, ollama_model, gemini_model])

                        # Temperature + Max Tokens
                        with gr.Row():
                            temperature = gr.Slider(0.0, 2.0, 0.7, step=0.1, label="创意度 (Temperature)")
                            max_tokens = gr.Slider(512, 32768, 8192, step=256, label="最大长度 (Max Tokens)")

                        # 转换按钮 + 状态
                        btn_convert = gr.Button("开始转换", variant="primary", size="lg")
                        status_output = gr.Textbox(label="处理状态", lines=2, interactive=False)

                        # Ollama 刷新
                        with gr.Row(visible=False) as ollama_row:
                            ollama_base_url = gr.Textbox(value="http://localhost:11434", label="Ollama 地址", scale=2)
                            btn_refresh = gr.Button("检测模型", size="sm", scale=1)
                        provider.change(lambda p: gr.update(visible=p=="ollama"), [provider], [ollama_row])
                        btn_refresh.click(lambda url: (fetch_ollama_models() or [], f"发现 {len(state.ollama_models)} 个模型" if state.ollama_models else "未发现运行中的模型"), [ollama_base_url], [ollama_model, api_status])

                    # --- 右侧：双栏输出 ---
                    with gr.Column(scale=3, min_width=600):
                        with gr.Tabs():
                            with gr.Tab("YAML 源码"):
                                yaml_editor = gr.Code(label="剧本 YAML（可编辑）", language="yaml", lines=28, elem_id="yaml-editor")
                            with gr.Tab("可视化预览"):
                                preview_output = gr.HTML("<div style='color:#888;padding:3rem;text-align:center'>点击「<b>开始转换</b>」开始</div>")

                        with gr.Row():
                            btn_validate = gr.Button("验证 YAML", variant="secondary", size="sm")
                            validation_result = gr.HTML("<span style='color:#888;font-size:12px'>点击验证 YAML 格式</span>")

                        btn_validate.click(validate_yaml, [yaml_editor], [validation_result])

                        with gr.Accordion("多格式导出", open=False):
                            with gr.Row():
                                export_fmt = gr.Dropdown(choices=[(a[0],a[1]) for a in EXPORT_FORMATS], value="yaml", label="导出格式", scale=2)
                                btn_export = gr.Button("导出", variant="primary", size="sm", scale=1)
                            with gr.Row():
                                export_file = gr.File(label="下载", visible=False)
                                export_preview = gr.Textbox(label="预览", lines=10, visible=False)
                            btn_export.click(do_export, [yaml_editor, export_fmt], [export_file, export_preview])

                # 绑定转换按钮
                btn_convert.click(do_convert, inputs=[
                    input_method, text_input, file_input, title_input, author_input,
                    provider, xfyun_api_key, xfyun_model, openai_api_key, openai_model,
                    ollama_model, ollama_base_url, gemini_api_key, gemini_model,
                    temperature, max_tokens, style_input,
                ], outputs=[status_output, yaml_editor, preview_output])

            # ═══ Tab 2: Schema 参考 ═══
            with gr.Tab("YAML Schema"):
                gr.HTML("""
                <div style='padding:16px;line-height:1.8;font-size:14px'>
                <h2>Novel2Script YAML Schema</h2>
                <p>完整文档见项目根目录 <code>YAML_SCHEMA.md</code></p>
                <h3>5 个顶层键</h3>
                <pre style='background:#f8fafc;padding:12px;border-radius:8px'>
script:        # 基本元信息（标题、作者、类型、一句话简介）
metadata:      # 制作元数据（场景数、角色数、时长等）
characters:    # 角色列表（全局唯一 ID 引用）
act_structure: # 幕结构（固定 3 幕，含各幕场景编号）
scenes:        # 场景列表（含类型化元素）</pre>
                <h3>场景元素类型</h3>
                <table style='width:100%;border-collapse:collapse;font-size:13px'>
                <tr style='background:#f1f5f9'><th style='padding:6px'>type</th><th>必填字段</th><th>说明</th></tr>
                <tr><td style='padding:4px'>dialogue</td><td>character, content</td><td>角色对话</td></tr>
                <tr><td style='padding:4px'>action</td><td>content</td><td>动作描述</td></tr>
                <tr><td style='padding:4px'>narrative</td><td>content</td><td>旁白/叙述</td></tr>
                <tr><td style='padding:4px'>transition</td><td>content</td><td>转场指令（淡入/淡出）</td></tr>
                <tr><td style='padding:4px'>camera</td><td>content</td><td>镜头建议</td></tr>
                </table>
                <h3>设计亮点</h3>
                <ul>
                <li><b>全局角色表 + ID 引用</b>：角色定义一次，场景中通过 ID 引用</li>
                <li><b>固定三幕制</b>：Setup / Confrontation / Resolution</li>
                <li><b>扁平化 elements 列表</b>：对话、动作、旁白交替出现</li>
                <li><b>可扩展</b>：以 <code>x_</code> 前缀添加自定义字段</li>
                </ul>
                </div>""")

            # ═══ Tab 3: 使用说明 ═══
            with gr.Tab("使用说明"):
                gr.HTML("""
                <div style='padding:16px;line-height:1.8;font-size:14px'>
                <h2>快速开始</h2>
                <ol>
                <li>粘贴小说文本（至少 3 章）或上传文件（支持 .txt / .docx / .pdf）</li>
                <li>填写 API Key（讯飞 MaaS Coding 推荐）</li>
                <li>选择模型和剧本风格</li>
                <li>点击「<b>开始转换</b>」</li>
                <li>在「YAML 源码」或「可视化预览」标签页查看结果</li>
                <li>导出为 YAML / TXT / Fountain / JSON 格式</li>
                </ol>
                <h3>AI 配置说明</h3>
                <table style='width:100%;border-collapse:collapse'>
                <tr style='background:#f1f5f9'><th style='padding:6px'>提供商</th><th>说明</th><th>推荐模型</th></tr>
                <tr><td style='padding:4px'>讯飞 MaaS Coding</td><td>需自行获取 API Key</td><td>xsparkx2flash</td></tr>
                <tr><td style='padding:4px'>OpenAI</td><td>效果最佳，需 API Key</td><td>gpt-4o-mini</td></tr>
                <tr><td style='padding:4px'>Ollama</td><td>本地运行，免费</td><td>qwen2.5</td></tr>
                <tr><td style='padding:4px'>Gemini</td><td>Google 多模态模型</td><td>gemini-1.5-flash</td></tr>
                </table>
                <h3>注意事项</h3>
                <ul>
                <li>至少需要 3 个章节</li>
                <li>文本建议 1000 字以上效果更佳</li>
                <li>转换通常需要 2-5 分钟</li>
                <li>Ollama 需本地安装并运行 <code>ollama serve</code></li>
                </ul>
                </div>""")

    return demo


if __name__ == "__main__":
    demo = build_ui()
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False, show_error=True)
