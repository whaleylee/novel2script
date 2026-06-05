"""
File parsing service — TXT, DOCX, PDF text extraction.
"""

import re
from pathlib import Path
from typing import Tuple, List

from backend.core.config import (
    CHAPTER_PATTERNS,
    SUPPORTED_EXTENSIONS,
    MAX_FILE_SIZE,
    MIN_CHAPTERS,
)


def extract_text_from_txt(file_content: bytes) -> str:
    """Extract text from plain text file, handling encoding."""
    encodings = ["utf-8", "gbk", "gb2312", "gb18030", "utf-16"]
    for enc in encodings:
        try:
            return file_content.decode(enc).strip()
        except (UnicodeDecodeError, AttributeError):
            continue
    return file_content.decode("utf-8", errors="replace").strip()


def extract_text_from_docx(file_content: bytes, tmp_path: str) -> str:
    """Extract text from DOCX file."""
    import docx
    from io import BytesIO
    doc = docx.Document(BytesIO(file_content))
    return "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())


def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF file."""
    from PyPDF2 import PdfReader
    from io import BytesIO
    reader = PdfReader(BytesIO(file_content))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages)


def extract_text(file_path: str, file_content: bytes) -> str:
    """Dispatch to appropriate extractor based on file extension."""
    ext = Path(file_path).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")

    if file_content.size > MAX_FILE_SIZE:
        raise ValueError(f"File too large: {file_content.size / 1024 / 1024:.1f}MB > 10MB limit")

    if ext == ".txt":
        return extract_text_from_txt(file_content)
    elif ext == ".docx":
        return extract_text_from_docx(file_content, file_path)
    elif ext == ".pdf":
        return extract_text_from_pdf(file_content)
    raise ValueError(f"Unsupported extension: {ext}")


def detect_chapters(text: str) -> List[Tuple[str, str]]:
    """
    Detect chapter boundaries in novel text.

    Returns list of (chapter_title, chapter_content) tuples.
    Falls back to splitting by number of chapters detected.
    """
    chapter_pattern = "|".join(f"({p})" for p in CHAPTER_PATTERNS)
    pattern = re.compile(chapter_pattern, re.MULTILINE | re.IGNORECASE)

    matches = list(pattern.finditer(text))

    if len(matches) < MIN_CHAPTERS:
        return split_by_estimated_chapters(text, MIN_CHAPTERS)

    chapters = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        raw_title = text[start:match.end()].strip()
        title = re.sub(r"\s+", " ", raw_title).strip()
        content = text[start:end].strip()
        chapters.append((title, content))

    return chapters


def split_by_estimated_chapters(text: str, min_chapters: int) -> List[Tuple[str, str]]:
    """Fallback: split text into roughly equal chunks."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return [("第1节", text[: len(text) // 2]), ("第2节", text[len(text) // 2 :])]

    total = len(paragraphs)
    chunk_size = max(1, total // min_chapters)
    chapters = []
    for i in range(min_chapters):
        start = i * chunk_size
        end = (i + 1) * chunk_size if i < min_chapters - 1 else total
        chunk_paras = paragraphs[start:end]
        if chunk_paras:
            chapter_text = "\n\n".join(chunk_paras)
            chapters.append((f"第{i + 1}章", chapter_text))
    return chapters


def analyze_text(text: str) -> dict:
    """Analyze text to produce basic metadata."""
    chapters = detect_chapters(text)
    char_count = len(text)
    word_count = len(text.replace("\n", "").replace(" ", ""))

    # Rough character detection
    potential_chars = set()
    dialogue_pattern = re.compile(r"[\u300e\u300f\u201c\u201d]([^\u300e\u300f\u300e\u300f\n]{1,20})[\u300e\u300f\u201c\u201d]", re.UNICODE)
    for match in dialogue_pattern.finditer(text):
        speaker = match.group(1).strip()
        if 2 <= len(speaker) <= 10 and not any(c.isdigit() for c in speaker):
            potential_chars.add(speaker)

    return {
        "char_count": char_count,
        "word_count": word_count,
        "chapter_count": len(chapters),
        "potential_characters": list(potential_chars)[:20],
        "preview": text[:500],
    }
