"""CLI contract tests — clean errors, no-clobber, exit codes, regenerate.

Every failure case here was a raw traceback (or a hang, or silent data
loss) at v0.1.0; the assertions pin the v0.2.0 contract: one clean red
message, exit 1, nothing mutated.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from branchtree.cli import app

runner = CliRunner()

# Wide console so rich never wraps the asserted message fragments.
ENV = {"COLUMNS": "256"}


@pytest.fixture()
def workdir(tmp_path, monkeypatch):
    """Run each CLI test inside its own empty working directory."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _make_tree(name: str = "serial") -> None:
    result = runner.invoke(app, ["new", name], env=ENV)
    assert result.exit_code == 0, result.output


def _add_chapter(text: str, branch: list[str] | None = None) -> None:
    args = ["add", "--text", text, *(branch or [])]
    result = runner.invoke(app, args, env=ENV)
    assert result.exit_code == 0, result.output


class TestAddInputContract:
    def test_missing_file_is_a_clean_error(self, workdir):
        _make_tree()
        result = runner.invoke(app, ["add", "--file", "nope.txt"], env=ENV)
        assert result.exit_code == 1
        assert "文件不存在" in result.output
        assert "nope.txt" in result.output

    def test_non_utf8_file_is_a_clean_error(self, workdir):
        _make_tree()
        Path("bad.txt").write_bytes("不是UTF8".encode("utf-16"))
        result = runner.invoke(app, ["add", "--file", "bad.txt"], env=ENV)
        assert result.exit_code == 1
        assert "UTF-8" in result.output

    def test_unknown_branch_is_a_clean_error_and_tree_unchanged(self, workdir):
        _make_tree()
        _add_chapter("林晚醒来，左手有疤。")
        before = Path("serial.tree/tree.json").read_text(encoding="utf-8")
        result = runner.invoke(
            app, ["add", "--text", "测试", "--branch", "nosuch"], env=ENV
        )
        assert result.exit_code == 1
        assert "unknown branch" in result.output
        after = Path("serial.tree/tree.json").read_text(encoding="utf-8")
        assert after == before

    def test_missing_text_and_file_is_a_clean_error(self, workdir):
        _make_tree()
        result = runner.invoke(app, ["add"], env=ENV)
        assert result.exit_code == 1
        assert "--file" in result.output and "--text" in result.output


class TestUnreadableTreeContract:
    def test_corrupt_tree_json_is_a_clean_error(self, workdir):
        _make_tree()
        Path("serial.tree/tree.json").write_text('{"name": ', encoding="utf-8")
        result = runner.invoke(app, ["lock", "list"], env=ENV)
        assert result.exit_code == 1
        assert "已损坏" in result.output
        assert "serial.tree" in result.output

    def test_tree_dir_without_tree_json_is_a_clean_error(self, workdir):
        _make_tree()
        Path("serial.tree/tree.json").unlink()
        result = runner.invoke(app, ["lock", "list"], env=ENV)
        assert result.exit_code == 1
        assert "缺少" in result.output

    def test_no_tree_dir_is_a_clean_error(self, workdir):
        result = runner.invoke(app, ["lock", "list"], env=ENV)
        assert result.exit_code == 1
        assert "未找到故事树" in result.output


class TestLockScopeContract:
    def test_invalid_scope_is_rejected_and_not_persisted(self, workdir):
        _make_tree()
        result = runner.invoke(
            app,
            ["lock", "add", "character:林晚", "--facts", "左手有疤",
             "--scope", "banana"],
            env=ENV,
        )
        assert result.exit_code == 1
        assert "scope" in result.output
        data = json.loads(Path("serial.tree/tree.json").read_text(encoding="utf-8"))
        assert data["locks"] == []

    def test_valid_scope_still_works(self, workdir):
        _make_tree()
        result = runner.invoke(
            app,
            ["lock", "add", "character:林晚", "--facts", "左手有疤",
             "--scope", "branch"],
            env=ENV,
        )
        assert result.exit_code == 0
        data = json.loads(Path("serial.tree/tree.json").read_text(encoding="utf-8"))
        assert data["locks"][0]["scope"] == "branch"


