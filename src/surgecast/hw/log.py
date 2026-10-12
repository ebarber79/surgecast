"""CSV log of a guide session: raw readings plus what the guide decided. Same format for the
simulated and the real device, so real sessions can be replayed and compared."""

from __future__ import annotations

import csv
import math

from .guide import Instruction, Reading

FIELDS = ["t", "gas_resistance", "wind_angle_deg", "heading_deg", "signal", "detected", "state",
          "target_heading_deg", "turn_deg", "text"]


def write_csv(path: str, readings: list[Reading], instructions: list[Instruction]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(FIELDS)
        for r, i in zip(readings, instructions):
            w.writerow([f"{r.t:.2f}", f"{r.gas_resistance:.0f}", f"{math.degrees(r.wind_angle):.1f}",
                        f"{math.degrees(r.heading):.1f}", f"{i.signal:.4f}", int(i.detected), i.state,
                        f"{math.degrees(i.target_heading):.1f}", f"{math.degrees(i.turn):.1f}", i.text])


def read_readings(path: str) -> list[Reading]:
    """Raw readings from a log, to replay through a (possibly retuned) Guide."""
    with open(path, newline="") as f:
        return [Reading(float(row["t"]), float(row["gas_resistance"]),
                        math.radians(float(row["wind_angle_deg"])), math.radians(float(row["heading_deg"])))
                for row in csv.DictReader(f)]
