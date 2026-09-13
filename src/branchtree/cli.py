"""BranchTree CLI — the single entry point.

Commands
--------
new        Create an empty story tree.
add        Append a chapter (from --file or --text).
branch     Fork a new branch from an existing node.
merge      Promote a branch's take back into the main line.
lock       Manage locks (add / list).
view       Render the tree to a static HTML page and open it.
regenerate Rewrite a branch tip via the LLM adapter; outputs that
           violate locked facts are refused.
consistency  Run the cross-chapter consistency checker (exit 1 on findings).
"""
from __future__ import annotations

from pathlib import Path
from typing import NoReturn

import typer
from pydantic import ValidationError
from rich import print as rprint

from . import __version__
from .consistency import check_consistency
from .llm import LLMAdapter
from .render_html import render_to_file
from .tree import (
    TREE_DIR_SUFFIX,
    TREE_FILENAME,
    Lock,
    StoryTree,
)

app = typer.Typer(
    name="branchtree",
    help="把故事当树，不当纸 — 网文连载故事树 agent。",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        rprint(f"branchtree {__version__}")
        raise typer.Exit(0)


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="显示版本号并退出。",
    ),
) -> None:
    """把故事当树，不当纸 — 网文连载故事树 agent。"""


# ---------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------

def _fail(message: str) -> NoReturn:
    """Print one clean red error line and exit 1 (the CLI error contract)."""
    rprint(f"[red]{message}[/red]")
    raise typer.Exit(1)


def _load_tree(base_dir: str = ".") -> StoryTree:
    """Find and load the .tree/ directory in *base_dir* with a clean error contract."""
    tree_dirs = sorted(Path(base_dir).glob(f"*{TREE_DIR_SUFFIX}"))
    if not tree_dirs:
        _fail("未找到故事树。请先运行 `branchtree new <name>`。")
    tree_dir = tree_dirs[0]
    if not (tree_dir / TREE_FILENAME).is_file():
        _fail(f"{tree_dir.name}/ 缺少 {TREE_FILENAME} — 故事树目录不完整。")
    try:
        return StoryTree.load(tree_dir)
    except ValidationError:
        _fail(f"{tree_dir.name}/{TREE_FILENAME} 已损坏（无效 JSON 或字段缺失），无法加载。")


# ---------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------

@app.command()
def new(
    name: str = typer.Argument(..., help="故事树名称"),
    force: bool = typer.Option(False, "--force", help="覆盖已存在的同名故事树"),
) -> None:
    """创建一棵空的故事树。"""
    if not name.strip():
        _fail("故事树名称不能为空。")
    if "/" in name or "\\" in name or Path(name).name != name:
        _fail(f"故事树名称不能包含路径分隔符：{name!r}")
    tree_dir = Path(f"{name}{TREE_DIR_SUFFIX}")
    existing = (tree_dir / TREE_FILENAME).is_file()
    if existing and not force:
        _fail(f"故事树已存在：{tree_dir}/ — 重新创建会清空现有内容，如确需覆盖请加 --force。")
    tree = StoryTree(name=name)
    tree.save()
    if existing and force:
        rprint(f"[yellow]已覆盖既有故事树[/yellow] [bold]{tree_dir}/[/bold]")
    rprint(f"[green]已创建故事树[/green] [bold]{name}[/bold] → {tree_dir}/tree.json")


@app.command()
def add(
    file: Path | None = typer.Option(None, "--file", "-f", help="从文件读取章节文本"),
    text: str | None = typer.Option(None, "--text", "-t", help="直接传入章节文本"),
    branch: str = typer.Option("main", "--branch", "-b", help="追加到指定分支"),
) -> None:
    """追加一个章节节点。"""
    if file is None and text is None:
        _fail("请通过 --file 或 --text 提供章节文本。")

    if file is not None:
        if not file.is_file():
            _fail(f"文件不存在：{file}")
        try:
            content = file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            _fail(f"文件不是 UTF-8 文本：{file}")
    else:
        content = text or ""

    tree = _load_tree()
    try:
        node = tree.add_chapter(content, branch=branch)
    except ValueError as exc:
        _fail(str(exc))
    tree.save()
    rprint(
        f"[green]已追加章节[/green] [bold]{node.id}[/bold] "
        f"(branch={branch}, {node.extracted_state.word_count} 字)"
    )