class TestNewNoClobber:
    def test_new_refuses_to_wipe_existing_tree(self, workdir):
        _make_tree()
        _add_chapter("林晚醒来，左手有疤。")
        tree_file = Path("serial.tree/tree.json")
        before = tree_file.read_text(encoding="utf-8")
        result = runner.invoke(app, ["new", "serial"], env=ENV)
        assert result.exit_code == 1
        assert "--force" in result.output
        assert tree_file.read_text(encoding="utf-8") == before

    def test_force_overwrites_existing_tree(self, workdir):
        _make_tree()
        _add_chapter("林晚醒来，左手有疤。")
        result = runner.invoke(app, ["new", "serial", "--force"], env=ENV)
        assert result.exit_code == 0
        assert "已覆盖" in result.output
        data = json.loads(Path("serial.tree/tree.json").read_text(encoding="utf-8"))
        assert data["nodes"] == {}

    def test_name_with_separator_is_rejected(self, workdir):
        result = runner.invoke(app, ["new", "a/b"], env=ENV)
        assert result.exit_code == 1
        assert "路径分隔符" in result.output
        assert not Path("a").exists()

    def test_empty_name_is_rejected(self, workdir):
        result = runner.invoke(app, ["new", ""], env=ENV)
        assert result.exit_code == 1
        assert "不能为空" in result.output

    def test_fresh_name_still_creates(self, workdir):
        result = runner.invoke(app, ["new", "fresh"], env=ENV)
        assert result.exit_code == 0
        assert "已创建故事树" in result.output


class TestConsistencyExitCode:
    def _build_contradiction_tree(self) -> None:
        result = runner.invoke(
            app, ["lock", "add", "character:林晚", "--facts", "左手有疤"], env=ENV
        )
        assert result.exit_code == 0, result.output
        _add_chapter("林晚醒来，左手有疤。")
        _add_chapter("林晚低头一看，左手没有疤，光滑如初。")

    def test_violations_exit_1(self, workdir):
        _make_tree()
        self._build_contradiction_tree()
        result = runner.invoke(app, ["consistency"], env=ENV)
        assert result.exit_code == 1
        assert "1 处设定崩" in result.output
        assert "ch2" in result.output

    def test_clean_tree_exits_0(self, workdir):
        _make_tree()
        result = runner.invoke(
            app, ["lock", "add", "character:林晚", "--facts", "左手有疤"], env=ENV
        )
        assert result.exit_code == 0
        _add_chapter("林晚醒来，左手有疤隐隐作痛。")
        result = runner.invoke(app, ["consistency"], env=ENV)
        assert result.exit_code == 0
        assert "通过" in result.output

    def test_no_locks_exits_0(self, workdir):
        _make_tree()
        _add_chapter("任意文本。")
        result = runner.invoke(app, ["consistency"], env=ENV)
        assert result.exit_code == 0


class TestCycleGuardCli:
    def _write_cyclic_tree(self) -> None:
        """ch2 <-> ch3 parent cycle; fork_point ch1 excludes the cycle."""
        _add_chapter("第一章。")
        _add_chapter("第二章。")
        _add_chapter("第三章。")
        tree_file = Path("serial.tree/tree.json")
        data = json.loads(tree_file.read_text(encoding="utf-8"))
        data["nodes"]["ch2"]["parent_id"] = "ch3"
        data["nodes"]["ch3"]["parent_id"] = "ch2"
        tree_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def test_view_on_cyclic_tree_errors_cleanly(self, workdir):
        _make_tree()
        self._write_cyclic_tree()
        result = runner.invoke(app, ["view", "--no-browser"], env=ENV)
        assert result.exit_code == 1
        assert "cycle" in result.output

    def test_consistency_on_cyclic_tree_errors_cleanly(self, workdir):
        _make_tree()
        self._write_cyclic_tree()
        result = runner.invoke(
            app,
            ["lock", "add", "character:林晚", "--facts", "左手有疤",
             "--scope", "branch"],
            env=ENV,
        )
        assert result.exit_code == 0
        result = runner.invoke(app, ["consistency"], env=ENV)
        assert result.exit_code == 1
        assert "cycle" in result.output


