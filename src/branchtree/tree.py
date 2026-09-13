"""The branchable story-tree primitive.

A story tree is a directed acyclic graph of chapter nodes.  Every node
carries a ``parent_id``, so forking an alternate take and later merging it
back into the main line never destroys prior work — the old chapters stay
reachable in the tree.  This is the core format-asset of BranchTree and
the reason the project exists: serialized fiction deserves version
control over *narrative state*, not just text.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from .state import StateSnap, extract_state

TREE_DIR_SUFFIX = ".tree"
TREE_FILENAME = "tree.json"


class ChapterNode(BaseModel):
    """A single chapter in the story tree."""

    id: str
    parent_id: Optional[str] = None
    branch: str = "main"
    text: str = ""
    extracted_state: StateSnap = Field(default_factory=StateSnap)


class Branch(BaseModel):
    """A named alternative continuation from a fork point.

    ``fork_point`` is the shared node both lines pass through; ``active_tip``
    is the newest node on this branch.
    """

    name: str
    fork_point: str
    active_tip: str


class Lock(BaseModel):
    """An immutable invariant across regeneration.

    ``kind``   — character | setting | foreshadow
    ``scope``  — tree   | branch
    """

    kind: str
    target: str
    pinned_facts: list[str] = Field(default_factory=list)
    scope: str = "tree"


class StoryTree(BaseModel):
    """The branchable story-tree project file."""

    name: str
    next_id: int = 1
    nodes: dict[str, ChapterNode] = Field(default_factory=dict)
    branches: dict[str, Branch] = Field(default_factory=dict)
    locks: list[Lock] = Field(default_factory=list)

    # ------------------------------------------------------------------
    # character index — a convenience set used by state extraction
    # ------------------------------------------------------------------

    def known_characters(self) -> list[str]:
        """Return the targets of every character lock on the tree."""
        return [
            lock.target
            for lock in self.locks
            if lock.kind == "character"
        ]

    # ------------------------------------------------------------------
    # chapter operations
    # ------------------------------------------------------------------

    def add_chapter(
        self,
        text: str,
        branch: str = "main",
    ) -> ChapterNode:
        """Append a chapter to *branch*, parented to that branch's active tip."""
        if branch != "main" and branch not in self.branches:
            raise ValueError(f"unknown branch '{branch}'")

        parent_id: Optional[str] = None
        if branch in self.branches:
            parent_id = self.branches[branch].active_tip

        node_id = f"ch{self.next_id}"
        self.next_id += 1

        node = ChapterNode(
            id=node_id,
            parent_id=parent_id,
            branch=branch,
            text=text,
            extracted_state=extract_state(text, self.known_characters()),
        )
        self.nodes[node_id] = node

        if branch == "main" and "main" not in self.branches:
            self.branches["main"] = Branch(
                name="main",
                fork_point=node_id,
                active_tip=node_id,
            )
        else:
            self.branches[branch].active_tip = node_id

        return node

    def branch_from(self, node_id: str, branch_name: str) -> Branch:
        """Fork a new branch starting from *node_id*."""
        if node_id not in self.nodes:
            raise ValueError(f"unknown node '{node_id}'")
        if branch_name in self.branches:
            raise ValueError(f"branch '{branch_name}' already exists")
        branch = Branch(name=branch_name, fork_point=node_id, active_tip=node_id)
        self.branches[branch_name] = branch
        return branch

    def merge_branch(self, branch_name: str, into: str = "main") -> None:
        """Promote *branch_name*'s take back into the *into* line.

        The branch's own nodes (everything after the shared fork point) are
        relabeled to the target branch and the target's active tip moves to
        the branch tip.  The fork point itself is already shared and stays
        untouched.  The merged branch record is retired.
        """
        if branch_name not in self.branches:
            raise ValueError(f"unknown branch '{branch_name}'")
        if branch_name == into:
            raise ValueError("cannot merge a branch into itself")
        if into not in self.branches:
            raise ValueError(f"unknown target branch '{into}'")

        branch = self.branches[branch_name]
        for node in self.nodes.values():
            if node.branch == branch_name and node.id != branch.fork_point:
                node.branch = into

        if branch.active_tip != branch.fork_point:
            self.branches[into].active_tip = branch.active_tip

        del self.branches[branch_name]

    def add_lock(self, lock: Lock) -> Lock:
        """Register a new lock on the tree."""
        self.locks.append(lock)
        return lock

    # ------------------------------------------------------------------
    # traversal helpers
    # ------------------------------------------------------------------

    def branch_path(self, branch_name: str) -> list[str]:
        """Return node ids from the branch's fork point to its active tip.

        Raises ``ValueError`` if the parent chain contains a cycle — a
        hand-edited or corrupted ``tree.json`` must fail loudly here, not
        loop forever.
        """
        if branch_name not in self.branches:
            raise ValueError(f"unknown branch '{branch_name}'")
        branch = self.branches[branch_name]
        path: list[str] = []
        seen: set[str] = set()
        current: Optional[str] = branch.active_tip
        while current is not None and current in self.nodes:
            if current in seen:
                raise ValueError(
                    f"cycle detected in parent chain at '{current}' "
                    f"(branch '{branch_name}') — tree.json 已损坏"
                )
            seen.add(current)
            path.append(current)
            node = self.nodes[current]
            if current == branch.fork_point:
                break
            current = node.parent_id
        path.reverse()
        return path

    def children_of(self, node_id: str) -> list[str]:
        """Return the ids of every node whose parent is *node_id*."""
        return [
            nid
            for nid, node in self.nodes.items()
            if node.parent_id == node_id
        ]

    def nodes_for_lock(self, lock: Lock) -> list[ChapterNode]:
        """Return the nodes a lock applies to, based on its scope."""
        if lock.scope == "branch":
            branch_name = lock.target if lock.target in self.branches else "main"
            return [
                self.nodes[nid]
                for nid in self.branch_path(branch_name)
                if nid in self.nodes
            ]
        return list(self.nodes.values())

    # ------------------------------------------------------------------
    # validation
    # ------------------------------------------------------------------

    def validate(self) -> bool:
        """Verify the tree is acyclic and all references are intact."""
        n = len(self.nodes)
        for start_id in self.nodes:
            seen: set[str] = set()
            current: Optional[str] = start_id
            while current is not None:
                if current in seen:
                    return False
                seen.add(current)
                node = self.nodes.get(current)
                if node is None:
                    return False
                current = node.parent_id
                if len(seen) > n:
                    return False
        for branch in self.branches.values():
            if branch.fork_point not in self.nodes:
                return False
            if branch.active_tip not in self.nodes:
                return False
        return True

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------

    def save(self, base_dir: str | Path = ".") -> Path:
        """Persist the tree to ``<base_dir>/<name>.tree/tree.json``."""
        tree_dir = Path(base_dir) / f"{self.name}{TREE_DIR_SUFFIX}"
        tree_dir.mkdir(parents=True, exist_ok=True)
        data_file = tree_dir / TREE_FILENAME
        data_file.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        return tree_dir

    @classmethod
    def load(cls, tree_dir: str | Path) -> "StoryTree":
        """Load a tree from a ``.tree/`` directory."""
        tree_dir = Path(tree_dir)
        data_file = tree_dir / TREE_FILENAME
        return cls.model_validate_json(data_file.read_text(encoding="utf-8"))

    @classmethod
    def find(cls, base_dir: str | Path = ".") -> Optional["StoryTree"]:
        """Find and load the single ``.tree/`` directory in *base_dir*."""
        base = Path(base_dir)
        tree_dirs = sorted(base.glob(f"*{TREE_DIR_SUFFIX}"))
        if not tree_dirs:
            return None
        return cls.load(tree_dirs[0])
