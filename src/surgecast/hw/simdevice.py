"""A simulated person carrying the guide through an indoor fan plume.

This exercises the full hardware path before any parts arrive: a slow, noisy MOX sensor
reporting resistance, a noisy vane and IMU, and a person who follows instructions with a
reaction delay, a limited turn rate, and some wobble.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

import numpy as np

from ..plume import Plume, PlumeConfig
from ..sim import EpisodeResult
from .detect import OdorSignal
from .guide import Guide, Instruction, Reading, wrap


def indoor_plume() -> PlumeConfig:
    """A box fan across an 8 x 6 m room: steady direction, lots of small-scale mixing."""
    return PlumeConfig(
        source=(1.0, 0.0),
        wind_speed=1.0,
        meander_sigma=0.15,
        meander_tau=3.0,
        turbulence=0.2,
        bounds=(0.0, 8.0, -3.0, 3.0),
    )


@dataclass
class DeviceSimConfig:
    plume: PlumeConfig = field(default_factory=indoor_plume)
    dt: float = 0.1
    warmup: float = 15.0
    max_time: float = 120.0
    walk_speed: float = 0.5  # m/s
    reaction: float = 0.7  # s between an instruction and the person acting on it
    turn_rate: float = math.radians(180)  # rad/s
    heading_wobble: float = 0.1  # rad
    sensor_tau: float = 2.0  # s, MOX response time constant
    r_clean: float = 50_000.0  # ohm, resistance in clean air
    sensitivity: float = 20.0  # R = r_clean / (1 + sensitivity * c)
    sensor_noise: float = 0.003  # relative
    vane_noise: float = 0.15  # rad
    imu_noise: float = 0.03  # rad
    start_downwind: tuple[float, float] = (4.5, 6.0)
    start_crosswind: float = 1.0
    success_radius: float = 0.5


@dataclass
class DeviceRun:
    result: EpisodeResult
    readings: list[Reading]
    instructions: list[Instruction]


def run_device_episode(seed: int, cfg: DeviceSimConfig | None = None, record_every: int = 0,
                       guide: Guide | None = None) -> DeviceRun:
    cfg = cfg or DeviceSimConfig()
    plume = Plume(cfg.plume, np.random.default_rng([seed, 0]))
    rng = np.random.default_rng([seed, 2])
    # Clean-air calibration happened before the search, as on the real device.
    guide = guide or Guide(seed=seed, signal=OdorSignal(r_clean=cfg.r_clean))

    for _ in range(int(cfg.warmup / cfg.dt)):
        plume.step(cfg.dt)

    src = plume.source
    pos = np.array([src[0] + rng.uniform(*cfg.start_downwind),
                    src[1] + rng.uniform(-cfg.start_crosswind, cfg.start_crosswind)])
    heading = math.pi  # facing roughly toward the fan to start
    c_sensed = plume.concentration(pos)  # sensor has settled where the person stands
    pending: deque[tuple[float, float]] = deque()  # (time to act, target heading)
    target = heading
    xmin, xmax, ymin, ymax = cfg.plume.bounds

    path, states, frames, readings, instructions = [pos.copy()], [], [], [], []
    t, success = 0.0, False
    for i in range(int(cfg.max_time / cfg.dt)):
        # Sensors.
        c_sensed += (plume.concentration(pos) - c_sensed) * min(cfg.dt / cfg.sensor_tau, 1.0)
        resistance = cfg.r_clean / (1 + cfg.sensitivity * c_sensed)
        resistance *= 1 + cfg.sensor_noise * rng.standard_normal()
        w = plume.wind()
        wind_world = math.atan2(w[1], w[0])
        reading = Reading(
            t=t,
            gas_resistance=resistance,
            wind_angle=wrap(wind_world - heading + cfg.vane_noise * rng.standard_normal()),
            heading=wrap(heading + cfg.imu_noise * rng.standard_normal()),
        )
        ins = guide.step(reading)
        readings.append(reading)
        instructions.append(ins)
        states.append(ins.state)

        # The person acts on each instruction after a reaction delay.
        pending.append((t + cfg.reaction, ins.target_heading))
        while pending and pending[0][0] <= t:
            target = pending.popleft()[1]
        max_turn = cfg.turn_rate * cfg.dt
        heading = wrap(heading + float(np.clip(wrap(target - heading), -max_turn, max_turn)))
        walk = heading + cfg.heading_wobble * rng.standard_normal()
        pos = pos + cfg.walk_speed * cfg.dt * np.array([math.cos(walk), math.sin(walk)])
        pos[0] = np.clip(pos[0], xmin, xmax)
        pos[1] = np.clip(pos[1], ymin, ymax)

        plume.step(cfg.dt)
        t += cfg.dt
        path.append(pos.copy())
        if record_every and i % record_every == 0:
            frames.append(plume.pos.copy())
        if np.linalg.norm(pos - src) <= cfg.success_radius:
            success = True
            break

    states.append(states[-1] if states else "cast")
    result = EpisodeResult(
        agent="guide (simulated device)", seed=seed, success=success, time=t,
        path=np.array(path), states=states, hits=sum(i.detected for i in instructions),
        frames=frames, source=tuple(src), bounds=cfg.plume.bounds,
    )
    return DeviceRun(result, readings, instructions)