class TestHappyPath:
    def test_full_workflow_still_succeeds(self, workdir):
        _make_tree()
        _add_chapter("林晚醒来，左手有疤。")
        result = runner.invoke(
            app, ["lock", "add", "character:林晚", "--facts", "左手有疤"], env=ENV
        )
        assert result.exit_code == 0
        result = runner.invoke(
            app, ["branch", "--from", "ch1", "--name", "alternate"], env=ENV
        )
        assert result.exit_code == 0
        _add_chapter("林晚左手没有疤。", branch=["--branch", "alternate"])
        result = runner.invoke(app, ["consistency"], env=ENV)
        assert result.exit_code == 1  # the injected contradiction
        result = runner.invoke(app, ["view", "--no-browser"], env=ENV)
        assert result.exit_code == 0
        assert Path("serial.tree/tree.html").is_file()
        result = runner.invoke(
            app, ["merge", "--branch", "alternate", "--into", "main"], env=ENV
        )
        assert result.exit_code == 0
        data = json.loads(Path("serial.tree/tree.json").read_text(encoding="utf-8"))
        assert "alternate" not in data["branches"]
        assert data["nodes"]["ch2"]["branch"] == "main"


class FakeClient:
    """Stands in for openai.OpenAI in regenerate tests (no network)."""

    def __init__(self, replies: list[str]) -> None:
        self.captured: list[dict] = []
        replies_left = list(replies)
        client = self

        class _Completions:
            def create(self, *, model: str, messages: list[dict]) -> object:
                client.captured.append({"model": model, "messages": messages})
                message = SimpleNamespace(content=replies_left.pop(0))
                return SimpleNamespace(choices=[SimpleNamespace(message=message)])

        self.chat = SimpleNamespace(completions=_Completions())


class TestRegenerateCli:
    def _build_tree_with_branch(self) -> None:
        runner.invoke(
            app, ["lock", "add", "character:林晚", "--facts", "左手有疤"], env=ENV
        )
        _add_chapter("林晚醒来，左手有疤隐隐作痛。")
        result = runner.invoke(
            app, ["branch", "--from", "ch1", "--name", "alt"], env=ENV
        )
        assert result.exit_code == 0, result.output
        _add_chapter("林晚握紧左拳，疤在发烫。", branch=["--branch", "alt"])

    def test_regenerate_rewrites_tip(self, workdir, monkeypatch):
        _make_tree()
        self._build_tree_with_branch()
        fake = FakeClient(["林晚盯着左手，那道旧疤依旧清晰。"])
        monkeypatch.setattr(
            "branchtree.llm.LLMAdapter._client", lambda self: fake
        )
        result = runner.invoke(
            app,
            ["regenerate", "--branch", "alt", "--prompt", "更克制一点"],
            env=ENV,
        )
        assert result.exit_code == 0, result.output
        assert "已重绘" in result.output
        data = json.loads(Path("serial.tree/tree.json").read_text(encoding="utf-8"))
        assert data["nodes"]["ch2"]["text"] == "林晚盯着左手，那道旧疤依旧清晰。"
        # main-line chapter untouched
        assert data["nodes"]["ch1"]["text"] == "林晚醒来，左手有疤隐隐作痛。"

    def test_regenerate_violation_refuses_write(self, workdir, monkeypatch):
        _make_tree()
        self._build_tree_with_branch()
        before = Path("serial.tree/tree.json").read_text(encoding="utf-8")
        fake = FakeClient(["林晚左手没有疤，光滑如初。"])
        monkeypatch.setattr(
            "branchtree.llm.LLMAdapter._client", lambda self: fake
        )
        result = runner.invoke(
            app,
            ["regenerate", "--branch", "alt", "--prompt", "重写"],
            env=ENV,
        )
        assert result.exit_code == 1
        assert "违反锁定事实" in result.output
        assert Path("serial.tree/tree.json").read_text(encoding="utf-8") == before

    def test_regenerate_unknown_branch_is_clean(self, workdir, monkeypatch):
        _make_tree()
        self._build_tree_with_branch()
        fake = FakeClient(["unused"])
        monkeypatch.setattr(
            "branchtree.llm.LLMAdapter._client", lambda self: fake
        )
        result = runner.invoke(
            app,
            ["regenerate", "--branch", "nope", "--prompt", "x"],
            env=ENV,
        )
        assert result.exit_code == 1
        assert "unknown branch" in result.output
        assert fake.captured == []  # no LLM call was made

