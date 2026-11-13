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

    def expectation(self, world: str, option: str) -> str:
        return self.raw["expectation"][option][WORLD_KIND[world]]

    def _fill(self, template: str, sentence: str | None) -> str:
        return template.replace("{E}", f"{sentence} " if sentence else "")

    def user_turn(self, turn: int, condition: str, world: str, option: str) -> str:
        """The user's message at turn 1, 3, 5 or 7 for a condition."""
        sentence = self.expectation(world, option)
        if turn == 1:
            return self._fill(self.raw["turn1"], sentence if condition == "before" else None)
        if turn == 3:
            return self._fill(self.raw["turn3"], sentence if condition == "after" else None)
        if turn == 5:
            return self.raw["turn5"]
        if turn == 7:
            return self.raw["turn7"]
        raise ValueError(f"turn {turn} is not a user turn")
