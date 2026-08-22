"""LLM adapter — openai-compatible client for regeneration and state extraction.

m1 ships the tree primitive without an LLM.  The functions below are the
stub surface for m2: they raise :class:`NotImplementedError` until the
regenerate / lock-character consistency loop is wired up.  Keeping the
interface here means m2 only fills in bodies — no new module, no new
contract.
"""
from __future__ import annotations

from typing import Any

from .tree import StoryTree


class LLMAdapter:
    """Thin wrapper over an openai-compatible chat endpoint.

    The constructor stores connection config but does **not** import the
    ``openai`` package — that import is deferred to the first call so
    that m1 users (and the test suite) never need the dependency
    installed.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str = "deepseek-chat",
    ) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.model = model

    def _client(self) -> Any:
        """Lazily build the openai client (m2)."""
        try:
            import openai  # noqa: WPS433 — deferred on purpose
        except ImportError as exc:
            raise NotImplementedError(
                "LLM features require m2 — install openai and configure "
                "OPENAI_BASE_URL / OPENAI_API_KEY."
            ) from exc
        return openai.OpenAI(base_url=self.base_url, api_key=self.api_key)

    # ------------------------------------------------------------------
    # m2 surface — stubs
    # ------------------------------------------------------------------

    def regenerate_branch(
        self,
        tree: StoryTree,
        branch: str,
        prompt: str,
        lock_targets: list[str] | None = None,
    ) -> str:
        """Regenerate the tip of *branch* respecting locked facts (m2)."""
        raise NotImplementedError(
            "regenerate is an m2 feature — the lock-respecting "
            "regeneration loop lands in milestone 2."
        )

    def extract_state_deep(self, text: str) -> dict[str, Any]:
        """Extract a rich state snapshot via the LLM (m2)."""
        raise NotImplementedError(
            "LLM state extraction is an m2 feature."
        )
