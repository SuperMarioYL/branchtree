"""Chapter state extraction.

For m1 (no LLM) the extractor is a lightweight rule-based pass that
records word count and which known characters appear in the text.
The LLM-backed deep extractor lands in m2 — see :mod:`branchtree.llm`.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class StateSnap(BaseModel):
    """A snapshot of the narrative state extracted from a chapter."""

    characters: list[str] = Field(default_factory=list)
    summary: str = ""
    word_count: int = 0


def extract_state(
    text: str,
    known_characters: list[str] | None = None,
) -> StateSnap:
    """Extract a :class:`StateSnap` from *text* without an LLM.

    For each name in *known_characters* we record whether it surfaces in
    the chapter, so downstream consistency checks have something concrete
    to lock against. The summary is left empty here — m2 fills it via the
    LLM adapter.
    """
    word_count = len(text.strip())
    characters: list[str] = []
    if known_characters:
        characters = [name for name in known_characters if name in text]
    return StateSnap(
        characters=characters,
        summary="",
        word_count=word_count,
    )
