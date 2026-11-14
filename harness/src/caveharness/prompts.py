"""Turn wording, loaded from prompts/turns.toml (prompt draft v3)."""
from __future__ import annotations

import hashlib
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .config import PROMPTS_FILE, WORLD_KIND


@dataclass(frozen=True)
class Prompts:
    raw: dict
    sha256: str

    @classmethod
    def load(cls, path: Path = PROMPTS_FILE) -> "Prompts":
        # Hash with line endings normalised: a Windows checkout can turn LF into
        # CRLF, which leaves the prompt text unchanged (TOML normalises it) but
        # would change a raw-byte hash and make identical prompts look different.
        data = path.read_bytes().replace(b"\r\n", b"\n")
        return cls(tomllib.loads(data.decode("utf-8")), hashlib.sha256(data).hexdigest())

    @property
    def system(self) -> str:
        return self.raw["system"]

    @property
    def wordings(self) -> list[str]:
        return sorted(self.raw["expectation"])

    def expectation(self, world: str, option: str) -> str:
        return self.raw["expectation"][option][WORLD_KIND[world]]

    def all_expectation_sentences(self) -> list[str]:
        return [s for opt in self.raw["expectation"].values() for s in opt.values()]

    @staticmethod
    def split_condition(condition: str, option: str | None = None) -> tuple[str, str | None]:
        """"after_D" -> ("after", "D"); "never" -> ("never", None). A bare
        "before" or "after" needs an explicit option: there is no default
        wording, so nothing can silently fall back to one."""
        kind, _, wording = condition.partition("_")
        if kind not in ("never", "before", "after"):
            raise ValueError(f"unknown condition {condition!r}")
        if kind == "never":
            return kind, None
        wording = wording or option
        if not wording:
            raise ValueError(f"condition {condition!r} names no expectation wording "
                             "(use before_B, after_D, ...)")
        return kind, wording

    def _fill(self, template: str, sentence: str | None) -> str:
        return template.replace("{E}", f"{sentence} " if sentence else "")

    def user_turn(self, turn: int, condition: str, world: str, option: str | None = None) -> str:
        """The user's message at turn 1, 3, 5 or 7 for a condition (never,
        before_B, after_D, ...)."""
        kind, wording = self.split_condition(condition, option)
        sentence = self.expectation(world, wording) if wording else None
        if turn == 1:
            board = (f"\n\n{self.raw['board_sentence']}"
                     if self.raw.get("include_board_sentence") else "")
            text = self.raw["turn1"].replace("{BOARD}", board)
            return self._fill(text, sentence if kind == "before" else None)
        if turn == 3:
            return self._fill(self.raw["turn3"], sentence if kind == "after" else None)
        if turn == 5:
            return self.raw["turn5"]
        if turn == 7:
            return self.raw["turn7"]
        raise ValueError(f"turn {turn} is not a user turn")