@app.command()
def branch(
    from_: str = typer.Option(..., "--from", help="分叉起点节点 id"),
    name: str = typer.Option(..., "--name", "-n", help="分支名称"),
) -> None:
    """从指定节点分叉一条新的支线。"""
    tree = _load_tree()
    try:
        br = tree.branch_from(from_, name)
    except ValueError as exc:
        rprint(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    tree.save()
    rprint(
        f"[green]已分叉支线[/green] [bold]{name}[/bold] "
        f"(fork={br.fork_point} → tip={br.active_tip})"
    )


@app.command()
def merge(
    branch: str = typer.Option(..., "--branch", "-b", help="要合并的分支"),
    into: str = typer.Option("main", "--into", help="目标主线"),
) -> None:
    """把支线的 take 提升回主线。"""
    tree = _load_tree()
    try:
        tree.merge_branch(branch, into=into)
    except ValueError as exc:
        rprint(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    tree.save()
    rprint(f"[green]已合并[/green] [bold]{branch}[/bold] → {into}")


lock_app = typer.Typer(help="管理锁。")
app.add_typer(lock_app, name="lock")


@lock_app.command("add")
def lock_add(
    target: str = typer.Argument(..., help="格式 kind:target，如 character:林晚"),
    facts: str = typer.Option(..., "--facts", "-f", help="锁定事实，用 ; 分隔"),
    scope: str = typer.Option("tree", "--scope", help="作用域: tree | branch"),
) -> None:
    """添加一个锁。"""
    if ":" not in target:
        _fail("target 格式应为 kind:target，如 character:林晚")
    if scope not in ("tree", "branch"):
        _fail(f"scope 只能是 tree 或 branch，收到：{scope}")
    kind, tgt = target.split(":", 1)
    pinned = [f.strip() for f in facts.split(";") if f.strip()]
    tree = _load_tree()
    lock = Lock(kind=kind, target=tgt, pinned_facts=pinned, scope=scope)
    tree.add_lock(lock)
    tree.save()
    rprint(
        f"[green]已添加锁[/green] [bold]{kind}:{tgt}[/bold] "
        f"({len(pinned)} 条事实, scope={scope})"
    )


@lock_app.command("list")
def lock_list() -> None:
    """列出所有锁。"""
    tree = _load_tree()
    if not tree.locks:
        rprint("[dim]暂无锁。[/dim]")
        return
    for lock in tree.locks:
        rprint(
            f"  [bold]{lock.kind}:{lock.target}[/bold] "
            f"[dim]({lock.scope})[/dim] — {lock.pinned_facts}"
        )


@app.command()
def view(
    output: Path | None = typer.Option(None, "--output", "-o", help="HTML 输出路径"),
    no_browser: bool = typer.Option(False, "--no-browser", help="不自动打开浏览器"),
) -> None:
    """渲染静态 HTML 树视图并在浏览器中打开。"""
    tree = _load_tree()
    try:
        # Pre-flight: a cyclic parent chain would otherwise render as an
        # empty view (render_html swallows traversal errors by design).
        for bname in tree.branches:
            tree.branch_path(bname)
    except ValueError as exc:
        _fail(str(exc))
    path = render_to_file(tree, output=output, open_browser=not no_browser)
    rprint(f"[green]已渲染树视图[/green] → {path}")
    if no_browser:
        rprint(f"[dim]用浏览器打开: file://{path.resolve()}[/dim]")


@app.command()
def consistency() -> None:
    """运行跨章一致性校验。"""
    tree = _load_tree()
    try:
        violations = check_consistency(tree)
    except ValueError as exc:
        _fail(str(exc))
    if not violations:
        rprint("[green]一致性校验通过 — 无设定崩。[/green]")
        return
    rprint(f"[red]检出 {len(violations)} 处设定崩：[/red]")
    for v in violations:
        rprint(f"  [red]{v.node_id}[/red] — {v.lock_target}: {v.detail}")
    raise typer.Exit(1)


@app.command()
def regenerate(
    branch: str = typer.Option(..., "--branch", "-b", help="要重绘的支线"),
    prompt: str = typer.Option(..., "--prompt", "-p", help="重绘指令"),
    lock: list[str] = typer.Option([], "--lock", help="锁定 kind:target，可多次"),
) -> None:
    """重绘支线 tip，不得违反锁定事实。"""
    tree = _load_tree()
    adapter = LLMAdapter()
    try:
        result = adapter.regenerate_branch(
            tree,
            branch=branch,
            prompt=prompt,
            lock_targets=lock,
        )
    except NotImplementedError as exc:
        rprint(f"[yellow]{exc}[/yellow]")
        raise typer.Exit(1) from exc
    except ValueError as exc:
        _fail(str(exc))
    tree.save()
    rprint(f"[green]已重绘[/green] [bold]{branch}[/bold] tip:\n{result}")


if __name__ == "__main__":
    app()
