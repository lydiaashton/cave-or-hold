"""Study constants: paths, worlds and the release datasets.

Everything here comes from the design doc (13 Nov 2026). Turn wording lives in
prompts/turns.toml so it can be replaced by the signed-off Prompt draft without
touching code.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = HARNESS_DIR.parent
RELEASE_DIR = REPO_DIR / "release"
ANSWER_KEY_DIR = RELEASE_DIR / "answer_key"   # judges only; never reaches the sandbox
PROMPTS_FILE = HARNESS_DIR / "prompts" / "turns.toml"
JUDGE_PROMPTS_FILE = HARNESS_DIR / "prompts" / "judges.toml"
RUNS_DIR = HARNESS_DIR / "runs"
# One folder per batch, committed and pushed (scorers cannot see the repo).
# The export writes T2..T8, key/ and judges/; the judge runner writes judging/.
EXPORTS_DIR = REPO_DIR / "exports"
# Keys may sit in harness/.env or in the repository root's .env.
ENV_FILES = (HARNESS_DIR / ".env", REPO_DIR / ".env")

ADAPTION_BASE_URL = "https://api.prod.adaptionlabs.ai/api/v1"
# The three judges (design doc, "Models and judges"): name -> Inspect model
# string. No judge shares a developer with a tested model.
JUDGES = {
    "gemini-4-argon": "google/gemini-4-argon",
    "gpt-6-astra": "openai/gpt-6-astra",
    "deepseek-v4-flash": "openai-api/adaption/deepseek-v4-flash",
}

# Which way each world's expectation pushes. The sentences themselves live in
# prompts/turns.toml only, so they cannot drift from the signed-off wording.
WORLD_KIND = {"underpowered": "weak", "confounded": "weak", "strong": "strong"}


@dataclass(frozen=True)
class Dataset:
    world: str
    seed: int
    path: Path          # release/<world>_seed<seed>/branches.csv
    rank: int           # 1 = lowest seed in its world

    @property
    def original_five(self) -> bool:
        """The first five per world (five lowest seeds) are the original set."""
        return self.rank <= 5


def datasets(world: str | None = None, which: str = "all") -> list[Dataset]:
    """Datasets in release/, ordered by seed within world.

    which: "all" (every dataset in release/, sixty per world since 14 Nov) or
    "firstN" (the N lowest seeds per world, e.g. "first5", "first20"; the first
    ten are the 13 Nov release, unchanged). Which one the study uses is a
    pre-registered rule set by the study lead; this only applies it.
    """
    out: list[Dataset] = []
    for w in sorted(WORLD_KIND):
        if world and w != world:
            continue
        found = []
        for d in RELEASE_DIR.glob(f"{w}_seed*"):
            f = d / "branches.csv"
            if f.is_file():
                found.append((int(d.name.split("_seed")[1]), f))
        for rank, (seed, f) in enumerate(sorted(found), start=1):
            out.append(Dataset(w, seed, f, rank))
    if which == "all":
        return out
    m = re.fullmatch(r"first([1-9][0-9]*)", which)
    if not m:
        raise ValueError(f"which must be 'all' or 'firstN' (e.g. first5, first20), not {which!r}")
    n = int(m.group(1))
    for w in sorted({d.world for d in out}):
        have = sum(d.world == w for d in out)
        if n > have:
            raise ValueError(f"{which} asks for {n} datasets but release/ holds {have} for {w}")
    return [d for d in out if d.rank <= n]
