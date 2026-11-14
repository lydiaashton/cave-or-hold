"""The run list: rotation over datasets, a seeded shuffle, a round-robin deal.

Handoff section 8:
- runs per cell is a parameter and must be a multiple of the number of
  datasets used, so every dataset gets the same runs in every condition;
- the full run list is shuffled with a recorded seed and sent in that order;
- each After run is branched from its Never run, so it follows that run;
- the shuffled list is dealt round-robin across machines.

A "unit" is what one Inspect sample executes. A Never run and the After runs
branched from it are one unit ("pair"), which is what guarantees the After
runs follow their Never run. A Before run is its own unit.

The expectation wording is part of the condition (study lead, 13 Nov): with
wordings B and D the cells are never, before_B, after_B, before_D, after_D.
A pair unit holds the Never run and one After run per wording, all branched
from the same turn 2; each Before wording is its own unit. Every cell then
gets the same number of runs per dataset. A wording can be limited to some
worlds (wording_worlds); the strong world, say, may run B only.
"""
from __future__ import annotations

import random
from dataclasses import asdict, dataclass

from .config import Dataset, datasets


@dataclass(frozen=True)
class Unit:
    unit_id: str
    kind: str               # "pair" (Never + its After runs) or "before_<wording>"
    conditions: tuple[str, ...]
    world: str
    seed: int
    dataset_rank: int
    replicate: int
    path: str
    order_index: int = -1   # position in the shuffled full list
    machine_index: int = -1

    def as_metadata(self) -> dict:
        d = asdict(self)
        d.pop("path")       # host path never goes into sample metadata
        d["conditions"] = list(self.conditions)
        return d


def parse_wording_worlds(spec: str) -> dict[str, set[str]]:
    """"D:underpowered+confounded" -> {"D": {"underpowered", "confounded"}}.
    Several wordings are separated by ";". A wording not named runs in every world."""
    out: dict[str, set[str]] = {}
    for part in filter(None, (p.strip() for p in (spec or "").split(";"))):
        wording, _, worlds = part.partition(":")
        if not worlds:
            raise ValueError(f"wording_worlds entry {part!r} must look like D:world+world")
        out[wording.strip()] = {w.strip() for w in worlds.split("+") if w.strip()}
    return out


def build(worlds: list[str], which: str, runs_per_cell: int,
          conditions: list[str], shuffle_seed: int,
          wordings: list[str] | tuple[str, ...] = ("B",),
          wording_worlds: dict[str, set[str]] | None = None) -> list[Unit]:
    """conditions are the kinds (never, before, after); wordings expand before
    and after into one cell per wording (before_B, after_D, ...)."""
    unknown = set(conditions) - {"never", "before", "after"}
    if unknown or not conditions:   # a typo would otherwise drop a whole condition
        raise ValueError(f"conditions must be among never, before, after; got {conditions}")
    if "after" in conditions and "never" not in conditions:
        raise ValueError("After runs branch from Never runs; include 'never'.")
    wordings = list(wordings)
    if not wordings and ({"before", "after"} & set(conditions)):
        raise ValueError("Before and After runs need at least one expectation wording.")
    if len(set(wordings)) != len(wordings):
        raise ValueError(f"a wording is listed twice: {wordings}")
    wording_worlds = wording_worlds or {}
    for w, ws in wording_worlds.items():
        if w not in wordings:
            raise ValueError(f"wording_worlds names {w!r}, which is not among wordings {wordings}")
        if ws - set(worlds):
            raise ValueError(f"wording_worlds limits {w} to {sorted(ws - set(worlds))}, "
                             f"which are not among the batch's worlds {worlds}")
    units: list[Unit] = []
    for world in worlds:
        here = [w for w in wordings if world in wording_worlds.get(w, {world})]
        ds: list[Dataset] = datasets(world, which)
        if not ds:
            raise ValueError(f"no datasets found for world {world!r}")
        if runs_per_cell % len(ds):
            raise ValueError(
                f"runs_per_cell={runs_per_cell} is not a multiple of the "
                f"{len(ds)} datasets used for {world}")
        reps = runs_per_cell // len(ds)
        for d in ds:
            for r in range(1, reps + 1):
                base = f"{world}-s{d.seed}-r{r}"
                if "never" in conditions:
                    pair = ("never",) + (tuple(f"after_{w}" for w in here)
                                         if "after" in conditions else ())
                    units.append(Unit(f"{base}-pair", "pair", pair, world,
                                      d.seed, d.rank, r, str(d.path)))
                if "before" in conditions:
                    for w in here:
                        units.append(Unit(f"{base}-before_{w}", f"before_{w}",
                                          (f"before_{w}",), world, d.seed, d.rank, r,
                                          str(d.path)))
    rng = random.Random(shuffle_seed)
    rng.shuffle(units)
    return [Unit(**{**asdict(u), "order_index": i}) for i, u in enumerate(units)]


def deal(units: list[Unit], n_machines: int) -> list[Unit]:
    """Round-robin within each world x condition stratum, in send order.

    Plain round-robin over the whole shuffled list (unit i -> machine i % n)
    does not balance at pilot sizes: with 40 units and 2 machines it gave one
    machine 2 confounded pairs and the other 8. Dealing round-robin inside each
    stratum keeps every machine within one unit of every other for every world
    and condition, and keeps the shuffled send order. Each stratum starts on a
    different machine so machine 0 does not always take the odd unit.
    """
    strata = sorted({(u.world, u.kind) for u in units})
    offset = {s: i for i, s in enumerate(strata)}
    count: dict[tuple[str, str], int] = {}
    out = []
    for u in sorted(units, key=lambda x: x.order_index):
        s = (u.world, u.kind)
        k = count.get(s, 0)
        count[s] = k + 1
        out.append(Unit(**{**asdict(u), "machine_index": (k + offset[s]) % n_machines}))
    return out
