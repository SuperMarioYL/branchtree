"""LLM adapter — openai-compatible client for regeneration.

``regenerate_branch`` rewrites the tip chapter of a branch through an
openai-compatible chat endpoint.  The rewritten text is post-checked
against every applicable lock's pinned facts with the same rule-based
contradiction detector the ``consistency`` command uses: an explicit
negation of a pinned fact refuses the write and leaves the tree
untouched.  The ``openai`` import stays deferred to the first call so
non-LLM usage (and the rule-based test suite) never needs the
dependency active.
"""
from __future__ import annotations

import os
from typing import Any

from .consistency import _is_contradicted
from .prompts import render_regen_prompt
from .state import extract_state
from .tree import StoryTree


class LLMAdapter:
    """Thin wrapper over an openai-compatible chat endpoint.

    The constructor stores connection config but does **not** import the
    ``openai`` package — that import is deferred to the first call so
    users who never regenerate (and the rule-based test suite) never
    need the dependency active.  ``base_url`` / ``api_key`` fall back to
    the ``OPENAI_BASE_URL`` / ``OPENAI_API_KEY`` environment variables.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str = "deepseek-chat",
    ) -> None:
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model

    def _client(self) -> Any:
        """Lazily build the openai client."""
        try:
            import openai  # noqa: WPS433 — deferred on purpose
        except ImportError as exc:
            raise NotImplementedError(
                "LLM 功能需要 openai 包 — 请安装 openai 并配置 "
                "OPENAI_BASE_URL / OPENAI_API_KEY。"
            ) from exc
        return openai.OpenAI(base_url=self.base_url, api_key=self.api_key)

    # ------------------------------------------------------------------
    # regeneration
    # ------------------------------------------------------------------

    def regenerate_branch(
        self,
        tree: StoryTree,
        branch: str,
        prompt: str,
        lock_targets: list[str] | None = None,
    ) -> str:
        """Regenerate the tip of *branch* respecting locked facts.

        The rewritten text replaces the tip node's ``text`` (id, parent
        and branch label are preserved) and its extracted state is
        recomputed.  Raises ``ValueError`` — leaving the tree unmodified —
        for an unknown branch, an empty branch, an unknown lock target,
        an empty model reply, or a reply that explicitly negates a
        pinned fact of an applicable lock.
        """
        if branch not in tree.branches:
            raise ValueError(f"unknown branch '{branch}'")
        branch_rec = tree.branches[branch]
        if branch_rec.active_tip == branch_rec.fork_point:
            raise ValueError(
                f"branch '{branch}' 在分叉点后还没有章节 — 先用 "
                f"`branchtree add --branch {branch}` 写一章再重绘。"
            )

        locks = self._applicable_locks(tree, lock_targets)
        branch_nodes = [tree.nodes[nid] for nid in tree.branch_path(branch)]
        user_prompt = render_regen_prompt(locks, branch_nodes, prompt)

        client = self._client()
        completion = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = completion.choices[0].message.content
        if not text or not text.strip():
            raise ValueError("模型返回了空内容，未做任何修改。")
        text = text.strip()

        violated = [
            fact
            for lock in locks
            for fact in lock.pinned_facts
            if _is_contradicted(text, fact)
        ]
        if violated:
            raise ValueError(
                "重绘结果违反锁定事实，已拒绝写入：" + "；".join(violated)
            )

        tip = tree.nodes[branch_rec.active_tip]
        tip.text = text
        tip.extracted_state = extract_state(text, tree.known_characters())
        return text

    @staticmethod
    def _applicable_locks(
        tree: StoryTree,
        lock_targets: list[str] | None,
    ) -> list:
        """Return the locks a regeneration must respect.

        With no *lock_targets* every lock applies; otherwise only the
        locks matching a ``kind:target`` entry, and an entry matching
        nothing is rejected rather than silently ignored.
        """
        if not lock_targets:
            return list(tree.locks)
        by_key = {f"{lock.kind}:{lock.target}": lock for lock in tree.locks}
        unknown = [t for t in lock_targets if t not in by_key]
        if unknown:
            raise ValueError(
                "unknown lock target(s): " + ", ".join(unknown)
            )
        return [by_key[t] for t in lock_targets]
