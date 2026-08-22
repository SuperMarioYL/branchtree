"""Tests for the consistency checker — lock contradiction detection."""
from __future__ import annotations

from branchtree.consistency import check_consistency
from branchtree.tree import Lock, StoryTree


def _tree_with_lock() -> StoryTree:
    """A tree with a character lock and consistent chapters."""
    tree = StoryTree(name="t")
    tree.add_lock(
        Lock(
            kind="character",
            target="林晚",
            pinned_facts=["左手有疤", "恨哥哥"],
        )
    )
    tree.add_chapter("林晚醒来，左手有疤隐隐作痛。她恨哥哥恨到了骨子里。")
    tree.add_chapter("林晚又想起了那道疤。")
    return tree


class TestConsistency:
    def test_consistent_tree_has_no_violations(self):
        tree = _tree_with_lock()
        assert check_consistency(tree) == []

    def test_contradicted_fact_is_detected(self):
        tree = StoryTree(name="t")
        tree.add_lock(
            Lock(
                kind="character",
                target="林晚",
                pinned_facts=["左手有疤"],
            )
        )
        # a chapter that mentions the character but contradicts the fact
        tree.add_chapter("林晚低头一看，左手没有疤，光滑如初。")
        violations = check_consistency(tree)
        assert len(violations) == 1
        assert violations[0].lock_target == "林晚"
        assert "左手有疤" in violations[0].detail

    def test_hate_contradicted_by_forgiveness(self):
        tree = StoryTree(name="t")
        tree.add_lock(
            Lock(
                kind="character",
                target="林晚",
                pinned_facts=["恨哥哥"],
            )
        )
        tree.add_chapter("林晚终于原谅了哥哥，不再恨了。")
        violations = check_consistency(tree)
        assert len(violations) >= 1

    def test_chapter_without_target_is_skipped(self):
        tree = StoryTree(name="t")
        tree.add_lock(
            Lock(
                kind="character",
                target="林晚",
                pinned_facts=["左手有疤"],
            )
        )
        # chapter doesn't mention the character — should not be scanned
        tree.add_chapter("周远站在门外，左手没有疤。")
        violations = check_consistency(tree)
        assert violations == []

    def test_multiple_violations_across_chapters(self):
        tree = StoryTree(name="t")
        tree.add_lock(
            Lock(
                kind="character",
                target="林晚",
                pinned_facts=["左手有疤", "恨哥哥"],
            )
        )
        tree.add_chapter("林晚发现左手没有疤。")
        tree.add_chapter("林晚决定原谅哥哥。")
        violations = check_consistency(tree)
        assert len(violations) == 2

    def test_no_locks_means_no_violations(self):
        tree = StoryTree(name="t")
        tree.add_chapter("任意文本。")
        assert check_consistency(tree) == []
