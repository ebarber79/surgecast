"""Handheld guide: sensor readings in, walking instructions out.

Frames: `heading` is the world angle the device (and the person holding it) faces, from the
IMU. `wind_angle` is the direction the air is moving *toward*, relative to that facing, from
the vane. World wind is their sum. The world frame only has to stay consistent during one
search, so a gyro-only yaw (no magnetometer) is fine.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ..agents import Observation, SurgeCast
from .detect import OdorSignal, RiseDetector


@dataclass
class Reading:
    t: float  # s
    gas_resistance: float  # ohm
    wind_angle: float  # rad, wind-to direction relative to device facing
    heading: float  # rad, device facing in the world frame


@dataclass
class Instruction:
    t: float
    state: str  # agent state: surge / cast
    target_heading: float  # rad, world
    turn: float  # rad, positive = turn left (counter-clockwise)
    text: str
    signal: float
    detected: bool


def wrap(a: float) -> float:
    return (a + math.pi) % (2 * math.pi) - math.pi


def describe(state: str, target: float, wind_world: float, turn: float) -> str:
    if state == "surge":
        text = "Odor! Walk into the wind"
    elif state == "recover":
        text = "Lost it for a while, you may have passed it. Back off with the wind, sweeping across"
    else:
        # Which side the wind comes from, relative to the direction we want them to walk.
        wind_from = wind_world + math.pi
        side = "left" if wrap(wind_from - target) > 0 else "right"
        text = f"Lost it. Walk across the wind, wind on your {side}"
    deg = round(math.degrees(abs(turn)))
    if deg >= 20:
        text += f" (turn {'left' if turn > 0 else 'right'} {deg}°)"
    return text


class Guide:
    def __init__(self, agent: SurgeCast | None = None, detector: RiseDetector | None = None,
                 signal: OdorSignal | None = None, seed: int = 0, nominal_dt: float = 0.1):
        # Indoors the source has a wall or the fan right behind it, so recover from overshoot.
        self.agent = agent or SurgeCast(recover_after=10.0)
        self.agent.reset(np.random.default_rng(seed))
        self.detector = detector or RiseDetector()
        self.signal = signal or OdorSignal()
        self.nominal_dt = nominal_dt
        self.last_t: float | None = None

    def step(self, r: Reading) -> Instruction:
        dt = self.nominal_dt if self.last_t is None else r.t - self.last_t
        self.last_t = r.t
        s = self.signal.update(r.gas_resistance, dt)
        detected = self.detector.update(s, dt)
        wind_world = r.heading + r.wind_angle
        wind = np.array([math.cos(wind_world), math.sin(wind_world)])
        # Position is unknown on a handheld; surge-cast doesn't use it.
        h = self.agent.act(Observation(r.t, np.zeros(2), wind, s, detected), dt)
        target = math.atan2(h[1], h[0])
        turn = wrap(target - r.heading)
        return Instruction(r.t, self.agent.state, target, turn,
                           describe(self.agent.state, target, wind_world, turn), s, detected)
