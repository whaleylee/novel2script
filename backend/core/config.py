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

# ── Script Style Presets ───────────────────────────────────────────

STYLE_PRESETS = {
    "cinematic": {
        "name": "电影化",
        "description": "强镜头语言，强调画面感，适合拍电影",
        "prompt_suffix": (
            "\n\n【风格约束】\n"
            "1. 多用 camera 类型元素描述镜头运动（推、拉、摇、跟）\n"
            "2. action 描述要具体到肢体动作和表情\n"
            "3. 对话精简有力，旁白点到为止\n"
            "4. 注重空间感和视觉节奏\n"
        ),
    },
    "theatrical": {
        "name": "舞台戏剧",
        "description": "偏舞台剧风格，对话密集，动作描写少",
        "prompt_suffix": (
            "\n\n【风格约束】\n"
            "1. 以 dialogue 为主，减少 camera 和 action\n"
            "2. 场景描述简洁，聚焦人物\n"
            "3. 旁白使用舞台指示风格（*此处有灯光变化*）\n"
            "4. 适合室内剧或情感密集场景\n"
        ),
    },
    "practical": {
        "name": "可拍摄剧本",
        "description": "注重可操作性，台词口语化，适合低成本制作",
        "prompt_suffix": (
            "\n\n【风格约束】\n"
            "1. location 以实景为主，避免复杂特效\n"
            "2. 对话口语化、生活化\n"
            "3. 减少 camera，多写可执行的 action\n"
            "4. 控制每场角色数量，便于实际拍摄\n"
        ),
    },
    "literary": {
        "name": "文学剧本",
        "description": "保留文学性，旁白丰富，适合艺术片",
        "prompt_suffix": (
            "\n\n【风格约束】\n"
            "1. narrative 元素丰富，保留小说的诗意\n"
            "2. dialogue 可以更文学化，不追求口语\n"
            "3. 场景转换可以更自由，不受时空限制\n"
            "4. 保留小说的意象和隐喻\n"
        ),
    },
    "teleplay": {
        "name": "电视剧节奏",
        "description": "场景短，冲突频繁，适合分集剧本",
        "prompt_suffix": (
            "\n\n【风格约束】\n"
            "1. 场景拆分更细，每场控制在2-3分钟\n"
            "2. 每场结尾留悬念或钩子\n"
            "3. 节奏快，对话简洁\n"
            "4. 适合25-45分钟/集的剧集\n"
        ),
    },
}
import os
XF_API_KEY = os.environ.get("XF_API_KEY", "")
XF_BASE_URL = os.environ.get("XF_BASE_URL", "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2")

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
