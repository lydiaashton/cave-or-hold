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
# Pilot datasets: ten per world, never used in the main runs (generator/build_pilot_set.py).
PILOT_RELEASE_DIR = REPO_DIR / "release_pilot"
PILOT_ANSWER_KEY_DIR = PILOT_RELEASE_DIR / "answer_key"
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
    "gemma-4-31b-it": "openai-api/adaption/gemma-4-31b-it",
    "gpt-6.1-terra": "openai/gpt-6.1-terra",
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
    "firstN" (the N lowest seeds per world, e.g. "first5", "first20"). For
    confounded and strong the first ten are the 13 Nov release; the underpowered
    world was reselected on 14 Nov (primary p .10 to .13; generator/select_underpowered.py). Which one the study
    uses is a pre-registered rule set by the study lead; this only applies it.
    "pilot" or "pilotN" reads release_pilot/ instead: the ten pilot datasets per
    world, which never appear in release/ (all of them, or the N lowest seeds).
    """
    pilot = which.startswith("pilot")
    base = PILOT_RELEASE_DIR if pilot else RELEASE_DIR
    out: list[Dataset] = []
    for w in sorted(WORLD_KIND):
        if world and w != world:
            continue
        found = []
        for d in base.glob(f"{w}_seed*"):
            f = d / "branches.csv"
            if f.is_file():
                found.append((int(d.name.split("_seed")[1]), f))
        for rank, (seed, f) in enumerate(sorted(found), start=1):
            out.append(Dataset(w, seed, f, rank))
    if which in ("all", "pilot"):
        return out
    m = re.fullmatch(r"(?:first|pilot)([1-9][0-9]*)", which)
    if not m:
        raise ValueError(f"which must be 'all', 'firstN', 'pilot' or 'pilotN' "
                         f"(e.g. first5, first20, pilot7), not {which!r}")
    n = int(m.group(1))
    for w in sorted({d.world for d in out}):
        have = sum(d.world == w for d in out)
        if n > have:
            raise ValueError(f"{which} asks for {n} datasets but {base.name}/ holds {have} for {w}")
    return [d for d in out if d.rank <= n]
