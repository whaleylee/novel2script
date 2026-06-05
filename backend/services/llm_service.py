"""
LLM service — unified AI interface via LiteLLM.
"""

import os
import json
import httpx
from typing import AsyncIterator, Optional

import litellm
from litellm import acompletion, completion

from backend.core.models import AIConfig
from backend.core.config import OLLAMA_BASE_URL


class LLMService:
    """Unified LLM service supporting OpenAI, Ollama, Gemini via LiteLLM."""

    def __init__(self):
        litellm.drop_params = True
        litellm.set_verbose = False

    def _build_kwargs(self, config: AIConfig) -> dict:
        """Build litellm compatible kwargs from AIConfig."""
        kwargs = {
            "model": self._resolve_model(config),
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "stream": False,
        }
        if config.api_key:
            kwargs["api_key"] = config.api_key
        if config.base_url:
            kwargs["base_url"] = config.base_url
        return kwargs

    def _resolve_model(self, config: AIConfig) -> str:
        """Resolve model string for different providers."""
        if config.provider == "openai":
            return config.model if config.model.startswith("gpt") else f"openai/{config.model}"
        elif config.provider == "ollama":
            return f"ollama/{config.model}"
        elif config.provider == "gemini":
            return f"gemini/{config.model}"
        return config.model

    async def achat(self, messages: list[dict], config: AIConfig) -> str:
        """Async single-shot chat completion."""
        kwargs = self._build_kwargs(config)
        kwargs["messages"] = messages
        response = await acompletion(**kwargs)
        return response.choices[0].message.content

    async def astream(
        self, messages: list[dict], config: AIConfig
    ) -> AsyncIterator[str]:
        """Async streaming chat completion yielding text chunks."""
        kwargs = self._build_kwargs(config)
        kwargs["messages"] = messages
        kwargs["stream"] = True
        response = await acompletion(**kwargs)
        async for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    def chat(self, messages: list[dict], config: AIConfig) -> str:
        """Sync single-shot chat completion."""
        kwargs = self._build_kwargs(config)
        kwargs["messages"] = messages
        response = completion(**kwargs)
        return response.choices[0].message.content


# Global instance
llm_service = LLMService()


async def check_ollama_connection(base_url: str = OLLAMA_BASE_URL) -> bool:
    """Check if Ollama is running."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base_url}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False


async def check_openai_connection(api_key: str) -> bool:
    """Check if OpenAI API key is valid."""
    try:
        litellm.openai_chat_completions._check_valid_key(api_key)
        return True
    except Exception:
        return False


async def list_ollama_models(base_url: str = OLLAMA_BASE_URL) -> list[dict]:
    """List available Ollama models."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base_url}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                return data.get("models", [])
            return []
    except Exception:
        return []
