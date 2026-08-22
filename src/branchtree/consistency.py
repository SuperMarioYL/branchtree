"""Cross-chapter consistency checking.

For m1 the checker is rule-based: it walks every lock and verifies that
pinned facts are not contradicted by an explicit negation pattern in the
chapters the lock covers.  The LLM-powered deep contradiction detector —
which catches subtle tonal drift and implicit OOC — lands in m2 via
:mod:`branchtree.llm`.
"""
from __future__ import annotations

from pydantic import BaseModel

from .tree import Lock, StoryTree


class Violation(BaseModel):
    """A single consistency violation found by the checker."""

    node_id: str
    lock_target: str
    kind: str
    detail: str


# Negation fragments that, when they appear next to a fact's object,
# signal a likely contradiction.  Kept intentionally narrow: m1 only
# catches *explicit* contradictions, which is enough to demonstrate the
# lock primitive.
_NEGATION_TOKENS = ("没有", "无", "不", "非", "消失", "褪去")


def _fact_object(fact: str) -> tuple[str, str]:
    """Split a fact like '左手有疤' into ('有', '疤').

    Returns the first copular verb found and the remainder.  If no
    copula is present the whole string is treated as the object with an
    empty verb.
    """
    for verb in ("有", "是", "会", "能", "喜欢", "恨", "爱"):
        if verb in fact:
            idx = fact.index(verb)
            return verb, fact[idx + len(verb):]
    return "", fact


def _is_contradicted(text: str, fact: str) -> bool:
    """Return True if *text* contains an explicit negation of *fact*."""
    verb, obj = _fact_object(fact)
    if not verb or not obj:
        return False
    for neg in _NEGATION_TOKENS:
        if neg + obj in text or neg + verb + obj in text:
            return True
    # '恨哥哥' contradicted by '不恨' or '原谅'
    if verb == "恨" and ("原谅" in text or "不恨" in text):
        return True
    return False


def check_consistency(tree: StoryTree) -> list[Violation]:
    """Check the tree against its locks and return every violation found."""
    violations: list[Violation] = []

    for lock in tree.locks:
        relevant = tree.nodes_for_lock(lock)
        for fact in lock.pinned_facts:
            for node in relevant:
                # Only scan chapters that actually mention the locked
                # target, so unrelated prose does not produce noise.
                if lock.target and lock.target not in node.text:
                    continue
                if _is_contradicted(node.text, fact):
                    violations.append(Violation(
                        node_id=node.id,
                        lock_target=lock.target,
                        kind=lock.kind,
                        detail=f"pinned fact '{fact}' contradicted in {node.id}",
                    ))
    return violations
