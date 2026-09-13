"""BranchTree — branchable story-tree agent for serialized fiction."""
from __future__ import annotations

__version__ = "0.2.0"

from .tree import Branch, ChapterNode, Lock, StoryTree
from .state import StateSnap, extract_state
from .consistency import Violation, check_consistency

__all__ = [
    "__version__",
    "Branch",
    "ChapterNode",
    "Lock",
    "StoryTree",
    "StateSnap",
    "extract_state",
    "Violation",
    "check_consistency",
]
