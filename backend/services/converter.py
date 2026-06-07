"""
Conversion engine — orchestrates the novel → screenplay YAML pipeline.
"""

import re
import json
import yaml
from datetime import date
from typing import AsyncIterator, Optional

from backend.core.models import AIConfig, ConvertOptions, ConvertRequest
from backend.services.llm_service import llm_service
from backend.services.file_parser import detect_chapters, analyze_text


SYSTEM_PROMPT = """你是一位专业的剧本改编师，负责将小说文本改编为结构化剧本 YAML。
严格遵循以下 YAML Schema（YAML 格式，非 JSON）：

根对象包含5个键：script, metadata, characters, act_structure, scenes

script:
  title: "..."        # 必填，故事标题
  author: "..."       # 必填，原作者
  genre: "..."       # 必填，类型：drama/thriller/sci_fi/fantasy/romance/comedy/horror/action/historical/other
  logline: "..."     # 必填，一句话故事（≤200字符）
  original_source: "小说"  # 可填

metadata:
  total_scenes: N     # 必填，场景总数（估算）
  total_characters: N # 必填，角色总数
  total_acts: 3       # 必填，固定为3
  estimated_duration: "X分钟"  # 必填，估算时长
  generated_by: "..." # AI模型名称
  generated_at: "YYYY-MM-DD"  # 必填，日期

characters:           # 必填，角色列表
  - id: "char_001"    # 格式 char_NNN
    name: "姓名"
    role: "protagonist|antagonist|supporting|minor|narrator"
    description: "角色描述（≥10字符）"
    voice: "语音特征"  # 可填
    first_appearance: N  # 首次出现的场景编号
    relationships:    # 可填
      - target: "char_XXX"
        type: "mentor|family|friend|enemy|romantic|partner"
        description: "关系描述"

act_structure:         # 必填，固定3个act
  - act: 1
    title: "第一幕：标题"
    description: "幕描述"  # 可填
    scenes: [场景编号列表]
  - act: 2
    title: "第二幕：标题"
    scenes: [...]
  - act: 3
    title: "第三幕：标题"
    scenes: [...]

scenes:                # 必填，场景列表
  - id: N              # 从1开始的连续编号
    act: N              # 所属幕号
    location: "场景地点"
    time: "白天/夜晚/黄昏..."
    location_type: "ext|int|mixed"
    weather: "天气"     # 可填
    characters: ["char_XXX"]  # 出现此场景的角色ID列表
    summary: "场景概述"
    elements:           # 场景元素列表
      - type: "dialogue|action|narrative|transition|camera"
        character: "char_XXX"  # 仅 dialogue 需要
        content: "内容"
        parenthetical: "语气提示"  # 仅 dialogue 可填

重要规则：
1. 输出必须是完整、合法、可直接解析的 YAML 文本，不要有任何解释文字
2. characters 中的 id 必须在全剧中唯一且一致
3. scenes 中的 id 从1开始连续编号，act_structure 中的 scenes 列表必须与之对应
4. dialogue 的 character 必须是 characters 中已定义的角色 ID
5. 场景数量建议：每章 2-5 个场景，总场景数 = 章节数 × 3 左右
6. 三幕比例建议：第一幕 20%，第二幕 50%，第三幕 30%
7. 适当加入 camera 镜头建议，增强画面感
8. 用中文输出所有内容（角色名、台词、描述等）
"""


