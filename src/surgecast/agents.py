"""Search strategies. Each agent returns a unit heading every step and exposes `state` for plots.

All agents get the same observation: position, local wind vector, odor concentration and a
binary detection (concentration above threshold). Moths sense airflow with their antennae,
so knowing the wind is fair game.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Observation:
    t: float
    position: np.ndarray
    wind: np.ndarray
    concentration: float
    detected: bool


def _unit(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def _rotate(v: np.ndarray, angle: float) -> np.ndarray:
    c, s = np.cos(angle), np.sin(angle)
    return np.array([c * v[0] - s * v[1], s * v[0] + c * v[1]])


class WindMemory:
    """Exponential moving average of the wind the agent has felt.

    The odor at the agent left the source seconds ago and travelled with the wind of that
    time, so the line back to the source follows the recent average wind, not the gust
    blowing right now. Surging along the average keeps the agent on the plume axis.
    """

    def __init__(self, tau: float):
        self.tau = tau
        self.w: np.ndarray | None = None

    def update(self, wind: np.ndarray, dt: float) -> np.ndarray:
        if self.w is None or self.tau <= 0:
            self.w = wind.copy()
        else:
            self.w = self.w + (wind - self.w) * min(dt / self.tau, 1.0)
        return self.w


class SurgeCast:
    """The moth strategy.

    On contact with odor, surge upwind. When the odor is lost, cast crosswind in a zigzag
    whose legs (in seconds) grow each turn, widening the search, while still edging slowly
    upwind. Unlike gradient-following, this never needs to compare two concentrations, which
    is why it works in turbulent air where gradients are meaningless.

    "Upwind" uses the wind averaged over `wind_tau` seconds (see `WindMemory`). `cast_upwind`
    is how much upwind progress to keep while casting. Above ~0.2 the agent starts
    overshooting the source, and nothing upwind of the source ever smells of anything.
    """

    name = "surgecast"

    def __init__(
        self,
        surge_time: float = 1.0,
        cast_leg: float = 2.0,
        cast_growth: float = 1.3,
        max_leg: float = 10.0,
        wind_tau: float = 10.0,
        cast_upwind: float = 0.2,
    ):
        self.surge_time = surge_time
        self.cast_leg = cast_leg
        self.cast_growth = cast_growth
        self.max_leg = max_leg
        self.wind_tau = wind_tau
        self.cast_upwind = cast_upwind

    def reset(self, rng: np.random.Generator) -> None:
        self.rng = rng
        self.wind = WindMemory(self.wind_tau)
        self.last_hit = -np.inf
        self.cast_dir = rng.choice([-1.0, 1.0])
        # First leg is half length so the zigzag is centred on where the odor was lost.
        self.leg_len = self.cast_leg / 2
        self.leg_t = 0.0
        self.state = "cast"

    def act(self, obs: Observation, dt: float) -> np.ndarray:
        upwind = _unit(-self.wind.update(obs.wind, dt))
        crosswind = np.array([-upwind[1], upwind[0]])

        if obs.detected:
            self.last_hit = obs.t
            self.leg_len = self.cast_leg / 2
            self.leg_t = 0.0

        since = obs.t - self.last_hit
        if since <= self.surge_time:
            self.state = "surge"
            return upwind

        self.state = "cast"
        self.leg_t += dt
        if self.leg_t >= self.leg_len:
            self.leg_t = 0.0
            self.cast_dir *= -1
            # After the opening half leg, legs start at full length and then widen.
            grown = self.cast_leg if self.leg_len < self.cast_leg else self.leg_len * self.cast_growth
            self.leg_len = min(grown, self.max_leg)
        return _unit(self.cast_dir * crosswind + self.cast_upwind * upwind)


class UpwindOnly:
    """Ablation: surge upwind on contact, but random-walk instead of casting when lost."""

    name = "upwind"

    def __init__(self, surge_time: float = 1.0, turn_sigma: float = 0.6, wind_tau: float = 10.0):
        self.surge_time = surge_time
        self.turn_sigma = turn_sigma
        self.wind_tau = wind_tau

    def reset(self, rng: np.random.Generator) -> None:
        self.rng = rng
        self.wind = WindMemory(self.wind_tau)
        self.last_hit = -np.inf
        self.heading = _rotate(np.array([1.0, 0.0]), rng.uniform(-np.pi, np.pi))
        self.state = "search"

    def act(self, obs: Observation, dt: float) -> np.ndarray:
        wind = self.wind.update(obs.wind, dt)
        if obs.detected:
            self.last_hit = obs.t
        if obs.t - self.last_hit <= self.surge_time:
            self.state = "surge"
            self.heading = _unit(-wind)
            return self.heading
        self.state = "search"
        self.heading = _rotate(self.heading, self.turn_sigma * np.sqrt(dt) * self.rng.standard_normal())
        return self.heading


class Gradient:
    """Baseline: klinotaxis. Keep going while concentration rises, turn randomly when it falls.

    This is what works for a bacterium in still water, and what fails in a turbulent plume.
    It ignores the wind entirely.
    """

    name = "gradient"

    def __init__(self, sample_time: float = 0.5, turn_sigma: float = 0.6):
        self.sample_time = sample_time
        self.turn_sigma = turn_sigma

    def reset(self, rng: np.random.Generator) -> None:
        self.rng = rng
        self.heading = _rotate(np.array([1.0, 0.0]), rng.uniform(-np.pi, np.pi))
        self.prev = 0.0
        self.acc = 0.0
        self.n = 0
        self.t_sample = 0.0
        self.state = "search"

    def act(self, obs: Observation, dt: float) -> np.ndarray:
        self.acc += obs.concentration
        self.n += 1
        self.t_sample += dt
        if self.t_sample >= self.sample_time:
            mean = self.acc / self.n
            if mean > self.prev and mean > 0:
                self.state = "climb"
            else:
                self.state = "search"
                self.heading = _rotate(self.heading, self.rng.uniform(-np.pi, np.pi))
            self.prev = mean
            self.acc, self.n, self.t_sample = 0.0, 0, 0.0
        else:
            self.heading = _rotate(self.heading, self.turn_sigma * np.sqrt(dt) * self.rng.standard_normal())
        return self.heading


AGENTS = {cls.name: cls for cls in (SurgeCast, UpwindOnly, Gradient)}
