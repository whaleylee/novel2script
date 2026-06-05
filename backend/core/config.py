"""
Core configuration and constants for Novel2Script.
"""

from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()

# Ollama defaults
OLLAMA_BASE_URL = "http://localhost:11434"

# File size limit (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Minimum chapters required
MIN_CHAPTERS = 3

# Supported file extensions
SUPPORTED_EXTENSIONS = {".txt", ".docx", ".pdf"}

# Chapter detection patterns (order matters — more specific first)
CHAPTER_PATTERNS = [
    # Chinese patterns
    r"^第[一二三四五六七八九十百千零\d]+[章节部篇]",           # 第1章 / 第一章 / 第一部
    r"^第[一二三四五六七八九十]+[章节部篇]\s*.+",             # 第一章 标题
    r"^CHAPTER\s+[IVXLCDM\d]+",                             # CHAPTER 1
    r"^Chapter\s+[IVXLCDM\d]+",                             # Chapter 1
    # English patterns
    r"^\d+\.\s+[A-Z]",                                     # 1. THE BEGINNING
    r"^Episode\s+\d+",                                     # Episode 1
    r"^Act\s+[IVXLCDM\d]+",                                # Act I
]

# Genre options
GENRE_OPTIONS = [
    ("drama", "剧情"),
    ("thriller", "悬疑"),
    ("sci_fi", "科幻"),
    ("fantasy", "奇幻"),
    ("romance", "爱情"),
    ("comedy", "喜剧"),
    ("horror", "恐怖"),
    ("action", "动作"),
    ("historical", "历史"),
    ("other", "其他"),
]

# Role options
ROLE_OPTIONS = [
    ("protagonist", "主角"),
    ("antagonist", "反派"),
    ("supporting", "配角"),
    ("minor", "次要角色"),
    ("narrator", "旁白"),
]

# Relationship types
RELATIONSHIP_TYPES = [
    "mentor",
    "family",
    "friend",
    "enemy",
    "romantic",
    "partner",
]

# Element types
ELEMENT_TYPES = ["dialogue", "action", "narrative", "transition", "camera"]

# Location types
LOCATION_TYPES = ["ext", "int", "mixed"]

# ── Xfyun (讯飞 MaaS Coding API) ─────────────────────────────────
import os
XF_API_KEY = os.environ.get("XF_API_KEY", "")
XF_BASE_URL = "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2"

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
