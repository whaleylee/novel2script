"""Export service for multi-format screenplay output."""
import json as json_mod
import io
from typing import Optional


def to_fountain(data: dict) -> str:
    """Convert YAML data to Fountain screenplay format."""
    lines = []
    script = data.get("script", {})
    lines.append(f"Title: {script.get('title', 'UNTITLED')}")
    lines.append(f"Credit: {script.get('author', 'Unknown')}")
    lines.append(f"Source: {script.get('original_source', 'Novel')}")
    lines.append("")

    char_map = {c.get("id", ""): c.get("name", "") for c in data.get("characters", [])}

    for scene in data.get("scenes", []):
        lines.append("")
        location = scene.get("location", "UNKNOWN")
        time_val = scene.get("time", "DAY")
        loc_type = scene.get("location_type", "INT")
        prefix = "INT." if loc_type == "int" else ("EXT." if loc_type == "ext" else "INT./EXT.")
        lines.append(f"{prefix} {location.upper()} - {time_val.upper()}")
        lines.append("")

        for el in scene.get("elements", []):
            etype = el.get("type", "")
            content = el.get("content", "")

            if etype == "dialogue":
                char_id = el.get("character", "")
                char_name = char_map.get(char_id, char_id)
                paren = el.get("parenthetical", "")
                if paren:
                    lines.append(f"({paren})")
                lines.append(char_name.upper())
                lines.append(content)
                lines.append("")
            elif etype == "action":
                lines.append(content)
                lines.append("")
            elif etype == "narrative":
                lines.append(content)
                lines.append("")
            elif etype == "transition":
                lines.append(f"> {content.upper()}")
                lines.append("")
            elif etype == "camera":
                # Fountain doesn't have camera, embed as comment
                lines.append(f"[[{content}]]")
                lines.append("")

    return "\n".join(lines)


def to_json(data: dict) -> str:
    """Convert YAML data to pretty-printed JSON."""
    return json_mod.dumps(data, ensure_ascii=False, indent=2)


def to_text(data: dict) -> str:
    """Convert YAML data to human-readable TXT screenplay."""
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
        role_map = {
            "protagonist": "主角", "antagonist": "反派",
            "supporting": "配角", "minor": "次要", "narrator": "旁白",
        }
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


EXPORT_FORMATS = {
    "yaml": {"mime": "text/yaml", "ext": ".yaml"},
    "txt": {"mime": "text/plain", "ext": ".txt"},
    "fountain": {"mime": "text/plain", "ext": ".fountain"},
    "json": {"mime": "application/json", "ext": ".json"},
}


def export(data: dict, fmt: str) -> str:
    """Export screenplay data in the requested format.

    Args:
        data: Parsed YAML dict
        fmt: One of 'yaml', 'txt', 'fountain', 'json'

    Returns:
        Formatted string output
    """
    import yaml

    if fmt == "yaml":
        return yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False, width=120)
    elif fmt == "fountain":
        return to_fountain(data)
    elif fmt == "json":
        return to_json(data)
    elif fmt == "txt":
        return to_text(data)
    else:
        raise ValueError(f"Unsupported format: {fmt}")
