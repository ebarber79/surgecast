"""Puff-based turbulent plume model.

The source releases discrete puffs. Each puff is carried by a wind whose direction wanders
over time (an Ornstein-Uhlenbeck process), so the plume snakes like a waved hose. Each puff
also takes its own random turbulent kicks and spreads as it ages. The result is what a moth
actually faces downwind: odor arrives in patches, with gaps, and the instantaneous
concentration says little about which way the source lies.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class PlumeConfig:
    source: tuple[float, float] = (5.0, 0.0)
    wind_speed: float = 1.0  # m/s
    meander_sigma: float = 0.35  # rad, stationary std of wind direction
    meander_tau: float = 4.0  # s, correlation time of wind direction
    release_rate: float = 5.0  # puffs per second
    puff_r0: float = 0.05  # m, radius at release
    puff_growth: float = 0.01  # m^2/s, growth of radius^2 with age
    turbulence: float = 0.25  # m/s^0.5, per-puff random-walk strength
    bounds: tuple[float, float, float, float] = (0.0, 60.0, -20.0, 20.0)  # xmin, xmax, ymin, ymax


class Plume:
    def __init__(self, cfg: PlumeConfig, rng: np.random.Generator):
        self.cfg = cfg
        self.rng = rng
        self.source = np.asarray(cfg.source, dtype=float)
        self.theta = 0.0  # wind direction, 0 = blowing toward +x
        self.pos = np.empty((0, 2))
        self.age = np.empty(0)
        self._release_debt = 0.0

    def wind(self) -> np.ndarray:
        """Wind vector. Spatially uniform, so it is also what an agent feels locally."""
        u = self.cfg.wind_speed
        return np.array([u * np.cos(self.theta), u * np.sin(self.theta)])

    def step(self, dt: float) -> None:
        c = self.cfg
        # Wind direction meander, scaled so its stationary std is meander_sigma.
        self.theta += -self.theta / c.meander_tau * dt + c.meander_sigma * np.sqrt(
            2 * dt / c.meander_tau
        ) * self.rng.standard_normal()

        # Release new puffs at the source.
        self._release_debt += c.release_rate * dt
        n_new = int(self._release_debt)
        if n_new:
            self._release_debt -= n_new
            self.pos = np.vstack([self.pos, np.repeat(self.source[None, :], n_new, axis=0)])
            self.age = np.concatenate([self.age, np.zeros(n_new)])

        # Advect, diffuse, age.
        self.pos += self.wind() * dt
        self.pos += c.turbulence * np.sqrt(dt) * self.rng.standard_normal(self.pos.shape)
        self.age += dt

        xmin, xmax, ymin, ymax = c.bounds
        keep = (
            (self.pos[:, 0] >= xmin)
            & (self.pos[:, 0] <= xmax)
            & (self.pos[:, 1] >= ymin)
            & (self.pos[:, 1] <= ymax)
        )
        self.pos, self.age = self.pos[keep], self.age[keep]

    def radius_sq(self) -> np.ndarray:
        return self.cfg.puff_r0**2 + self.cfg.puff_growth * self.age

    def concentration(self, point: np.ndarray) -> float:
        """Sum of unit-mass 2D Gaussian puffs at `point`."""
        if not len(self.pos):
            return 0.0
        r2 = self.radius_sq()
        d2 = np.sum((self.pos - point) ** 2, axis=1)
        return float(np.sum(np.exp(-d2 / (2 * r2)) / (2 * np.pi * r2)))
