"""Static HTML tree-view renderer.

Renders a :class:`StoryTree` to a single self-contained HTML file and
opens it in the user's default browser via :mod:`webbrowser`.  No server
process — the file is static and works from ``file://``.
"""
from __future__ import annotations

import webbrowser
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .tree import StoryTree

# The template is embedded as a string so the rendered HTML is a single
# self-contained file with no external CSS/JS dependencies.
_TEMPLATE = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ tree.name }} — BranchTree</title>
<style>
  :root { color-scheme: light dark; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, "PingFang SC", "Segoe UI", sans-serif;
    background: #f5f5f7; color: #1d1d1f; line-height: 1.6; padding: 24px;
  }
  h1 { font-size: 1.6rem; margin-bottom: 4px; }
  .sub { color: #6e6e73; font-size: 0.9rem; margin-bottom: 24px; }
  h2 { font-size: 1.1rem; margin: 24px 0 12px; border-bottom: 1px solid #c9c9d0; padding-bottom: 6px; }
  .locks { display: flex; flex-wrap: wrap; gap: 8px; }
  .lock {
    background: #fff; border: 1px solid #c9c9d0; border-radius: 10px;
    padding: 10px 14px; font-size: 0.85rem; min-width: 200px;
  }
  .lock .kind { color: #5e5ce6; font-weight: 600; text-transform: uppercase; font-size: 0.7rem; letter-spacing: 0.5px; }
  .lock .target { font-weight: 600; margin: 2px 0; }
  .lock .facts { color: #6e6e73; font-size: 0.8rem; }
  .tree-branch { margin-bottom: 20px; }
  .branch-header {
    display: flex; align-items: center; gap: 8px; font-weight: 600;
    font-size: 0.95rem; margin-bottom: 8px;
  }
  .branch-tag {
    font-size: 0.7rem; padding: 2px 8px; border-radius: 6px;
    background: #0071e3; color: #fff; font-weight: 500;
  }
  .branch-tag.alt { background: #5e5ce6; }
  .chapter {
    background: #fff; border: 1px solid #e0e0e5; border-radius: 12px;
    padding: 14px 18px; margin-bottom: 8px; position: relative;
  }
  .chapter .ch-id { color: #0071e3; font-weight: 600; font-size: 0.8rem; }
  .chapter .ch-text { margin-top: 6px; font-size: 0.9rem; color: #1d1d1f; white-space: pre-wrap; }
  .chapter .ch-state { margin-top: 6px; font-size: 0.75rem; color: #6e6e73; }
  .fork-marker {
    color: #5e5ce6; font-size: 0.75rem; font-weight: 600;
    margin: 4px 0 4px 20px;
  }
  .conn { color: #c9c9d0; margin-left: 20px; font-size: 0.75rem; }
  summary { cursor: pointer; color: #0071e3; font-size: 0.8rem; }
  @media (prefers-color-scheme: dark) {
    body { background: #1d1d1f; color: #f5f5f7; }
    .lock, .chapter { background: #2a2a2e; border-color: #3a3a44; }
    h2 { border-color: #3a3a44; }
    .chapter .ch-text { color: #f5f5f7; }
    .conn { color: #3a3a44; }
  }
</style>
</head>
<body>
  <h1>{{ tree.name }}</h1>
  <p class="sub">BranchTree 故事树 — {{ tree.nodes | length }} 章 · {{ tree.branches | length }} 分支 · {{ tree.locks | length }} 锁</p>

  {% if tree.locks %}
  <h2>锁定 (Locks)</h2>
  <div class="locks">
    {% for lock in tree.locks %}
    <div class="lock">
      <div class="kind">{{ lock.kind }} · {{ lock.scope }}</div>
      <div class="target">{{ lock.target }}</div>
      <div class="facts">{{ lock.pinned_facts | join("；") }}</div>
    </div>
    {% endfor %}
  </div>
  {% endif %}

  <h2>故事树</h2>
  {% for bname, branch in tree.branches.items() %}
  <div class="tree-branch">
    <div class="branch-header">
      <span class="branch-tag {{ 'alt' if bname != 'main' else '' }}">{{ bname }}</span>
      <span class="sub" style="font-size:0.8rem;">fork: {{ branch.fork_point }} → tip: {{ branch.active_tip }}</span>
    </div>
    {% set path = branch_path(tree, bname) %}
    {% for nid in path %}
      {% set node = tree.nodes[nid] %}
      {% if loop.first and bname != 'main' %}
      <div class="fork-marker">↳ 从 {{ branch.fork_point }} 分叉</div>
      {% endif %}
      <div class="chapter">
        <span class="ch-id">{{ node.id }}</span>
        <div class="ch-text">{{ node.text }}</div>
        {% if node.extracted_state.characters %}
        <div class="ch-state">出场：{{ node.extracted_state.characters | join("、") }} · {{ node.extracted_state.word_count }} 字</div>
        {% else %}
        <div class="ch-state">{{ node.extracted_state.word_count }} 字</div>
        {% endif %}
      </div>
      {% if not loop.last %}
      <div class="conn">│</div>
      {% endif %}
    {% endfor %}
  </div>
  {% endfor %}

  {% set children = orphan_branches(tree) %}
  {% if children %}
  <h2>分叉节点</h2>
  <details>
    <summary>查看分叉点下的所有子节点</summary>
    {% for nid, kids in children.items() %}
    <p class="sub">{{ nid }} → {{ kids | join(", ") }}</p>
    {% endfor %}
  </details>
  {% endif %}
</body>
</html>"""


def _branch_path(tree: StoryTree, branch_name: str) -> list[str]:
    """Jinja helper: return the path for a branch."""
    try:
        return tree.branch_path(branch_name)
    except ValueError:
        return []


def _orphan_branches(tree: StoryTree) -> dict[str, list[str]]:
    """Jinja helper: nodes with more than one child (fork points)."""
    result: dict[str, list[str]] = {}
    for nid in tree.nodes:
        kids = tree.children_of(nid)
        if len(kids) > 1:
            result[nid] = kids
    return result


def render_html(tree: StoryTree) -> str:
    """Render *tree* to a self-contained HTML string."""
    env = Environment(autoescape=select_autoescape(["html"]), loader=FileSystemLoader([]))
    env.globals["branch_path"] = _branch_path
    env.globals["orphan_branches"] = _orphan_branches
    template = env.from_string(_TEMPLATE)
    return template.render(tree=tree)


def render_to_file(
    tree: StoryTree,
    output: str | Path | None = None,
    open_browser: bool = True,
) -> Path:
    """Render *tree* to an HTML file and optionally open it."""
    if output is None:
        tree_dir = Path(f"{tree.name}.tree")
        output = tree_dir / "tree.html" if tree_dir.exists() else Path("tree.html")
    else:
        output = Path(output)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_html(tree), encoding="utf-8")

    if open_browser:
        webbrowser.open(output.resolve().as_uri())

    return output
