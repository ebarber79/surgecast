"""CSV log of a guide session: raw readings plus what the guide decided. Same format for the
simulated and the real device, so real sessions can be replayed and compared.

Lines starting with `#` before the header carry session metadata (`# key=value`), such as the
clean-air calibration, which a replay needs to reproduce the session exactly.
"""

from __future__ import annotations

import csv
import math
from typing import IO

from .guide import Instruction, Reading

FIELDS = ["t", "gas_resistance", "wind_angle_deg", "heading_deg", "signal", "detected", "state",
          "target_heading_deg", "turn_deg", "text"]


class SessionLog:
    """Appends one row per step and flushes, so a crash on the device loses nothing."""

    def __init__(self, path: str, **meta):
        self.f: IO[str] = open(path, "w", newline="")
        for k, v in meta.items():
            if v is not None:
                self.f.write(f"# {k}={v}\n")
        self.w = csv.writer(self.f)
        self.w.writerow(FIELDS)

    def write(self, r: Reading, i: Instruction) -> None:
        self.w.writerow([f"{r.t:.2f}", f"{r.gas_resistance:.0f}", f"{math.degrees(r.wind_angle):.1f}",
                         f"{math.degrees(r.heading):.1f}", f"{i.signal:.4f}", int(i.detected), i.state,
                         f"{math.degrees(i.target_heading):.1f}", f"{math.degrees(i.turn):.1f}", i.text])
        self.f.flush()

    def close(self) -> None:
        self.f.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def write_csv(path: str, readings: list[Reading], instructions: list[Instruction], **meta) -> None:
    with SessionLog(path, **meta) as log:
        for r, i in zip(readings, instructions):
            log.write(r, i)


def read_session(path: str) -> tuple[list[Reading], dict[str, str]]:
    """Raw readings and metadata from a log, to replay through a (possibly retuned) Guide."""
    meta: dict[str, str] = {}
    with open(path, newline="") as f:
        lines = f.readlines()
    body = []
    for line in lines:
        if line.startswith("#"):
            k, _, v = line[1:].strip().partition("=")
            meta[k.strip()] = v.strip()
        else:
            body.append(line)
    readings = [Reading(float(row["t"]), float(row["gas_resistance"]),
                        math.radians(float(row["wind_angle_deg"])), math.radians(float(row["heading_deg"])))
                for row in csv.DictReader(body)]
    return readings, meta


def read_readings(path: str) -> list[Reading]:
    return read_session(path)[0]
