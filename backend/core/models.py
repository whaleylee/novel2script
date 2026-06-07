"""
Pydantic models for Novel2Script API request/response schemas.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class AIConfig(BaseModel):
    """AI provider configuration."""
    provider: Literal["openai", "ollama", "gemini", "xfyun"] = "xfyun"
    api_key: Optional[str] = None
    model: str = "gpt-4o-mini"
    base_url: Optional[str] = None  # For Ollama / custom endpoints
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=8192, ge=100, le=128000)


class ConvertOptions(BaseModel):
    """Conversion options."""
    style: Literal["cinematic", "theatrical", "practical", "literary", "teleplay"] = "cinematic"
    add_camera_directions: bool = True
    add_transitions: bool = True
    preserve_narrative: bool = True
    max_scenes_per_chapter: int = 5


class ConvertRequest(BaseModel):
    """Request body for /convert endpoint."""
    text: str = Field(..., min_length=100, description="Novel text content")
    config: AIConfig = Field(default_factory=AIConfig)
    options: ConvertOptions = Field(default_factory=ConvertOptions)
    title: Optional[str] = None
    author: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    ollama_connected: bool = False
    openai_connected: bool = False


class OllamaModel(BaseModel):
    """Ollama model info."""
    name: str
    size: int


class OllamaModelsResponse(BaseModel):
    """Response for /ollama/models endpoint."""
    models: List[OllamaModel]
    connected: bool
