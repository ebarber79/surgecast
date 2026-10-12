"""Run one search episode, or a benchmark of agents on shared plume realizations."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .agents import AGENTS, Observation
from .plume import Plume, PlumeConfig


@dataclass
class EpisodeConfig:
    dt: float = 0.1  # s
    max_time: float = 150.0  # s
    warmup: float = 60.0  # s of plume before the agent starts, so the arena fills
    speed: float = 0.8  # m/s agent ground speed
    threshold: float = 0.02  # detection threshold on concentration
    success_radius: float = 1.0  # m
    start_downwind: tuple[float, float] = (25.0, 35.0)  # m downwind of source, sampled
    start_crosswind: float = 3.0  # m, start y sampled from +/- this


@dataclass
class EpisodeResult:
    agent: str
    seed: int
    success: bool
    time: float
    path: np.ndarray
    states: list[str]
    hits: int
    # Puff positions every `record_every` steps, only filled when recording.
    frames: list[np.ndarray] = field(default_factory=list)
    source: tuple[float, float] = (0.0, 0.0)
    bounds: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)


def run_episode(
    agent_name: str,
    seed: int,
    plume_cfg: PlumeConfig | None = None,
    ep_cfg: EpisodeConfig | None = None,
    record_every: int = 0,
) -> EpisodeResult:
    plume_cfg = plume_cfg or PlumeConfig()
    ep = ep_cfg or EpisodeConfig()

    # Separate streams: the plume depends only on the seed, so every agent faces the
    # same wind and puffs for a given seed.
    plume = Plume(plume_cfg, np.random.default_rng([seed, 0]))
    agent_rng = np.random.default_rng([seed, 1])
    agent = AGENTS[agent_name]()
    agent.reset(agent_rng)

    for _ in range(int(ep.warmup / ep.dt)):
        plume.step(ep.dt)

    src = plume.source
    pos = np.array(
        [
            src[0] + agent_rng.uniform(*ep.start_downwind),
            src[1] + agent_rng.uniform(-ep.start_crosswind, ep.start_crosswind),
        ]
    )
    xmin, xmax, ymin, ymax = plume_cfg.bounds

    path, states, frames = [pos.copy()], [agent.state], []
    hits, t, success = 0, 0.0, False
    for i in range(int(ep.max_time / ep.dt)):
        c = plume.concentration(pos)
        detected = c > ep.threshold
        hits += detected
        heading = agent.act(Observation(t, pos.copy(), plume.wind(), c, detected), ep.dt)
        pos = pos + ep.speed * ep.dt * heading
        pos[0] = np.clip(pos[0], xmin, xmax)
        pos[1] = np.clip(pos[1], ymin, ymax)
        plume.step(ep.dt)
        t += ep.dt
        path.append(pos.copy())
        states.append(agent.state)
        if record_every and i % record_every == 0:
            frames.append(plume.pos.copy())
        if np.linalg.norm(pos - src) <= ep.success_radius:
            success = True
            break

    return EpisodeResult(
        agent=agent_name,
        seed=seed,
        success=success,
        time=t,
        path=np.array(path),
        states=states,
        hits=int(hits),
        frames=frames,
        source=tuple(src),
        bounds=plume_cfg.bounds,
    )


@dataclass
class BenchRow:
    agent: str
    trials: int
    success_rate: float
    median_time: float  # over successful runs, nan if none


def bench(
    agents: list[str],
    trials: int,
    plume_cfg: PlumeConfig | None = None,
    ep_cfg: EpisodeConfig | None = None,
    seed0: int = 0,
) -> list[BenchRow]:
    rows = []
    for name in agents:
        results = [run_episode(name, seed0 + s, plume_cfg, ep_cfg) for s in range(trials)]
        times = [r.time for r in results if r.success]
        rows.append(
            BenchRow(
                agent=name,
                trials=trials,
                success_rate=len(times) / trials,
                median_time=float(np.median(times)) if times else float("nan"),
            )
        )
    return rows
