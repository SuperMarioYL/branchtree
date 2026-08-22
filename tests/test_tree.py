"""Tests for the story-tree primitive — fork, merge, acyclicity."""
from __future__ import annotations

import pytest

from branchtree.tree import Branch, ChapterNode, Lock, StoryTree


def _build_simple_tree() -> StoryTree:
    """A tree with 5 chapters on main and a branch from ch3."""
    tree = StoryTree(name="test")
    for i in range(1, 6):
        tree.add_chapter(f"第{i}章 林晚走在路上。")
    tree.branch_from("ch3", "alt-take")
    tree.add_chapter("林晚决定先动手。", branch="alt-take")
    tree.add_chapter("林晚回到了家。", branch="alt-take")
    return tree


class TestAddChapter:
    def test_first_chapter_has_no_parent(self):
        tree = StoryTree(name="t")
        node = tree.add_chapter("hello")
        assert node.parent_id is None
        assert node.id == "ch1"
        assert node.branch == "main"

    def test_subsequent_chapters_chain_parents(self):
        tree = StoryTree(name="t")
        n1 = tree.add_chapter("a")
        n2 = tree.add_chapter("b")
        n3 = tree.add_chapter("c")
        assert n2.parent_id == n1.id
        assert n3.parent_id == n2.id

    def test_id_counter_increments(self):
        tree = StoryTree(name="t")
        tree.add_chapter("a")
        tree.add_chapter("b")
        assert tree.next_id == 3

    def test_add_to_unknown_branch_raises(self):
        tree = StoryTree(name="t")
        tree.add_chapter("a")
        with pytest.raises(ValueError, match="unknown branch"):
            tree.add_chapter("b", branch="nope")

    def test_state_extraction_records_word_count(self):
        tree = StoryTree(name="t")
        node = tree.add_chapter("林晚睁开眼")
        assert node.extracted_state.word_count == 5


class TestBranch:
    def test_branch_creates_record(self):
        tree = StoryTree(name="t")
        tree.add_chapter("a")
        tree.add_chapter("b")
        br = tree.branch_from("ch2", "alt")
        assert br.fork_point == "ch2"
        assert br.active_tip == "ch2"

    def test_branch_unknown_node_raises(self):
        tree = StoryTree(name="t")
        tree.add_chapter("a")
        with pytest.raises(ValueError, match="unknown node"):
            tree.branch_from("ch99", "alt")

    def test_branch_duplicate_name_raises(self):
        tree = StoryTree(name="t")
        tree.add_chapter("a")
        tree.branch_from("ch1", "alt")
        with pytest.raises(ValueError, match="already exists"):
            tree.branch_from("ch1", "alt")

    def test_branch_chains_from_fork_point(self):
        tree = StoryTree(name="t")
        tree.add_chapter("a")
        tree.add_chapter("b")
        tree.branch_from("ch2", "alt")
        n = tree.add_chapter("c", branch="alt")
        assert n.parent_id == "ch2"
        assert n.branch == "alt"
        assert tree.branches["alt"].active_tip == n.id

    def test_branch_path_returns_fork_to_tip(self):
        tree = _build_simple_tree()
        path = tree.branch_path("alt-take")
        assert path == ["ch3", "ch6", "ch7"]


class TestMerge:
    def test_merge_relabels_nodes(self):
        tree = _build_simple_tree()
        tree.merge_branch("alt-take", into="main")
        # alt-take's own nodes (ch6, ch7) should now be on main
        assert tree.nodes["ch6"].branch == "main"
        assert tree.nodes["ch7"].branch == "main"
        # the branch record is retired
        assert "alt-take" not in tree.branches

    def test_merge_updates_main_tip(self):
        tree = _build_simple_tree()
        tree.merge_branch("alt-take", into="main")
        assert tree.branches["main"].active_tip == "ch7"

    def test_merge_unknown_branch_raises(self):
        tree = _build_simple_tree()
        with pytest.raises(ValueError, match="unknown branch"):
            tree.merge_branch("nope")

    def test_merge_into_self_raises(self):
        tree = _build_simple_tree()
        with pytest.raises(ValueError, match="into itself"):
            tree.merge_branch("main", into="main")

    def test_fork_point_stays_shared(self):
        tree = _build_simple_tree()
        tree.merge_branch("alt-take", into="main")
        # ch3 is the fork point — it was already on main and stays there
        assert tree.nodes["ch3"].branch == "main"


class TestValidate:
    def test_valid_tree_passes(self):
        tree = _build_simple_tree()
        assert tree.validate() is True

    def test_empty_tree_passes(self):
        tree = StoryTree(name="t")
        assert tree.validate() is True

    def test_tree_with_branch_and_merge_is_acyclic(self):
        tree = _build_simple_tree()
        tree.merge_branch("alt-take", into="main")
        assert tree.validate() is True

    def test_children_of_fork_point(self):
        tree = _build_simple_tree()
        # ch3 is the fork point — main continues with ch4, branch starts with ch6
        kids = tree.children_of("ch3")
        assert set(kids) == {"ch4", "ch6"}


class TestPersistence:
    def test_save_and_load_roundtrip(self, tmp_path):
        tree = _build_simple_tree()
        tree_dir = tree.save(base_dir=tmp_path)
        assert tree_dir.exists()
        loaded = StoryTree.load(tree_dir)
        assert loaded.name == "test"
        assert len(loaded.nodes) == 7
        assert "alt-take" in loaded.branches
        assert loaded.validate() is True

    def test_find_discovers_tree_dir(self, tmp_path):
        tree = _build_simple_tree()
        tree.save(base_dir=tmp_path)
        found = StoryTree.find(base_dir=tmp_path)
        assert found is not None
        assert found.name == "test"


class TestLocks:
    def test_known_characters_from_locks(self):
        tree = StoryTree(name="t")
        tree.add_lock(Lock(kind="character", target="林晚", pinned_facts=["左手有疤"]))
        tree.add_lock(Lock(kind="setting", target="长安城"))
        assert tree.known_characters() == ["林晚"]

    def test_lock_persists_through_save(self, tmp_path):
        tree = StoryTree(name="t")
        tree.add_lock(Lock(kind="character", target="林晚", pinned_facts=["左手有疤"]))
        tree.save(base_dir=tmp_path)
        loaded = StoryTree.find(base_dir=tmp_path)
        assert loaded is not None
        assert loaded.locks[0].target == "林晚"
