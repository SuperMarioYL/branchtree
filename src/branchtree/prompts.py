"""Jinja2 prompt templates for the m2 LLM loop.

These templates are referenced by :mod:`branchtree.llm` when m2 lands.
Keeping them here — rather than inline strings — means the prompt
contract is visible in one place and easy to tune without touching
adapter code.
"""
from __future__ import annotations

from jinja2 import Environment, Template

_env = Environment(autoescape=False, keep_trailing_newline=True)

REGENERATE_PROMPT = _env.from_string("""\
你是一名网文连载续写引擎。请基于以下已锁定的人物事实重写当前支线tip。

【不可变锁定（lock）】
{% for lock in locks %}
- {{ lock.kind }}:{{ lock.target }} — {{ lock.pinned_facts | join("；") }}
{% endfor %}

【上下文：本支线已有章节】
{% for node in branch_nodes %}
[{{ node.id }}] {{ node.text }}
{% endfor %}

【作者指令】
{{ user_prompt }}

请输出重写后的章节正文，不得违反任何锁定事实。只输出正文，不要解释。""")

EXTRACT_STATE_PROMPT = _env.from_string("""\
请从以下章节文本中抽取叙事状态，输出 JSON：
{ "characters": [...], "summary": "...", "foreshadows": [...] }

章节文本：
{{ chapter_text }}""")


def render_regen_prompt(
    locks: list,
    branch_nodes: list,
    user_prompt: str,
) -> str:
    return REGENERATE_PROMPT.render(
        locks=locks,
        branch_nodes=branch_nodes,
        user_prompt=user_prompt,
    )


def render_extract_prompt(chapter_text: str) -> str:
    return EXTRACT_STATE_PROMPT.render(chapter_text=chapter_text)
