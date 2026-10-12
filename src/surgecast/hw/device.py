"""The live loop the handheld runs: sensors -> guide -> feedback, logging every step.

Hardware plugs in through two small interfaces. A `SensorSource` yields `Reading`s at the
loop rate (real drivers block until the next sample is due; `ReplaySource` plays back a
logged session). A `Feedback` renders cues. `TerminalFeedback` prints them, and the buzzer
will render the same patterns.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from .guide import Guide, Instruction, Reading
from .log import SessionLog, read_session


class SensorSource(Protocol):
    def read(self) -> Reading | None:
        """Next reading, or None when the stream ends."""


class Feedback(Protocol):
    def cue(self, cue: "Cue", ins: Instruction) -> None: ...


@dataclass(frozen=True)
class Cue:
    """What to tell the person, as a pattern they can act on without reading.

    Reaction time dominates search time in simulation, so each change is one short, distinct
    pattern: `-` is a long buzz, `.` a short one.
    """

    name: str
    pattern: str
    meaning: str


CUES = {
    "surge": Cue("surge", "-", "odor: face into the wind and walk"),
    "left": Cue("left", "..", "turn left, walk across the wind"),
    "right": Cue("right", "...", "turn right, walk across the wind"),
    "recover": Cue("recover", "--", "lost it for a while: back off with the wind, sweeping"),
}


class Cuer:
    """Turns the instruction stream into cues, only when the person needs to change course."""

    def __init__(self):
        self.last: tuple[str, str] | None = None

    def update(self, ins: Instruction) -> Cue | None:
        side = "left" if "wind on your left" in ins.text else "right"
        key = (ins.state, side if ins.state == "cast" else "")
        if key == self.last:
            return None
        self.last = key
        if ins.state == "cast":
            return CUES["left" if ins.turn > 0 else "right"]
        return CUES.get(ins.state)


class TerminalFeedback:
    def __init__(self, out=print):
        self.out = out

    def cue(self, cue: Cue, ins: Instruction) -> None:
        self.out(f"{ins.t:7.1f}s  {cue.pattern:<4} {cue.name.upper():<8} {ins.text}")


class ReplaySource:
    """Plays back a logged session, optionally at the speed it was recorded."""

    def __init__(self, path: str, realtime: bool = False):
        self.readings, self.meta = read_session(path)
        self.realtime = realtime
        self.i = 0
        self.t0_wall: float | None = None

    def read(self) -> Reading | None:
        if self.i >= len(self.readings):
            return None
        r = self.readings[self.i]
        self.i += 1
        if self.realtime:
            if self.t0_wall is None:
                self.t0_wall = time.monotonic() - r.t
            delay = self.t0_wall + r.t - time.monotonic()
            if delay > 0:
                time.sleep(delay)
        return r


def run_live(source: SensorSource, guide: Guide, feedback: Feedback | None = None,
             log_path: str | None = None, max_time: float | None = None, **log_meta
             ) -> list[Instruction]:
    cuer = Cuer()
    log = SessionLog(log_path, **log_meta) if log_path else None
    instructions = []
    try:
        while (r := source.read()) is not None:
            ins = guide.step(r)
            instructions.append(ins)
            if log:
                log.write(r, ins)
            cue = cuer.update(ins)
            if cue and feedback:
                feedback.cue(cue, ins)
            if max_time is not None and r.t >= max_time:
                break
    finally:
        if log:
            log.close()
    return instructions
