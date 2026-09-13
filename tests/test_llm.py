"""Tests for the LLM adapter's lock-respecting regeneration.

The openai client is replaced by a scripted fake, so these tests pin
the regenerate contract (rewrite tip, enforce locks, refuse violations)
without any network or dependency on a live endpoint.
"""
from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from branchtree.consistency import check_consistency
from branchtree.llm import LLMAdapter
from branchtree.tree import Lock, StoryTree


class FakeClient:
    """Stands in for openai.OpenAI; returns scripted replies in order."""

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


def _tree_with_branch() -> tuple[StoryTree, str]:
    """main: ch1; alt: ch2 (forked from ch1), with a character lock."""
    tree = StoryTree(name="t")
    tree.add_lock(Lock(kind="character", target="林晚", pinned_facts=["左手有疤"]))
    tree.add_chapter("林晚醒来，左手有疤隐隐作痛。")
    tree.branch_from("ch1", "alt")
    tree.add_chapter("林晚握紧左拳，疤在发烫。", branch="alt")
    return tree, "alt"


def _adapter(fake: FakeClient) -> LLMAdapter:
    adapter = LLMAdapter()
    adapter._client = lambda: fake  # type: ignore[method-assign]
    return adapter


class TestRegenerateHappyPath:
    def test_rewrites_tip_and_recomputes_state(self):
        tree, branch = _tree_with_branch()
        adapter = _adapter(FakeClient(["林晚盯着左手，那道旧疤依旧清晰。"]))
        result = adapter.regenerate_branch(tree, branch, "更克制一点")
        assert result == "林晚盯着左手，那道旧疤依旧清晰。"
        tip = tree.nodes[tree.branches[branch].active_tip]
        assert tip.id == "ch2"
        assert tip.parent_id == "ch1"
        assert tip.branch == "alt"
        assert tip.text == "林晚盯着左手，那道旧疤依旧清晰。"
        assert tip.extracted_state.word_count == len("林晚盯着左手，那道旧疤依旧清晰。")
        assert "林晚" in tip.extracted_state.characters
        # main-line chapter untouched
        assert tree.nodes["ch1"].text == "林晚醒来，左手有疤隐隐作痛。"

    def test_prompt_carries_locks_and_branch_context(self):
        tree, branch = _tree_with_branch()
        fake = FakeClient(["林晚盯着左手，那道旧疤依旧清晰。"])
        adapter = _adapter(fake)
        adapter.regenerate_branch(tree, branch, "更克制一点")
        assert len(fake.captured) == 1
        prompt = fake.captured[0]["messages"][0]["content"]
        assert "左手有疤" in prompt
        assert "林晚醒来" in prompt  # branch context includes prior chapters
        assert "更克制一点" in prompt

    def test_lock_targets_filter_which_locks_apply(self):
        tree, branch = _tree_with_branch()
        tree.add_lock(Lock(kind="setting", target="长安城", pinned_facts=["城墙是黑色"]))
        # the reply negates the character fact but not the setting fact
        reply = "林晚左手没有疤，但长安城的城墙黑得发亮。"
        fake = FakeClient([reply])
        adapter = _adapter(fake)
        # only the setting lock applies: the character contradiction is not enforced
        adapter.regenerate_branch(tree, branch, "重写", lock_targets=["setting:长安城"])
        prompt = fake.captured[0]["messages"][0]["content"]
        assert "setting:长安城" in prompt
        assert "character:林晚" not in prompt
        assert tree.nodes["ch2"].text == reply

        # without filtering, every lock applies and the same reply is refused
        tree2, branch2 = _tree_with_branch()
        tree2.add_lock(Lock(kind="setting", target="长安城", pinned_facts=["城墙是黑色"]))
        adapter2 = _adapter(FakeClient([reply]))
        with pytest.raises(ValueError, match="左手有疤"):
            adapter2.regenerate_branch(tree2, branch2, "重写")


class TestRegenerateRefusals:
    def test_lock_violation_refused_and_tree_unchanged(self):
        tree, branch = _tree_with_branch()
        before = tree.nodes["ch2"].text
        adapter = _adapter(FakeClient(["林晚左手没有疤，光滑如初。"]))
        with pytest.raises(ValueError, match="左手有疤"):
            adapter.regenerate_branch(tree, branch, "重写")
        assert tree.nodes["ch2"].text == before

    def test_unknown_branch_raises_before_any_llm_call(self):
        tree, _ = _tree_with_branch()
        fake = FakeClient(["unused"])
        adapter = _adapter(fake)
        with pytest.raises(ValueError, match="unknown branch"):
            adapter.regenerate_branch(tree, "nope", "x")
        assert fake.captured == []

    def test_empty_branch_cannot_regenerate_shared_fork_point(self):
        tree, _ = _tree_with_branch()
        tree.branch_from("ch1", "empty")  # tip == fork_point
        adapter = _adapter(FakeClient(["unused"]))
        with pytest.raises(ValueError, match="分叉点"):
            adapter.regenerate_branch(tree, "empty", "x")

    def test_unknown_lock_target_raises(self):
        tree, branch = _tree_with_branch()
        adapter = _adapter(FakeClient(["unused"]))
        with pytest.raises(ValueError, match="unknown lock target"):
            adapter.regenerate_branch(
                tree, branch, "x", lock_targets=["character:不存在"]
            )

    def test_empty_model_reply_raises(self):
        tree, branch = _tree_with_branch()
        adapter = _adapter(FakeClient(["   "]))
        with pytest.raises(ValueError, match="空内容"):
            adapter.regenerate_branch(tree, branch, "x")


class TestDeferredOpenaiImport:
    def test_missing_openai_raises_actionable_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "openai", None)
        adapter = LLMAdapter()
        with pytest.raises(NotImplementedError, match="OPENAI_BASE_URL"):
            adapter._client()

    def test_env_defaults_are_used(self, monkeypatch):
        monkeypatch.setenv("OPENAI_BASE_URL", "https://api.example.com/v1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        adapter = LLMAdapter()
        assert adapter.base_url == "https://api.example.com/v1"
        assert adapter.api_key == "sk-test"


class TestRegeneratedTreeStaysConsistent:
    def test_accepted_rewrite_passes_consistency(self):
        tree, branch = _tree_with_branch()
        adapter = _adapter(FakeClient(["林晚望着左手的旧疤出神。"]))
        adapter.regenerate_branch(tree, branch, "重写")
        assert check_consistency(tree) == []
