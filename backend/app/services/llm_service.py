import json
from openai import OpenAI

from app.core.config import settings


def get_client():
    return OpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com/v1",
    )


def auto_map_fields(fields_data: list[dict], directories_data: list[dict]) -> list[dict]:
    """
    Use DeepSeek to automatically map fields to directories.
    Returns a list of suggested mappings: [{field_id, directory_id, confidence, reason}]
    """
    if not fields_data or not directories_data:
        return []

    dir_tree_text = _format_directories(directories_data)
    fields_text = _format_fields(fields_data)

    prompt = f"""你是一个数据资产管理专家。请分析以下数据字段和资产目录结构，为每个字段推荐最合适的目录映射。

## 资产目录结构
{dir_tree_text}

## 待映射字段列表
{fields_text}

## 任务要求
- 基于字段的 name（名称）、data_type（类型）、table_name（表名）、business_domain（业务域）、description（描述），匹配最合适的目录节点
- 一个字段可以映射到多个目录
- 给出置信度（0.0-1.0）和推荐理由
- 仅返回 JSON 数组，不要其他文字

返回格式：
[
  {{"field_id": 1, "directory_id": 2, "confidence": 0.95, "reason": "字段是客户名称，属于客户域目录"}},
  ...
]"""

    client = get_client()
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a data management expert. Always respond with valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=4096,
    )

    content = response.choices[0].message.content.strip()
    # Clean up markdown code blocks if present
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

    try:
        suggestions = json.loads(content)
        return suggestions
    except json.JSONDecodeError:
        return []


def _format_directories(dirs: list[dict]) -> str:
    lines = []
    for d in dirs:
        indent = "  " * d.get("level", 0)
        tags = f" [标签: {d.get('tags', '')}]" if d.get("tags") else ""
        lines.append(f"{indent}- ID={d['id']} | {d['name']} ({d.get('code', '')}){tags}")
        if d.get("description"):
            lines.append(f"{indent}  描述: {d['description']}")
    return "\n".join(lines)


def _format_fields(fields: list[dict]) -> str:
    lines = []
    for f in fields:
        parts = [
            f"ID={f['id']}",
            f"name={f.get('name', '')}",
            f"data_type={f.get('data_type', '')}",
            f"table={f.get('table_name', '')}",
        ]
        if f.get("business_domain"):
            parts.append(f"domain={f['business_domain']}")
        if f.get("description"):
            parts.append(f"desc={f['description']}")
        lines.append(" | ".join(parts))
    return "\n".join(lines)