def build_chapter_prompt(chapter_title: str, chapter_text: str, options: ConvertOptions, all_known_chars: list[dict] = None) -> list[dict]:
    """Build messages for a single chapter conversion."""
    char_context = ""
    if all_known_chars:
        char_context = "\n已发现的角色：\n" + "\n".join(
            f"- {c['name']}（{c['id']}）: {c['description'][:30]}"
            for c in all_known_chars[:10]
        )

    user_content = f"## 章节：{chapter_title}\n\n{chapter_text[:8000]}{char_context}\n\n请将以上章节改编为剧本 YAML 的场景定义。只输出 YAML 代码，不要解释。"

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def build_summary_prompt(chapters_data: list[dict], options: ConvertOptions) -> list[dict]:
    """Build messages for global analysis (characters + act structure)."""
    chapters_summary = "\n\n".join(
        f"=== {ch['title']} ===\n{ch['summary']}"
        for ch in chapters_data
    )

    user_content = f"""## 小说各章摘要

{chapters_summary}

请对以上章节摘要进行全局分析，输出完整的 YAML（script + metadata + characters + act_structure 部分，scenes 部分填入各章摘要）。

要求：
1. 从章节摘要中提取所有角色，构建 characters 列表
2. 分析三幕结构比例（1:2:1 黄金比例），确定各幕包含的章节
3. 估算总场景数（建议每章 3 个场景）
4. 只输出 YAML，不要解释
"""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def parse_yaml_chunk(raw: str) -> dict:
    """Parse YAML from LLM output, stripping markdown fences."""
    text = raw.strip()
    text = re.sub(r"^```yaml\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return yaml.safe_load(text)


def yaml_to_string(data: dict) -> str:
    """Serialize dict to nicely formatted YAML string."""
    return yaml.dump(
        data,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=120,
    )


async def convert_novel(
    request: ConvertRequest,
) -> AsyncIterator[str]:
    """
    Main conversion pipeline:
    1. Parse text into chapters
    2. Global analysis → characters + act structure
    3. Per-chapter analysis → scenes
    4. Merge and yield final YAML
    """
    text = request.text.strip()
    options = request.options
    config = request.config

    # Step 1: Detect chapters
    chapters = detect_chapters(text)
    chapter_count = len(chapters)

    yield f"检测到 {chapter_count} 个章节\n"
    if chapter_count < 3:
        raise ValueError(f"章节数不足：检测到 {chapter_count} 个章节，需要至少 3 个章节")

    # Step 2: Quick text analysis
    analysis = analyze_text(text)
    yield f"字数：{analysis['word_count']:,} 字，潜在角色：{len(analysis['potential_characters'])} 个\n"

    # Step 3: Global analysis
    yield "正在分析全局结构（角色、幕结构）...\n"

    # First pass: summarize each chapter
    chapter_summaries = []
    for i, (title, content) in enumerate(chapters):
        yield f"正在摘要章节 {i + 1}/{chapter_count}: {title}\n"
        messages = build_chapter_prompt(title, content[:3000], options)
        try:
            summary_text = await llm_service.achat(messages, config)
            # Try to extract just the YAML summary
            if "---" in summary_text or "scenes:" in summary_text.lower() or "yaml" in summary_text.lower():
                try:
                    parsed = parse_yaml_chunk(summary_text)
                    if parsed and isinstance(parsed, dict):
                        summary_text = parsed.get("scenes", [{}])[0].get("summary", summary_text[:200]) if parsed.get("scenes") else summary_text[:200]
                except Exception:
                    pass
        except Exception as e:
            summary_text = content[:300]
        chapter_summaries.append({"title": title, "summary": summary_text[:500]})

    # Step 4: Global analysis for characters + act structure
    yield "正在构建角色图谱和幕结构...\n"
    global_messages = build_summary_prompt(chapter_summaries, options)
    try:
        global_yaml_raw = await llm_service.achat(global_messages, config)
        global_data = parse_yaml_chunk(global_yaml_raw)
    except Exception as e:
        global_data = {
            "script": {
                "title": request.title or "未命名剧本",
                "author": request.author or "未知作者",
                "genre": "drama",
                "logline": "故事改编中...",
            },
            "metadata": {
                "total_scenes": chapter_count * 3,
                "total_characters": 3,
                "total_acts": 3,
                "estimated_duration": f"{chapter_count * 15}分钟",
                "generated_by": config.model,
                "generated_at": str(date.today()),
            },
            "characters": [],
            "act_structure": [],
            "scenes": [],
        }

    # Step 5: Per-chapter scene generation
    yield "正在逐章生成场景...\n"
    all_scenes = []
    character_map = {c["id"]: c for c in (global_data or {}).get("characters", [])}

    for i, (title, content) in enumerate(chapters):
        yield f"正在生成第 {i + 1}/{chapter_count} 章的场景...\n"
        messages = build_chapter_prompt(title, content, options, list(character_map.values()))
        try:
            chapter_yaml_raw = await llm_service.achat(messages, config)
            chapter_data = parse_yaml_chunk(chapter_yaml_raw)
            if chapter_data and isinstance(chapter_data, dict):
                scenes = chapter_data.get("scenes", [])
                for scene in scenes:
                    scene["id"] = len(all_scenes) + 1
                    # Determine act by position
                    scene_count = max(1, chapter_count * 3)
                    act_idx = int((len(all_scenes) / scene_count) * 3) + 1
                    scene["act"] = min(act_idx, 3)
                    all_scenes.append(scene)
                if len(all_scenes) > 100:
                    break

                # Accumulate new characters
                for char in chapter_data.get("characters", []):
                    if char.get("id") and char["id"] not in character_map:
                        character_map[char["id"]] = char
        except Exception as e:
            # Create a basic scene for this chapter on error
            all_scenes.append({
                "id": len(all_scenes) + 1,
                "act": min((i // max(1, chapter_count // 3)) + 1, 3),
                "location": "场景",
                "time": "时间",
                "location_type": "int",
                "characters": [],
                "summary": title,
                "elements": [
                    {"type": "transition", "content": "淡入"},
                    {"type": "narrative", "content": f"场景：{title}"},
                    {"type": "transition", "content": "淡出"},
                ],
            })

    # Step 6: Build final YAML
    characters_list = list(character_map.values())
    total_scenes = len(all_scenes) or (chapter_count * 3)

    # Recompute act structure
    act1_scenes = [s["id"] for s in all_scenes if s.get("act") == 1]
    act2_scenes = [s["id"] for s in all_scenes if s.get("act") == 2]
    act3_scenes = [s["id"] for s in all_scenes if s.get("act") == 3]

    # Fallback: distribute evenly
    if not act2_scenes and not act3_scenes:
        per_act = max(1, total_scenes // 3)
        act1_scenes = list(range(1, per_act + 1))
        act2_scenes = list(range(per_act + 1, per_act * 2 + 1))
        act3_scenes = list(range(per_act * 2 + 1, total_scenes + 1))

    act_structure = [
        {
            "act": 1,
            "title": "第一幕：起因",
            "description": "建立世界，引入冲突",
            "scenes": act1_scenes,
        },
        {
            "act": 2,
            "title": "第二幕：对抗",
            "description": "冲突升级，挫折阻碍",
            "scenes": act2_scenes,
        },
        {
            "act": 3,
            "title": "第三幕：解决",
            "description": "高潮对决，结局收束",
            "scenes": act3_scenes,
        },
    ]

    # Build script metadata
    if "script" not in global_data or not global_data["script"].get("title"):
        global_data.setdefault("script", {})["title"] = request.title or "小说改编剧本"
    if "script" not in global_data or not global_data["script"].get("author"):
        global_data.setdefault("script", {})["author"] = request.author or "未知"

    final_data = {
        "script": global_data.get("script", {
            "title": request.title or "小说改编剧本",
            "author": request.author or "未知",
            "genre": "drama",
            "logline": "故事改编中...",
        }),
        "metadata": {
            "total_scenes": total_scenes,
            "total_characters": len(characters_list),
            "total_acts": 3,
            "estimated_duration": f"{min(total_scenes * 2, 120)}分钟",
            "word_count": analysis["word_count"],
            "generated_by": config.model,
            "generated_at": str(date.today()),
            "version": "1.0",
        },
        "characters": characters_list[:20],  # Cap at 20
        "act_structure": act_structure,
        "scenes": all_scenes[:100],  # Cap at 100 scenes
    }

    yield "\n生成完成！正在格式化输出...\n"

    final_yaml = yaml_to_string(final_data)
    yield "---YAML_OUTPUT_START---\n"
    for line in final_yaml.split("\n"):
        yield line + "\n"
    yield "---YAML_OUTPUT_END---\n"
    yield f"\n剧本生成完成！共 {total_scenes} 个场景，{len(characters_list)} 个角色。\n"


def yaml_to_screenplay(yaml_text: str) -> str:
    """Convert YAML to human-readable screenplay TXT format."""
    try:
        data = yaml.safe_load(yaml_text)
    except Exception:
        return yaml_text

    lines = []
    script = data.get("script", {})
    lines.append("=" * 60)
    lines.append(f"标题：{script.get('title', '未命名')}")
    lines.append(f"作者：{script.get('author', '未知')}")
    lines.append(f"类型：{script.get('genre', '剧情')}")
    lines.append(f"一句话简介：{script.get('logline', '')}")
    lines.append("=" * 60)
    lines.append("")

    # Characters
    lines.append("【角色表】")
    for char in data.get("characters", []):
        lines.append(f"  {char.get('name', char.get('id'))}（{char.get('role', '')}）")
    lines.append("")

    # Scenes
    for scene in data.get("scenes", []):
        lines.append("")
        lines.append(f"--- 场景 {scene.get('id', '?')} ---")
        lines.append(f"[{'内' if scene.get('location_type') == 'int' else '外'}景] {scene.get('location', '')} - {scene.get('time', '')}")
        if scene.get("weather"):
            lines.append(f"天气：{scene.get('weather')}")
        lines.append(f"出场：{', '.join(c for c in scene.get('characters', []))}")
        lines.append(f"概要：{scene.get('summary', '')}")
        lines.append("")

        for elem in scene.get("elements", []):
            elem_type = elem.get("type", "")
            content = elem.get("content", "")

            if elem_type == "transition":
                lines.append(f"\n>> {content}")
            elif elem_type == "dialogue":
                char_id = elem.get("character", "")
                paren = elem.get("parenthetical", "")
                char_name = char_id
                # Try to resolve char name
                for c in data.get("characters", []):
                    if c.get("id") == char_id:
                        char_name = c.get("name", char_id)
                        break
                prefix = f"（{paren}）" if paren else ""
                lines.append(f"  {char_name}{prefix}")
                lines.append(f"    {content}")
            elif elem_type == "camera":
                lines.append(f"  [镜头] {content}")
            elif elem_type == "narrative":
                lines.append(f"  （旁白）{content}")
            elif elem_type == "action":
                lines.append(f"  （动作）{content}")

    return "\n".join(lines)
