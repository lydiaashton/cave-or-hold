"""The run list: rotation over datasets, a seeded shuffle, a round-robin deal.

Handoff section 8:
- runs per cell is a parameter and must be a multiple of the number of
  datasets used, so every dataset gets the same runs in every condition;
- the full run list is shuffled with a recorded seed and sent in that order;
- each After run is branched from its Never run, so it follows that run;
- the shuffled list is dealt round-robin across machines.

A "unit" is what one Inspect sample executes. A Never run and the After run
branched from it are one unit ("pair"), which is what guarantees the After
run follows its Never run. A Before run is its own unit.
"""
from __future__ import annotations

import random
from dataclasses import asdict, dataclass

from .config import Dataset, datasets


@dataclass(frozen=True)
class Unit:
    unit_id: str
    kind: str               # "pair" (Never + its After) or "before"
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


def build(worlds: list[str], which: str, runs_per_cell: int,
          conditions: list[str], shuffle_seed: int) -> list[Unit]:
    unknown = set(conditions) - {"never", "before", "after"}
    if unknown or not conditions:   # a typo would otherwise drop a whole condition
        raise ValueError(f"conditions must be among never, before, after; got {conditions}")
    if "after" in conditions and "never" not in conditions:
        raise ValueError("After runs branch from Never runs; include 'never'.")
    units: list[Unit] = []
    for world in worlds:
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
                pair = tuple(c for c in ("never", "after") if c in conditions)
                if pair:
                    units.append(Unit(f"{base}-pair", "pair", pair, world,
                                      d.seed, d.rank, r, str(d.path)))
                if "before" in conditions:
                    units.append(Unit(f"{base}-before", "before", ("before",),
                                      world, d.seed, d.rank, r, str(d.path)))
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
