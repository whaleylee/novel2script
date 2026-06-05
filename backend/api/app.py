"""
FastAPI application entry point.
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import Optional
import asyncio

from backend.core.models import (
    ConvertRequest,
    ConvertOptions,
    AIConfig,
    HealthResponse,
    OllamaModelsResponse,
)
from backend.services.llm_service import (
    check_ollama_connection,
    list_ollama_models,
)
from backend.services.file_parser import extract_text
from backend.services.converter import convert_novel, yaml_to_screenplay

app = FastAPI(
    title="Novel2Script API",
    description="AI-powered novel to screenplay YAML converter",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    ollama = await check_ollama_connection()
    return HealthResponse(
        status="ok",
        ollama_connected=ollama,
        openai_connected=False,  # Don't auto-check, only on convert
    )


@app.get("/ollama/models", response_model=OllamaModelsResponse)
async def get_ollama_models():
    """List available Ollama models."""
    connected = await check_ollama_connection()
    if not connected:
        return OllamaModelsResponse(models=[], connected=False)
    models = await list_ollama_models()
    return OllamaModelsResponse(
        models=[{"name": m.get("name", ""), "size": m.get("size", 0)} for m in models],
        connected=True,
    )


@app.post("/convert")
async def convert_endpoint(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    provider: str = Form("openai"),
    api_key: Optional[str] = Form(None),
    model: str = Form("gpt-4o-mini"),
    base_url: Optional[str] = Form(None),
    temperature: float = Form(0.7),
    max_tokens: int = Form(8192),
    title: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    add_camera_directions: bool = Form(True),
    add_transitions: bool = Form(True),
    preserve_narrative: bool = Form(True),
):
    """Convert novel text to screenplay YAML."""
    # Resolve input text
    if file:
        content = await file.read()
        try:
            raw_text = extract_text(file.filename, content)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    elif text:
        raw_text = text.strip()
    else:
        raise HTTPException(status_code=400, detail="必须提供 text 或 file 参数")

    if len(raw_text) < 500:
        raise HTTPException(status_code=400, detail="文本内容过短，至少需要 500 字符")

    config = AIConfig(
        provider=provider,
        api_key=api_key,
        model=model,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    options = ConvertOptions(
        add_camera_directions=add_camera_directions,
        add_transitions=add_transitions,
        preserve_narrative=preserve_narrative,
    )
    request = ConvertRequest(
        text=raw_text,
        config=config,
        options=options,
        title=title,
        author=author,
    )

    async def generate():
        try:
            async for chunk in convert_novel(request):
                yield f"data: {chunk}\n\n"
                await asyncio.sleep(0.01)
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/convert/plain")
async def convert_plain(request: ConvertRequest):
    """Convert novel text to screenplay YAML (plain JSON response)."""
    from backend.services.file_parser import detect_chapters

    chapters = detect_chapters(request.text)
    if len(chapters) < 3:
        raise HTTPException(
            status_code=400,
            detail=f"章节数不足：检测到 {len(chapters)} 个章节，需要至少 3 个章节",
        )

    full_yaml = ""
    in_yaml = False
    async for chunk in convert_novel(request):
        if "---YAML_OUTPUT_START---" in chunk:
            in_yaml = True
            chunk = chunk.replace("---YAML_OUTPUT_START---", "").strip()
            continue
        if "---YAML_OUTPUT_END---" in chunk:
            break
        if in_yaml and chunk.strip():
            full_yaml += chunk + "\n"

    return {"yaml": full_yaml.strip()}


@app.post("/export/screenplay")
async def export_screenplay(yaml_text: str):
    """Convert YAML to human-readable screenplay TXT."""
    result = yaml_to_screenplay(yaml_text)
    return {"screenplay": result}
